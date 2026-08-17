import os
import time
import random
import hashlib
import json
import threading
import concurrent.futures
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

class GeminiClient:
    """
    Centralized Gemini Client Wrapper.
    Handles caching, rate limits, exponential backoff, quota exhaustion detection,
    token usage tracking, in-flight request deduplication, and automatic DEMO/CACHE mode fallback.
    """
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        
        self.llm = None
        if self.api_key:
            try:
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.3,
                    max_output_tokens=4096,
                    request_timeout=10.0
                )
            except Exception as e:
                print(f"[GeminiClient Warning] Failed to initialize ChatGoogleGenerativeAI: {e}")

        # In-memory Response Cache, In-flight Lock & Telemetry
        self.cache = {}
        self.in_flight = {}  # cache_key -> (threading.Event, holder_dict)
        self.lock = threading.Lock()
        self.request_count = 0
        self.cache_hits = 0
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Circuit Breaker & Quota State
        self.quota_exhausted = False
        self.circuit_open = False
        self.gemini_available = True if (self.api_key and self.llm) else False
        self.last_failure_time = 0.0
        try:
            self.cooldown_seconds = float(os.getenv("GEMINI_COOLDOWN_SECONDS", "60"))
        except (ValueError, TypeError):
            self.cooldown_seconds = 60.0

        if not self.gemini_available:
            self.circuit_open = True
            self.quota_exhausted = True
            self.last_failure_time = time.time()

        self.last_error = None
        self.total_latency_seconds = 0.0

    def _get_cooldown_seconds(self) -> float:
        """Helper to get configurable cooldown period in seconds."""
        try:
            return float(os.getenv("GEMINI_COOLDOWN_SECONDS", str(self.cooldown_seconds)))
        except (ValueError, TypeError):
            return 60.0

    def _is_service_exhausted_error(self, e: Exception, err_msg: str) -> bool:
        """
        Detects if an error is due to 429, quota limits, 499 cancellation, timeout,
        resource exhaustion, or service unavailability.
        """
        msg_lower = err_msg.lower()
        if isinstance(e, (concurrent.futures.TimeoutError, TimeoutError)):
            return True

        status_code = getattr(e, "status_code", None) or getattr(e, "code", None)
        if status_code in (429, 499, 503, 504):
            return True

        exhaustion_keywords = [
            "429", "499", "503", "504",
            "quota", "resourceexhausted", "resource_exhausted",
            "rate limit", "ratelimit", "cancel", "cancelled", "canceled",
            "timeout", "timed out", "exhausted", "invalid", "overloaded",
            "unavailable", "deadline", "service unavailable", "serviceunavailable"
        ]
        return any(k in msg_lower for k in exhaustion_keywords)

    def _normalize_prompt(self, prompt: str) -> str:
        """Create a normalized hash key for caching."""
        clean_text = re.sub(r'\s+', ' ', prompt.strip().lower())
        return hashlib.md5(clean_text.encode("utf-8")).hexdigest()

    def generate(self, prompt: str, system_instruction: str = "", max_retries: int = 1) -> dict:
        """
        Main entry point for all Gemini requests across all agents.
        Returns dict: {"content": str, "is_cached": bool, "is_demo": bool, "tokens": int}
        """
        full_text = f"{system_instruction}\n\n{prompt}".strip()
        cache_key = self._normalize_prompt(full_text)

        # 1. Check Response Cache & In-flight Deduplication
        with self.lock:
            if cache_key in self.cache:
                self.cache_hits += 1
                print(f"[GeminiClient CACHE HIT] Reusing cached response for query hash: {cache_key[:8]}")
                return {
                    "content": self.cache[cache_key],
                    "is_cached": True,
                    "is_demo": False,
                    "quota_exhausted": not self.gemini_available
                }
            
            if cache_key in self.in_flight:
                event, holder = self.in_flight[cache_key]
                print(f"[GeminiClient DEDUPLICATION] Reusing in-flight request for query hash: {cache_key[:8]}")
                need_wait = True
            else:
                event = threading.Event()
                holder = {"result": None}
                self.in_flight[cache_key] = (event, holder)
                need_wait = False

        if need_wait:
            event.wait(timeout=30.0)
            with self.lock:
                self.cache_hits += 1
            res = holder.get("result")
            if res:
                return res
            # Fallback if wait timed out or failed
            demo_res = self._generate_demo_fallback(prompt)
            return {
                "content": demo_res,
                "is_cached": False,
                "is_demo": True,
                "quota_exhausted": True
            }

        # 2. CIRCUIT BREAKER FAST-FAIL CHECK
        with self.lock:
            cooldown = self._get_cooldown_seconds()
            if not self.gemini_available or self.circuit_open or self.quota_exhausted:
                time_since_failure = time.time() - self.last_failure_time
                if time_since_failure < cooldown:
                    print("[GeminiClient] Circuit OPEN - Gemini temporarily unavailable")
                    print("[GeminiClient] Skipping request - using cache/demo fallback")
                    demo_res = self._generate_demo_fallback(prompt)
                    self.cache[cache_key] = demo_res
                    result = {
                        "content": demo_res,
                        "is_cached": False,
                        "is_demo": True,
                        "quota_exhausted": True
                    }
                    holder["result"] = result
                    event.set()
                    self.in_flight.pop(cache_key, None)
                    return result
                else:
                    # Cooldown period elapsed: HALF-OPEN state (allow 1 trial test request)
                    print("[GeminiClient] Circuit HALF-OPEN - Cooldown elapsed. Testing Gemini availability...")

        # 3. Check if API key is missing
        if not self.llm or not self.api_key:
            print("[GeminiClient] API key missing. Circuit OPEN.")
            print("[GeminiClient] Skipping request - using cache/demo fallback")
            demo_res = self._generate_demo_fallback(prompt)
            result = {
                "content": demo_res,
                "is_cached": False,
                "is_demo": True,
                "quota_exhausted": True
            }
            with self.lock:
                self.circuit_open = True
                self.quota_exhausted = True
                self.gemini_available = False
                self.last_failure_time = time.time()
                self.cache[cache_key] = demo_res
                holder["result"] = result
                event.set()
                self.in_flight.pop(cache_key, None)
            return result

        # 4. Request Execution with Zero-Retry Quota Protection
        start_time = time.time()
        with self.lock:
            self.request_count += 1
        
        estimated_prompt_tokens = max(1, len(full_text) // 4)
        result = None
        actual_retries = max(1, min(max_retries, 2))

        for attempt in range(actual_retries):
            try:
                print(f"[GeminiClient LLM Call] Attempt {attempt + 1}/{actual_retries}")
                
                # Execute LLM call with a hard 10-second timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.llm.invoke, full_text)
                    response = future.result(timeout=10.0)
                
                # Extract text content safely
                content = ""
                raw_content = getattr(response, "content", response)
                if isinstance(raw_content, list):
                    text_parts = []
                    for item in raw_content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)
                    content = "\n".join(text_parts).strip()
                elif isinstance(raw_content, str):
                    content = raw_content.strip()
                else:
                    content = str(raw_content).strip()

                if not content:
                    raise ValueError("Received empty response from Gemini API.")

                latency = round(time.time() - start_time, 2)
                estimated_completion_tokens = max(1, len(content) // 4)

                with self.lock:
                    if self.circuit_open or not self.gemini_available:
                        print("[GeminiClient] Circuit CLOSED - Gemini service recovered!")
                    self.circuit_open = False
                    self.quota_exhausted = False
                    self.gemini_available = True
                    self.last_error = None
                    self.total_latency_seconds += latency
                    self.token_usage["prompt_tokens"] += estimated_prompt_tokens
                    self.token_usage["completion_tokens"] += estimated_completion_tokens
                    self.token_usage["total_tokens"] += (estimated_prompt_tokens + estimated_completion_tokens)
                    self.cache[cache_key] = content

                print(f"[GeminiClient SUCCESS] Completed in {latency}s")
                result = {
                    "content": content,
                    "is_cached": False,
                    "is_demo": False,
                    "quota_exhausted": False
                }
                break

            except Exception as e:
                err_msg = str(e)
                print(f"[GeminiClient Error - Attempt {attempt + 1}]: {err_msg}")
                with self.lock:
                    self.last_error = err_msg

                # Detect quota, 429, 499, cancellation, resource exhaustion, timeout, or invalid key
                is_quota_or_exhaustion = self._is_service_exhausted_error(e, err_msg)

                if is_quota_or_exhaustion:
                    with self.lock:
                        self.circuit_open = True
                        self.quota_exhausted = True
                        self.gemini_available = False
                        self.last_failure_time = time.time()
                    print("[GeminiClient] Circuit OPEN - Gemini temporarily unavailable")
                    print("[GeminiClient] Skipping request - using cache/demo fallback")
                    
                    demo_content = self._generate_demo_fallback(prompt)
                    with self.lock:
                        self.cache[cache_key] = demo_content
                    result = {
                        "content": demo_content,
                        "is_cached": False,
                        "is_demo": True,
                        "quota_exhausted": True
                    }
                    # FAST FAIL: Break loop immediately on quota failure. DO NOT RETRY!
                    break

                # Transient error retry (only if attempt < actual_retries - 1)
                if attempt < actual_retries - 1:
                    wait_time = 0.5
                    print(f"[GeminiClient Retrying] Transient error. Waiting {wait_time:.2f}s before retry...")
                    time.sleep(wait_time)

        if not result:
            demo_content = self._generate_demo_fallback(prompt)
            with self.lock:
                self.circuit_open = True
                self.quota_exhausted = True
                self.gemini_available = False
                self.last_failure_time = time.time()
                self.cache[cache_key] = demo_content
            print("[GeminiClient] Circuit OPEN - Gemini temporarily unavailable")
            print("[GeminiClient] Skipping request - using cache/demo fallback")
            result = {
                "content": demo_content,
                "is_cached": False,
                "is_demo": True,
                "quota_exhausted": True
            }

        # Complete in-flight deduplication event
        with self.lock:
            holder["result"] = result
            event.set()
            self.in_flight.pop(cache_key, None)

        return result

    def _generate_demo_fallback(self, prompt: str) -> str:
        """Generates realistic structured business responses when Gemini API quota is unavailable."""
        prompt_lower = prompt.lower()

        if "research" in prompt_lower or "market" in prompt_lower:
            return json.dumps({
                "market_demand": "High consumer interest observed across digital channels and specialized e-commerce platforms.",
                "competition": "Moderate to high competitive density with established incumbents and agile niche entrants.",
                "risk_level": "Medium",
                "key_insights": [
                    "Strong target demographic willingness to pay premium rates for customized solutions.",
                    "Supply chain lead times require active vendor diversification to protect gross margins.",
                    "Digital marketing acquisition costs are rising; organic content and referral loops are required."
                ],
                "opportunities": [
                    "Direct-to-Consumer subscription or bundle sales.",
                    "Strategic co-branding with regional macro-influencers."
                ]
            }, indent=2)

        elif "plan" in prompt_lower or "roadmap" in prompt_lower:
            return json.dumps([
                {
                    "phase": "PHASE 1 (Months 1-2)",
                    "title": "MVP Launch & Supplier Setup",
                    "description": "Establish supplier partnerships, complete brand positioning, and launch initial e-commerce platform."
                },
                {
                    "phase": "PHASE 2 (Months 3-4)",
                    "title": "Customer Acquisition & Optimization",
                    "description": "Scale digital ad campaigns, optimize conversion funnel, and establish customer support workflows."
                },
                {
                    "phase": "PHASE 3 (Months 5-6)",
                    "title": "Scaling & Channel Expansion",
                    "description": "Expand product variants, introduce referral rewards, and evaluate wholesale distribution channels."
                }
            ], indent=2)

        elif "follow" in prompt_lower or "question" in prompt_lower:
            return (
                "Based on the analysis, pursuing this initiative offers strong commercial upside provided customer "
                "acquisition costs (CAC) are controlled via targeted organic channels. Reducing operational overhead "
                "during Phase 1 preserves cash flow and minimizes market entry risk."
            )

        else:
            # Executive Decision Fallback
            return json.dumps({
                "viability_score": 78,
                "confidence": 84,
                "recommendation_title": "Proceed with Phased Market Launch",
                "executive_summary": (
                    "The business opportunity demonstrates solid market viability with favorable profit margins. "
                    "A disciplined phased rollout is recommended to manage initial inventory exposure and validate "
                    "customer acquisition cost assumptions."
                ),
                "why_this_decision": [
                    "High market demand with strong willingness to buy",
                    "Manageable break-even threshold within 4 to 6 months",
                    "Favorable product gross margins above 45%"
                ],
                "key_risks": [
                    "Rising customer acquisition costs on paid ad networks",
                    "Potential inventory holding costs if initial sales velocity lags"
                ],
                "key_opportunities": [
                    "Cross-selling accessory lines to increase Average Order Value (AOV)",
                    "Building brand loyalty through personalized customer experience"
                ]
            }, indent=2)

    def get_telemetry_metrics(self) -> dict:
        """Returns AI usage monitoring telemetry."""
        with self.lock:
            hit_rate = 0.0
            total_queries = self.request_count + self.cache_hits
            if total_queries > 0:
                hit_rate = round((self.cache_hits / total_queries) * 100, 1)

            avg_latency = 0.0
            if self.request_count > 0:
                avg_latency = round(self.total_latency_seconds / self.request_count, 2)

            return {
                "gemini_requests": self.request_count,
                "cached_responses": self.cache_hits,
                "cache_hit_rate_pct": hit_rate,
                "average_response_sec": avg_latency,
                "token_usage": dict(self.token_usage),
                "quota_exhausted": self.quota_exhausted,
                "mode": "DEMO/CACHE MODE (Quota Protected)" if self.quota_exhausted else "LIVE GEMINI API",
                "last_error": self.last_error
            }

# Global Singleton Instance
gemini_client = GeminiClient()


import os
import time
import random
import hashlib
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

class GeminiClient:
    """
    Centralized Gemini Client Wrapper.
    Handles caching, rate limits, exponential backoff, quota exhaustion detection,
    token usage tracking, and automatic DEMO/CACHE mode fallback.
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
                    max_output_tokens=4096
                )
            except Exception as e:
                print(f"[GeminiClient Warning] Failed to initialize ChatGoogleGenerativeAI: {e}")

        # In-memory Response Cache & Telemetry
        self.cache = {}
        self.request_count = 0
        self.cache_hits = 0
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.quota_exhausted = False
        self.last_error = None
        self.total_latency_seconds = 0.0

    def _normalize_prompt(self, prompt: str) -> str:
        """Create a normalized hash key for caching."""
        clean_text = " ".join(prompt.strip().lower().split())
        return hashlib.md5(clean_text.encode("utf-8")).hexdigest()

    def generate(self, prompt: str, system_instruction: str = "", max_retries: int = 3) -> dict:
        """
        Main entry point for all Gemini requests across all agents.
        Returns dict: {"content": str, "is_cached": bool, "is_demo": bool, "tokens": int}
        """
        full_text = f"{system_instruction}\n\n{prompt}".strip()
        cache_key = self._normalize_prompt(full_text)

        # 1. Check Response Cache
        if cache_key in self.cache:
            self.cache_hits += 1
            print(f"[GeminiClient CACHE HIT] Reusing cached response for query hash: {cache_key[:8]}")
            return {
                "content": self.cache[cache_key],
                "is_cached": True,
                "is_demo": False,
                "quota_exhausted": self.quota_exhausted
            }

        # 2. Check if API key is missing or quota is known to be exhausted
        if not self.llm or not self.api_key:
            print("[GeminiClient] API key missing. Switching to DEMO mode.")
            self.quota_exhausted = True
            demo_res = self._generate_demo_fallback(prompt)
            return {
                "content": demo_res,
                "is_cached": False,
                "is_demo": True,
                "quota_exhausted": True
            }

        # 3. Request Execution with Exponential Backoff
        start_time = time.time()
        self.request_count += 1
        
        # Estimate input tokens (~4 chars per token)
        estimated_prompt_tokens = max(1, len(full_text) // 4)

        for attempt in range(max_retries):
            try:
                print(f"[GeminiClient LLM Call] Attempt {attempt + 1}/{max_retries}")
                response = self.llm.invoke(full_text)
                
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
                self.total_latency_seconds += latency
                
                estimated_completion_tokens = max(1, len(content) // 4)
                self.token_usage["prompt_tokens"] += estimated_prompt_tokens
                self.token_usage["completion_tokens"] += estimated_completion_tokens
                self.token_usage["total_tokens"] += (estimated_prompt_tokens + estimated_completion_tokens)

                # Store in Cache
                self.cache[cache_key] = content
                self.quota_exhausted = False
                self.last_error = None

                print(f"[GeminiClient SUCCESS] Completed in {latency}s")
                return {
                    "content": content,
                    "is_cached": False,
                    "is_demo": False,
                    "quota_exhausted": False
                }

            except Exception as e:
                err_msg = str(e)
                print(f"[GeminiClient Error - Attempt {attempt + 1}]: {err_msg}")
                self.last_error = err_msg

                is_quota_err = (
                    "429" in err_msg or
                    "quota" in err_msg.lower() or
                    "resourceexhausted" in err_msg.lower() or
                    "rate limit" in err_msg.lower()
                )

                if is_quota_err or attempt == max_retries - 1:
                    if is_quota_err:
                        print("[GeminiClient QUOTA EXHAUSTED] Triggering DEMO/CACHE fallback mode.")
                        self.quota_exhausted = True
                    
                    # Fallback to demo/cache mode gracefully
                    demo_content = self._generate_demo_fallback(prompt)
                    self.cache[cache_key] = demo_content
                    return {
                        "content": demo_content,
                        "is_cached": False,
                        "is_demo": True,
                        "quota_exhausted": True
                    }

                # Exponential backoff delay
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"[GeminiClient Retrying] Waiting {wait_time:.2f}s before retry...")
                time.sleep(wait_time)

        # Fallback if loop ends unexpectedly
        demo_content = self._generate_demo_fallback(prompt)
        return {
            "content": demo_content,
            "is_cached": False,
            "is_demo": True,
            "quota_exhausted": True
        }

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
            "token_usage": self.token_usage,
            "quota_exhausted": self.quota_exhausted,
            "mode": "DEMO/CACHE MODE (Quota Protected)" if self.quota_exhausted else "LIVE GEMINI API",
            "last_error": self.last_error
        }

# Global Singleton Instance
gemini_client = GeminiClient()

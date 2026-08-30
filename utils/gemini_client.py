import os
import time
import hashlib
import json
import threading
import concurrent.futures
import re
import random
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


class GeminiClient:
    """
    Centralized Production-Ready Enterprise Gemini Client Wrapper.
    
    Features:
    - Environment-driven configurable model chain (Primary -> Fallback -> Lightweight)
    - Accurate error classification (AUTH, QUOTA, TRANSIENT, TIMEOUT, MODEL_NOT_FOUND)
    - 503 errors never permanently lock quota or disable availability
    - Bounded exponential backoff with jitter across retry attempts
    - 3-State Circuit Breaker (CLOSED, OPEN, HALF_OPEN) with automatic recovery probing
    - Strict caching policy: ONLY genuine LIVE AI responses are cached
    - No fabricated generic reports presented as live AI; returns clean structured retry responses
    - Transparent telemetry and health status monitoring (LIVE, TEMPORARILY_UNAVAILABLE, RATE_LIMITED, CONFIGURATION_ERROR, RECOVERING)
    """

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        
        # Priority Model Hierarchy configured via environment variables
        self.primary_model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
        self.fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
        self.lightweight_model = os.getenv("GEMINI_LIGHTWEIGHT_MODEL", "gemini-3.5-flash-lite")

        self.candidate_models = []
        for m in [self.primary_model, self.fallback_model, self.lightweight_model]:
            if m and m not in self.candidate_models:
                self.candidate_models.append(m)

        # Configurable Timeout (default 45.0s)
        try:
            self.timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "45.0"))
        except (ValueError, TypeError):
            self.timeout_seconds = 45.0

        # Configurable Cooldown (default 15.0s)
        try:
            self.cooldown_seconds = float(os.getenv("GEMINI_COOLDOWN_SECONDS", "15.0"))
        except (ValueError, TypeError):
            self.cooldown_seconds = 15.0

        # Configurable Consecutive Failure Threshold before opening circuit (default 3)
        try:
            self.failure_threshold = int(os.getenv("GEMINI_CIRCUIT_FAILURE_THRESHOLD", "3"))
        except (ValueError, TypeError):
            self.failure_threshold = 3

        # In-memory Response Cache & Deduplication
        self.cache: Dict[str, str] = {}
        self.in_flight: Dict[str, Tuple[threading.Event, Dict[str, Any]]] = {}
        self.lock = threading.Lock()

        # Shared Persistent Executor for bounded async execution
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="gemini_worker")

        # Telemetry counters
        self.request_count = 0
        self.cache_hits = 0
        self.fallback_count = 0
        self.failed_requests = 0
        self.total_latency_seconds = 0.0
        self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Circuit Breaker States: CLOSED, OPEN, HALF_OPEN
        self.circuit_state = "CLOSED"
        self.consecutive_failures = 0
        self.last_failure_time = 0.0
        self.probe_in_progress = False

        # Status flags
        self.quota_exhausted = False
        self.gemini_available = True if self.api_key else False
        self.last_error = None
        self.last_error_type = None

        # Initialize LLM instances
        self.llms = {}
        if self.api_key:
            self._init_models()
        else:
            self.gemini_available = False
            self.last_error = "GOOGLE_API_KEY environment variable is not set."
            self.last_error_type = "AUTH"

    def _init_models(self):
        """Initializes LangChain ChatGoogleGenerativeAI instances for all candidate models."""
        for m in self.candidate_models:
            try:
                self.llms[m] = ChatGoogleGenerativeAI(
                    model=m,
                    google_api_key=self.api_key,
                    temperature=0.3,
                    max_output_tokens=4096,
                    request_timeout=self.timeout_seconds
                )
            except Exception as e:
                print(f"[GeminiClient] Warning: Failed to init model '{m}': {e}")

    @property
    def circuit_open(self) -> bool:
        """Backward compatibility property for circuit state."""
        return self.circuit_state == "OPEN"

    @circuit_open.setter
    def circuit_open(self, value: bool):
        if value:
            self.circuit_state = "OPEN"
        else:
            self.circuit_state = "CLOSED"
            self.consecutive_failures = 0

    def _classify_error(self, e: Exception, err_msg: str) -> str:
        """
        Explicitly classifies Gemini errors into specific categories.
        Returns one of: 'AUTH', 'QUOTA', 'TIMEOUT', 'MODEL_NOT_FOUND', 'TRANSIENT', 'UNKNOWN'
        """
        msg_lower = err_msg.lower()

        # 1. Authentication / Configuration Errors (Permanent failures)
        auth_indicators = [
            "api_key_invalid", "invalid api key", "api key not valid", "unauthenticated",
            "permission_denied", "permissiondenied", "forbidden", "401", "403",
            "auth_missing", "unauthorized"
        ]
        if any(k in msg_lower for k in auth_indicators):
            return "AUTH"

        # 2. Rate / Quota Errors (Triggers controlled backoff and quota shielding)
        quota_indicators = [
            "resource_exhausted", "resourceexhausted", "quota", "rate limit", "429",
            "too many requests", "quota_exceeded", "exceeded your current quota"
        ]
        if any(k in msg_lower for k in quota_indicators):
            return "QUOTA"

        # 3. Model Not Found / Unsupported
        model_indicators = [
            "not_found", "notfound", "404", "is no longer available", "model not found",
            "is not supported", "unknown model"
        ]
        if any(k in msg_lower for k in model_indicators):
            return "MODEL_NOT_FOUND"

        # 4. Timeout
        if isinstance(e, (concurrent.futures.TimeoutError, TimeoutError)) or any(k in msg_lower for k in ["timed out", "timeout", "deadline exceeded", "deadlineexceeded"]):
            return "TIMEOUT"

        # 5. Temporary Service Overload / Server Errors
        transient_indicators = [
            "500", "502", "503", "504", "unavailable", "connection reset", "service unavailable",
            "temporary failure", "internal server error", "high demand", "currently experiencing high demand",
            "econnreset", "connection error", "remote disconnected", "server error"
        ]
        if any(k in msg_lower for k in transient_indicators):
            return "TRANSIENT"

        return "UNKNOWN"

    def _is_retryable(self, error_type: str) -> bool:
        """Determines if the error category qualifies for a transient retry."""
        return error_type in ("TRANSIENT", "TIMEOUT", "UNKNOWN")

    def _normalize_prompt(self, prompt: str) -> str:
        """Generates a consistent hash key for prompt caching."""
        clean_text = re.sub(r'\s+', ' ', prompt.strip().lower())
        return hashlib.md5(clean_text.encode("utf-8")).hexdigest()

    def _extract_text_content(self, response) -> str:
        """Robustly extracts text content from various response representations."""
        if response is None:
            return ""

        raw_content = getattr(response, "content", response)

        # Handle list of dicts (modern google-genai representation)
        if isinstance(raw_content, list):
            text_parts = []
            for item in raw_content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif "text" in item:
                        text_parts.append(str(item["text"]))
                elif isinstance(item, str):
                    text_parts.append(item)
                else:
                    text_parts.append(str(item))
            return "\n".join(text_parts).strip()

        # Handle string
        if isinstance(raw_content, str):
            return raw_content.strip()

        return str(raw_content).strip()

    def _invoke_with_backoff(self, full_text: str) -> Tuple[str, str]:
        """
        Executes bounded exponential backoff with jitter across candidate models:
        Primary (gemini-3.7-flash) -> Fallback (gemini-3.6-flash) -> Lightweight (gemini-3.5-flash-lite)
        
        Returns: (content_text, used_model_name)
        Raises: Exception if all attempts across all models fail
        """
        last_exc = None
        total_candidate_models = len(self.candidate_models)

        for model_idx, model_name in enumerate(self.candidate_models):
            llm_inst = self.llms.get(model_name)
            if not llm_inst:
                continue

            # Model attempt configuration: 2 attempts per candidate model
            max_attempts = 2
            for attempt in range(1, max_attempts + 1):
                print(f"[AI] Attempt {attempt}/{max_attempts} | Model: {model_name}")

                try:
                    # Submit to persistent worker pool to enforce timeout strictly
                    future = self._executor.submit(llm_inst.invoke, full_text)
                    response = future.result(timeout=self.timeout_seconds)

                    content = self._extract_text_content(response)
                    if content and len(content.strip()) > 10:
                        print(f"[AI] SUCCESS: Model '{model_name}' responded with {len(content)} chars.")
                        return content, model_name
                    else:
                        raise ValueError("Model returned empty or truncated response.")

                except Exception as e:
                    last_exc = e
                    err_msg = str(e)
                    err_type = self._classify_error(e, err_msg)

                    # Non-retryable error (e.g. Auth failure or permanent 401/403)
                    if err_type == "AUTH":
                        print(f"[AI] Permanent Authentication Error on '{model_name}': {err_msg[:120]}")
                        raise e

                    # Model not found -> immediately break to next fallback model
                    if err_type == "MODEL_NOT_FOUND":
                        print(f"[AI] Model '{model_name}' not available. Skipping to next candidate.")
                        break

                    # Rate limited -> break to fallback model
                    if err_type == "QUOTA":
                        print(f"[AI] Rate limit (429) on '{model_name}'. Switching to fallback chain.")
                        break

                    # If retryable transient error and attempts remain for this model
                    if self._is_retryable(err_type) and attempt < max_attempts:
                        # Bounded exponential backoff with jitter: ~1.0s, ~2.0s + jitter
                        base_backoff = 1.0 * (2 ** (attempt - 1))
                        jitter = random.uniform(0.1, 0.4)
                        delay = min(4.0, base_backoff + jitter)

                        status_label = "503" if "503" in err_msg or "high demand" in err_msg.lower() else err_type
                        print(f"[AI] Temporary error {status_label} | Retrying in {delay:.2f}s")
                        time.sleep(delay)
                    else:
                        print(f"[AI] Attempt {attempt} failed for '{model_name}' ({err_type}): {err_msg[:100]}")

            # Notify fallback model switch if another model exists in chain
            if model_idx + 1 < total_candidate_models:
                next_model = self.candidate_models[model_idx + 1]
                print(f"[AI] Switching to fallback model: {next_model}")

        if last_exc:
            raise last_exc
        raise RuntimeError("All candidate Gemini models failed to produce a valid response.")

    def generate(self, prompt: str, system_instruction: str = "", max_retries: int = 1, force_refresh: bool = False) -> dict:
        """
        Primary entry point for Gemini requests with error classification, circuit protection,
        and caching for genuine live AI responses.
        
        Returns dict:
        {
            "success": bool,
            "status": "ok" | "temporary_ai_unavailable" | "rate_limited" | "configuration_error",
            "content": str,
            "message": Optional[str],
            "retry_after_seconds": Optional[int],
            "is_cached": bool,
            "is_demo": bool,
            "quota_exhausted": bool,
            "source": "live" | "cache" | "unavailable" | "auth_error",
            "model": str,
            "error": Optional[str]
        }
        """
        full_text = f"{system_instruction}\n\n{prompt}".strip() if system_instruction else prompt.strip()
        cache_key = self._normalize_prompt(full_text)

        # 1. Check In-Memory Cache for Genuine Live Responses (Only if not force_refresh)
        if not force_refresh:
            with self.lock:
                if cache_key in self.cache:
                    self.cache_hits += 1
                    print(f"[GeminiClient CACHE HIT] Reusing cached live response ({cache_key[:8]})")
                    return {
                        "success": True,
                        "status": "ok",
                        "content": self.cache[cache_key],
                        "is_cached": True,
                        "is_demo": False,
                        "quota_exhausted": False,
                        "source": "cache",
                        "model": "cached",
                        "error": None
                    }

                # 2. In-flight Request Deduplication
                if cache_key in self.in_flight:
                    event, holder = self.in_flight[cache_key]
                    print(f"[GeminiClient DEDUPLICATION] Joining in-flight request ({cache_key[:8]})")
                    need_wait = True
                else:
                    event = threading.Event()
                    holder = {"result": None}
                    self.in_flight[cache_key] = (event, holder)
                    need_wait = False

            if need_wait:
                event.wait(timeout=self.timeout_seconds + 5.0)
                res = holder.get("result")
                if res:
                    with self.lock:
                        if res.get("success"):
                            self.cache_hits += 1
                    return res
                return {
                    "success": False,
                    "status": "temporary_ai_unavailable",
                    "message": "The AI analysis service is temporarily busy. Please try again in a moment.",
                    "retry_after_seconds": 15,
                    "content": "",
                    "is_cached": False,
                    "is_demo": False,
                    "quota_exhausted": self.quota_exhausted,
                    "source": "unavailable",
                    "model": "none",
                    "error": "In-flight request wait timeout"
                }
        else:
            with self.lock:
                event = threading.Event()
                holder = {"result": None}
                self.in_flight[cache_key] = (event, holder)

        # 3. Check Authentication Configuration
        if not self.api_key or not self.llms:
            print("[GeminiClient] Error: Google API key is missing or no models initialized.")
            with self.lock:
                self.gemini_available = False
                self.last_error = "GOOGLE_API_KEY is not configured or authentication failed."
                self.last_error_type = "AUTH"
                err_res = {
                    "success": False,
                    "status": "configuration_error",
                    "message": "Gemini API configuration or authentication error. Please check your API key.",
                    "retry_after_seconds": None,
                    "content": "",
                    "is_cached": False,
                    "is_demo": False,
                    "quota_exhausted": False,
                    "source": "auth_error",
                    "model": "none",
                    "error": self.last_error
                }
                holder["result"] = err_res
                event.set()
                self.in_flight.pop(cache_key, None)
                return err_res

        # 4. Check Circuit Breaker State (CLOSED, OPEN, HALF_OPEN)
        is_probe = False
        with self.lock:
            if self.circuit_state == "OPEN":
                time_since_failure = time.time() - self.last_failure_time
                if time_since_failure >= self.cooldown_seconds:
                    # Transition to HALF_OPEN: allow exactly one probe
                    if not self.probe_in_progress:
                        self.circuit_state = "HALF_OPEN"
                        self.probe_in_progress = True
                        is_probe = True
                        print(f"[GeminiClient] Circuit HALF-OPEN after {time_since_failure:.1f}s cooldown. Probing live API...")
                    else:
                        print(f"[GeminiClient] Circuit HALF-OPEN (probe in progress). Fast-failing concurrent request.")
                        err_res = self._build_temporary_unavailable_response(15)
                        holder["result"] = err_res
                        event.set()
                        self.in_flight.pop(cache_key, None)
                        return err_res
                else:
                    retry_wait = max(1, int(self.cooldown_seconds - time_since_failure))
                    print(f"[GeminiClient] Circuit OPEN (cooldown active, {retry_wait}s remaining). Fast-failing.")
                    err_res = self._build_temporary_unavailable_response(retry_wait)
                    holder["result"] = err_res
                    event.set()
                    self.in_flight.pop(cache_key, None)
                    return err_res

        # 5. Execute Live Request
        start_time = time.time()
        with self.lock:
            self.request_count += 1

        estimated_prompt_tokens = max(1, len(full_text) // 4)
        result = None

        try:
            content, used_model = self._invoke_with_backoff(full_text)
            latency = round(time.time() - start_time, 2)
            estimated_completion_tokens = max(1, len(content) // 4)

            with self.lock:
                # Probe or normal call succeeded: Reset circuit to CLOSED
                self.circuit_state = "CLOSED"
                self.consecutive_failures = 0
                self.probe_in_progress = False
                self.quota_exhausted = False
                self.gemini_available = True
                self.last_error = None
                self.last_error_type = None

                self.total_latency_seconds += latency
                self.token_usage["prompt_tokens"] += estimated_prompt_tokens
                self.token_usage["completion_tokens"] += estimated_completion_tokens
                self.token_usage["total_tokens"] += (estimated_prompt_tokens + estimated_completion_tokens)

                # Store ONLY genuine live responses in cache
                self.cache[cache_key] = content

            result = {
                "success": True,
                "status": "ok",
                "content": content,
                "is_cached": False,
                "is_demo": False,
                "quota_exhausted": False,
                "source": "live",
                "model": used_model,
                "error": None
            }

        except Exception as e:
            latency = round(time.time() - start_time, 2)
            err_msg = str(e)
            err_type = self._classify_error(e, err_msg)

            print(f"[GeminiClient Error] Request failed ({err_type}, {latency}s): {err_msg[:120]}")

            with self.lock:
                self.failed_requests += 1
                self.probe_in_progress = False
                self.last_error = err_msg
                self.last_error_type = err_type
                self.last_failure_time = time.time()

                if err_type == "AUTH":
                    self.gemini_available = False
                    self.circuit_state = "OPEN"
                    self.quota_exhausted = False
                elif err_type == "QUOTA":
                    self.quota_exhausted = True
                    self.circuit_state = "OPEN"
                elif err_type in ("TRANSIENT", "TIMEOUT"):
                    # 503 / Transient: NEVER set quota_exhausted = True
                    self.quota_exhausted = False
                    self.consecutive_failures += 1
                    # Open circuit only if threshold reached or if failed in HALF_OPEN state
                    if is_probe or self.circuit_state == "HALF_OPEN" or self.consecutive_failures >= self.failure_threshold:
                        self.circuit_state = "OPEN"
                        print(f"[GeminiClient] Circuit state transitioned to OPEN (consecutive failures: {self.consecutive_failures})")
                else:
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.failure_threshold:
                        self.circuit_state = "OPEN"

            if err_type == "QUOTA":
                result = {
                    "success": False,
                    "status": "rate_limited",
                    "message": "AI request rate limit reached. Please wait a moment before retrying.",
                    "retry_after_seconds": int(self.cooldown_seconds),
                    "content": "",
                    "is_cached": False,
                    "is_demo": False,
                    "quota_exhausted": True,
                    "source": "unavailable",
                    "model": "none",
                    "error": err_msg
                }
            elif err_type == "AUTH":
                result = {
                    "success": False,
                    "status": "configuration_error",
                    "message": "Gemini API configuration or authentication error. Please check your API key.",
                    "retry_after_seconds": None,
                    "content": "",
                    "is_cached": False,
                    "is_demo": False,
                    "quota_exhausted": False,
                    "source": "auth_error",
                    "model": "none",
                    "error": err_msg
                }
            else:
                result = self._build_temporary_unavailable_response(int(self.cooldown_seconds), err_msg)

        # Release in-flight holders
        with self.lock:
            holder["result"] = result
            event.set()
            self.in_flight.pop(cache_key, None)

        return result

    def _build_temporary_unavailable_response(self, retry_after: int = 15, error: Optional[str] = None) -> dict:
        """Constructs a standard structured response for temporary AI service unavailability."""
        return {
            "success": False,
            "status": "temporary_ai_unavailable",
            "message": "The AI analysis service is temporarily busy. Please try again in a moment.",
            "retry_after_seconds": retry_after,
            "content": "",
            "is_cached": False,
            "is_demo": False,
            "quota_exhausted": self.quota_exhausted,
            "source": "unavailable",
            "model": "none",
            "error": error or self.last_error or "Service temporarily unavailable"
        }

    def generate_offline_baseline(self, prompt: str) -> str:
        """
        Generates structured, baseline analysis clearly demarcated as 'OFFLINE BASELINE ANALYSIS'.
        Only used when offline baseline mode is explicitly requested.
        """
        topic = "Business Initiative"
        clean_p = prompt.strip()
        patterns = [
            r"Business Problem / Strategic Question:\s*(.+)",
            r"Business Problem:\s*(.+)",
            r"Question:\s*(.+)",
            r"Task:\s*(.+)"
        ]
        for pat in patterns:
            m = re.search(pat, clean_p, re.IGNORECASE)
            if m:
                topic = m.group(1).split("\n")[0].strip()
                break

        clean_topic = topic.strip("?.!")
        with self.lock:
            self.fallback_count += 1

        return json.dumps({
            "executive_summary": (
                f"[OFFLINE BASELINE ANALYSIS] Preliminary baseline assessment of '{clean_topic}' based on standard financial "
                f"and operational parameters. Live AI models were unavailable at time of request."
            ),
            "market_demand": f"Observed demand dynamics and customer interest for {clean_topic}.",
            "competition": f"Competitive landscape for {clean_topic} involves established market incumbents and niche alternatives.",
            "target_customer": [
                f"Primary customer segment seeking {clean_topic}",
                "Early adopters prioritizing specialized service delivery"
            ],
            "why_this_decision": [
                f"Identified baseline demand and positioning opportunity for {clean_topic}",
                "Manageable break-even threshold under disciplined operational spending",
                "Unit margin viability with controlled customer acquisition costs"
            ],
            "key_risks": [
                f"Market adoption friction and pricing sensitivity for {clean_topic}",
                "Customer acquisition cost inflation across paid digital channels"
            ],
            "key_opportunities": [
                f"Niche positioning advantage in the {clean_topic} domain",
                "Product or service bundling to expand customer lifetime value"
            ],
            "recommended_decision": f"RECOMMEND CONTROLLED PHASED VALIDATION FOR {clean_topic.upper()}",
            "implementation_roadmap": [
                {
                    "phase": "Phase 1 — Validate",
                    "steps": [
                        f"Validate baseline customer demand for {clean_topic}",
                        "Test pricing elasticity and supplier cost structure",
                        "Benchmark key competitors"
                    ]
                },
                {
                    "phase": "Phase 2 — Pilot",
                    "steps": [
                        f"Launch a controlled pilot for {clean_topic}",
                        "Track conversion rates, unit margin, and CAC",
                        "Incorporate direct customer feedback"
                    ]
                },
                {
                    "phase": "Phase 3 — Scale",
                    "steps": [
                        "Track monthly net profit against break-even targets",
                        "Expand distribution once positive contribution margins are validated"
                    ]
                }
            ],
            "success_metrics": [
                "Monthly Volume: >150 units / customers",
                "Target Net Margin: >25%",
                "Break-even Timeline: <6 months",
                "Customer Retention: >70%"
            ],
            "conditions_and_assumptions": [
                "Fixed overhead expenses remain within initial budget allocation",
                "Customer acquisition cost remains below targeted unit margin"
            ],
            "viability_score": 72,
            "confidence": 75,
            "conclusion": f"Baseline strategic modeling for '{clean_topic}' indicates viability under a disciplined execution framework."
        }, indent=2)

    def get_telemetry_metrics(self) -> dict:
        """
        Returns accurate AI usage monitoring telemetry with explicit status distinction:
        LIVE, TEMPORARILY_UNAVAILABLE, RATE_LIMITED, CONFIGURATION_ERROR, RECOVERING
        """
        with self.lock:
            total_queries = self.request_count + self.cache_hits
            hit_rate = round((self.cache_hits / total_queries) * 100, 1) if total_queries > 0 else 0.0
            avg_latency = round(self.total_latency_seconds / self.request_count, 2) if self.request_count > 0 else 0.0

            # Determine accurate operational status
            if not self.gemini_available or self.last_error_type == "AUTH":
                status = "CONFIGURATION_ERROR"
            elif self.quota_exhausted or self.last_error_type == "QUOTA":
                status = "RATE_LIMITED"
            elif self.circuit_state == "HALF_OPEN":
                status = "RECOVERING"
            elif self.circuit_state == "OPEN":
                status = "TEMPORARILY_UNAVAILABLE"
            else:
                status = "LIVE"

            return {
                "gemini_requests": self.request_count,
                "cached_responses": self.cache_hits,
                "fallback_responses": self.fallback_count,
                "failed_requests": self.failed_requests,
                "cache_hit_rate_pct": hit_rate,
                "average_response_sec": avg_latency,
                "token_usage": dict(self.token_usage),
                "circuit_state": self.circuit_state,
                "consecutive_failures": self.consecutive_failures,
                "quota_exhausted": self.quota_exhausted,
                "gemini_available": self.gemini_available,
                "status": status,
                "mode": status,
                "primary_model": self.primary_model,
                "fallback_model": self.fallback_model,
                "lightweight_model": self.lightweight_model,
                "model_chain": list(self.candidate_models),
                "last_error": self.last_error,
                "last_error_type": self.last_error_type
            }


# Global Singleton Instance
gemini_client = GeminiClient()

import sys
import os
import time
import json
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app as flask_app
from utils.gemini_client import GeminiClient, gemini_client
from agents.research_agent import _clean_and_parse_json, _validate_and_sanitize_schema, research_agent


class TestProductionResilience(unittest.TestCase):

    def setUp(self):
        self.app = flask_app.test_client()
        with gemini_client.lock:
            gemini_client.circuit_state = "CLOSED"
            gemini_client.consecutive_failures = 0
            gemini_client.quota_exhausted = False
            gemini_client.gemini_available = True if gemini_client.api_key else False
            gemini_client.last_error = None
            gemini_client.last_error_type = None
            gemini_client.cache.clear()

    # 1. Error Classification Tests
    def test_error_classification(self):
        client = GeminiClient()

        # 503 / Service Unavailable / High demand -> TRANSIENT (Never sets quota_exhausted)
        self.assertEqual(client._classify_error(Exception(), "503 UNAVAILABLE: This model is currently experiencing high demand."), "TRANSIENT")
        self.assertEqual(client._classify_error(Exception(), "500 Internal Server Error"), "TRANSIENT")
        self.assertEqual(client._classify_error(Exception(), "502 Bad Gateway"), "TRANSIENT")
        self.assertEqual(client._classify_error(TimeoutError(), "Deadline exceeded / connection reset"), "TIMEOUT")

        # 429 / Resource Exhausted -> QUOTA
        self.assertEqual(client._classify_error(Exception(), "429 ResourceExhausted: quota exceeded"), "QUOTA")
        self.assertEqual(client._classify_error(Exception(), "Too Many Requests"), "QUOTA")

        # 401 / 403 / Invalid Key -> AUTH
        self.assertEqual(client._classify_error(Exception(), "401 API_KEY_INVALID: invalid api key"), "AUTH")
        self.assertEqual(client._classify_error(Exception(), "403 Permission Denied"), "AUTH")

        # 404 / Model Not Found -> MODEL_NOT_FOUND
        self.assertEqual(client._classify_error(Exception(), "404 Model Not Found: model is no longer available"), "MODEL_NOT_FOUND")

    # 2. 503 Does Not Cause False Quota Exhaustion
    def test_503_does_not_set_quota_exhausted(self):
        client = GeminiClient()
        client.candidate_models = ["mock-model"]
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("503 UNAVAILABLE: This model is currently experiencing high demand.")
        client.llms["mock-model"] = mock_llm

        res = client.generate("Test prompt for 503")

        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("status"), "temporary_ai_unavailable")
        self.assertFalse(client.quota_exhausted, "503 error MUST NOT set quota_exhausted=True")
        self.assertFalse(res.get("quota_exhausted"), "Response must not report quota_exhausted")
        self.assertIn("temporarily busy", res.get("message"))

    # 3. Model Fallback Chain (Primary -> Fallback -> Lightweight)
    def test_model_fallback_chain(self):
        client = GeminiClient()
        client.candidate_models = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]

        primary_llm = MagicMock()
        primary_llm.invoke.side_effect = Exception("503 Service Unavailable")

        fallback_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = json.dumps({
            "executive_summary": "Successful response from fallback model.",
            "market_demand": "High",
            "competition": "Moderate",
            "target_customer": ["Startups"],
            "why_this_decision": ["Viable"],
            "key_risks": ["Competition"],
            "key_opportunities": ["Expansion"],
            "recommended_decision": "Proceed",
            "implementation_roadmap": [{"phase": "P1", "steps": ["Validate"]}],
            "success_metrics": ["Profit > 20000"],
            "conditions_and_assumptions": ["Stable cost"],
            "suggested_followups": ["What is CAC?"],
            "viability_score": 85,
            "confidence": 88,
            "conclusion": "Positive."
        })
        fallback_llm.invoke.return_value = mock_resp

        client.llms = {
            "gemini-3.7-flash": primary_llm,
            "gemini-3.6-flash": fallback_llm,
            "gemini-3.5-flash-lite": MagicMock()
        }

        res = client.generate("Test query for fallback chain")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("model"), "gemini-3.6-flash", "Should fallback to secondary model on primary 503")
        self.assertFalse(client.quota_exhausted)
        self.assertEqual(client.circuit_state, "CLOSED")

    # 4. 3-State Circuit Breaker (CLOSED -> OPEN -> HALF_OPEN -> CLOSED / OPEN)
    def test_circuit_breaker_transitions(self):
        client = GeminiClient()
        client.candidate_models = ["mock-model"]
        client.cooldown_seconds = 0.5
        client.failure_threshold = 2

        mock_llm = MagicMock()
        client.llms["mock-model"] = mock_llm

        # Initial State: CLOSED
        self.assertEqual(client.circuit_state, "CLOSED")

        # 1st failure: increments consecutive_failures to 1 (threshold is 2), stays CLOSED
        mock_llm.invoke.side_effect = Exception("503 High demand")
        res1 = client.generate("Query 1")
        self.assertFalse(res1.get("success"))
        self.assertEqual(client.consecutive_failures, 1)
        self.assertEqual(client.circuit_state, "CLOSED")

        # 2nd failure: reaches threshold 2 -> transitions to OPEN
        res2 = client.generate("Query 2")
        self.assertFalse(res2.get("success"))
        self.assertEqual(client.consecutive_failures, 2)
        self.assertEqual(client.circuit_state, "OPEN")

        # Fast-fail while cooldown is active
        res3 = client.generate("Query 3")
        self.assertFalse(res3.get("success"))
        self.assertEqual(res3.get("status"), "temporary_ai_unavailable")

        # Wait for cooldown to expire
        time.sleep(0.6)

        # Probe in HALF_OPEN state with successful response -> transitions to CLOSED
        mock_resp = MagicMock()
        mock_resp.content = json.dumps({"executive_summary": "Recovered response"})
        mock_llm.invoke.side_effect = None
        mock_llm.invoke.return_value = mock_resp

        res4 = client.generate("Probe query")
        self.assertTrue(res4.get("success"))
        self.assertEqual(client.circuit_state, "CLOSED")
        self.assertEqual(client.consecutive_failures, 0)

    # 5. Caching: Only Successful Live Responses are Cached
    def test_cache_policy_only_live_responses(self):
        client = GeminiClient()
        client.candidate_models = ["mock-model"]
        mock_llm = MagicMock()
        client.llms["mock-model"] = mock_llm

        # 1. Failed request is NOT cached
        mock_llm.invoke.side_effect = Exception("503 High Demand")
        res_fail = client.generate("Failed test prompt")
        self.assertFalse(res_fail.get("success"))
        self.assertEqual(len(client.cache), 0, "Failed request must not be stored in cache")

        # 2. Successful live request IS cached
        mock_resp = MagicMock()
        mock_resp.content = "Valid Live Response Content"
        mock_llm.invoke.side_effect = None
        mock_llm.invoke.return_value = mock_resp

        res_succ = client.generate("Successful test prompt")
        self.assertTrue(res_succ.get("success"))
        self.assertEqual(res_succ.get("source"), "live")
        self.assertEqual(len(client.cache), 1)

        # 3. Subsequent request hits cache and marks source as "cache"
        res_cached = client.generate("Successful test prompt")
        self.assertTrue(res_cached.get("success"))
        self.assertEqual(res_cached.get("source"), "cache")
        self.assertTrue(res_cached.get("is_cached"))

    # 6. Research Agent JSON Parsing Reliability
    def test_research_agent_json_parsing(self):
        # Markdown fenced JSON
        fenced_json = """```json
{
  "executive_summary": "Test summary",
  "viability_score": 85,
  "confidence": 90
}
```"""
        parsed = _clean_and_parse_json(fenced_json)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get("executive_summary"), "Test summary")

        # Trailing comma repair
        trailing_comma_json = """
{
  "executive_summary": "Trailing comma test",
  "target_customer": ["Segment A", "Segment B",],
  "viability_score": 75,
}
"""
        parsed_fixed = _clean_and_parse_json(trailing_comma_json)
        self.assertIsNotNone(parsed_fixed)
        self.assertEqual(parsed_fixed.get("executive_summary"), "Trailing comma test")

        # Empty / whitespace detection
        self.assertIsNone(_clean_and_parse_json(""))
        self.assertIsNone(_clean_and_parse_json("   \n\t  "))
        self.assertIsNone(_clean_and_parse_json("Plain text with no json"))

    # 7. Health Endpoint Status Distinction
    def test_health_statuses(self):
        # 1. LIVE
        with gemini_client.lock:
            gemini_client.gemini_available = True
            gemini_client.circuit_state = "CLOSED"
            gemini_client.quota_exhausted = False
            gemini_client.last_error_type = None

        res1 = self.app.get("/health")
        d1 = res1.get_json()
        self.assertEqual(d1.get("status"), "LIVE")

        # 2. TEMPORARILY_UNAVAILABLE
        with gemini_client.lock:
            gemini_client.circuit_state = "OPEN"
            gemini_client.last_error_type = "TRANSIENT"

        res2 = self.app.get("/health")
        d2 = res2.get_json()
        self.assertEqual(d2.get("status"), "TEMPORARILY_UNAVAILABLE")

        # 3. RATE_LIMITED
        with gemini_client.lock:
            gemini_client.circuit_state = "OPEN"
            gemini_client.quota_exhausted = True
            gemini_client.last_error_type = "QUOTA"

        res3 = self.app.get("/health")
        d3 = res3.get_json()
        self.assertEqual(d3.get("status"), "RATE_LIMITED")

        # 4. CONFIGURATION_ERROR
        with gemini_client.lock:
            gemini_client.gemini_available = False
            gemini_client.last_error_type = "AUTH"

        res4 = self.app.get("/health")
        d4 = res4.get_json()
        self.assertEqual(d4.get("status"), "CONFIGURATION_ERROR")

        # 5. RECOVERING
        with gemini_client.lock:
            gemini_client.gemini_available = True
            gemini_client.circuit_state = "HALF_OPEN"
            gemini_client.quota_exhausted = False
            gemini_client.last_error_type = None

        res5 = self.app.get("/health")
        d5 = res5.get_json()
        self.assertEqual(d5.get("status"), "RECOVERING")


if __name__ == "__main__":
    unittest.main()

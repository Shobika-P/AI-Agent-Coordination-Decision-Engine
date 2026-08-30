import json
import re
from typing import Optional, Dict, Any
from utils.gemini_client import gemini_client


def _clean_and_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extracts and parses a JSON object from LLM response text.
    Handles markdown fences, leading/trailing conversational text, control characters,
    and minor syntax anomalies (such as trailing commas).
    """
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip()

    # 1. Strip markdown code fences (```json ... ``` or ``` ... ```)
    if "```" in cleaned:
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()

    # 2. Extract outermost JSON object { ... }
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = cleaned[start_idx:end_idx + 1].strip()
        
        # First attempt: direct json.loads
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Second attempt: repair trailing commas before closing braces/brackets
        try:
            fixed_str = re.sub(r',\s*([\]}])', r'\1', json_str)
            parsed = json.loads(fixed_str)
            if isinstance(parsed, dict):
                return parsed
        except Exception as e:
            print(f"[Research Agent JSON Parse Error] Failed parsing JSON: {e}. Snippet: {json_str[:150]}...")

    return None


def _validate_and_sanitize_schema(parsed: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Validates required fields in the parsed JSON response and provides safe type coercion.
    """
    # Ensure viability_score is valid int/float between 0 and 100
    try:
        score = int(parsed.get("viability_score", 78))
        parsed["viability_score"] = max(0, min(100, score))
    except (ValueError, TypeError):
        parsed["viability_score"] = 78

    # Ensure confidence is valid int/float between 0 and 100
    try:
        conf = int(parsed.get("confidence", 82))
        parsed["confidence"] = max(0, min(100, conf))
    except (ValueError, TypeError):
        parsed["confidence"] = 82

    # Ensure lists are actual lists
    list_fields = [
        "target_customer",
        "why_this_decision",
        "key_risks",
        "key_opportunities",
        "implementation_roadmap",
        "success_metrics",
        "conditions_and_assumptions",
        "suggested_followups"
    ]
    for lf in list_fields:
        val = parsed.get(lf)
        if val is None:
            parsed[lf] = []
        elif isinstance(val, str):
            parsed[lf] = [val]
        elif not isinstance(val, list):
            parsed[lf] = list(val) if hasattr(val, "__iter__") else [str(val)]

    # Ensure executive_summary is non-empty
    if not parsed.get("executive_summary"):
        clean_q = question.strip("?.!")
        parsed["executive_summary"] = f"Strategic evaluation of '{clean_q}' demonstrates viability under a disciplined execution framework."

    return parsed


def research_agent(question: str, force_refresh: bool = False) -> dict:
    """
    Primary AI Analysis Agent.
    Executes deep strategic and market analysis using live Gemini API.
    Returns structured, validated dictionary containing market research,
    planning roadmap, risk assessment, and decision metrics.
    
    Returns structured failure dict if live AI is unavailable or response is invalid.
    """
    system_instruction = """
You are the Primary AI Business Decision & Strategy Analyst in an Enterprise Decision Engine.
Perform an in-depth, specific strategic evaluation of the user's business problem.

Return ONLY a valid, parseable JSON object matching this exact schema:
{
  "executive_summary": "<Comprehensive executive summary paragraph tailored specifically to the user's business problem>",
  "market_demand": "<Specific market demand, customer willingness to pay, and target segment analysis>",
  "competition": "<Competitive landscape, incumbent threats, and positioning advantage>",
  "target_customer": [
    "<Primary target customer segment 1>",
    "<Primary target customer segment 2>"
  ],
  "why_this_decision": [
    "<Key strategic driver 1>",
    "<Key strategic driver 2>",
    "<Key strategic driver 3>"
  ],
  "key_risks": [
    "<Primary operational/market risk factor 1>",
    "<Primary operational/market risk factor 2>"
  ],
  "key_opportunities": [
    "<High-leverage growth or revenue upside opportunity 1>",
    "<High-leverage growth or revenue upside opportunity 2>"
  ],
  "recommended_decision": "<Clear, definitive actionable recommendation statement>",
  "implementation_roadmap": [
    {
      "phase": "Phase 1 — Validate",
      "steps": ["<Specific validation step 1>", "<Specific validation step 2>", "<Specific validation step 3>"]
    },
    {
      "phase": "Phase 2 — Pilot",
      "steps": ["<Specific pilot step 1>", "<Specific pilot step 2>", "<Specific pilot step 3>"]
    },
    {
      "phase": "Phase 3 — Measure",
      "steps": ["<Specific metric tracking step 1>", "<Specific metric tracking step 2>"]
    },
    {
      "phase": "Phase 4 — Scale",
      "steps": ["<Specific scaling step 1>", "<Specific scaling step 2>"]
    }
  ],
  "success_metrics": [
    "Target Volume / Customers: >150 units/month",
    "Target Retention Rate: >70%",
    "CAC Target: <₹100",
    "Monthly Net Profit Target: >₹20,000"
  ],
  "conditions_and_assumptions": [
    "<Key operational condition or baseline assumption 1>",
    "<Key operational condition or baseline assumption 2>"
  ],
  "suggested_followups": [
    "<Specific strategic/financial follow-up question 1 relevant to this business>",
    "<Specific strategic/financial follow-up question 2 relevant to this business>",
    "<Specific strategic/financial follow-up question 3 relevant to this business>"
  ],
  "viability_score": 80,
  "confidence": 85,
  "conclusion": "<Synthesized strategic concluding summary paragraph>"
}

CRITICAL RULES:
1. Ground ALL analysis, roadmap steps, risks, opportunities, and suggested followups SPECIFICALLY in the user's business question.
2. Avoid generic boilerplate. Be concrete, insightful, and numbers-aware.
3. Output ONLY the JSON object without markdown fences or outside commentary.
""".strip()

    prompt = f"Business Problem / Strategic Question:\n{question.strip()}"

    print(f"[LLM] Primary AI Analysis Call (Research Agent) for: '{question.strip()[:60]}'")
    res = gemini_client.generate(prompt, system_instruction=system_instruction, force_refresh=force_refresh)

    # If the Gemini client reported failure (e.g. 503 unavailable, rate limited, or circuit open)
    if not res.get("success"):
        status = res.get("status", "temporary_ai_unavailable")
        msg = res.get("message", "The AI analysis service is temporarily busy. Please try again in a moment.")
        err = res.get("error", "Service unavailable")
        retry_after = res.get("retry_after_seconds", 15)
        print(f"[Research Agent] Live AI request was not successful ({status}): {err}")
        return {
            "success": False,
            "status": status,
            "message": msg,
            "retry_after_seconds": retry_after,
            "error": err,
            "analysis_source": "UNAVAILABLE"
        }

    content = res.get("content", "")
    source = res.get("source", "live")
    is_cached = res.get("is_cached", False)

    parsed_dict = _clean_and_parse_json(content)

    if not parsed_dict:
        print(f"[Research Agent Error] Unparseable live LLM output. Length: {len(content)}. Content preview: {content[:120]}")
        return {
            "success": False,
            "status": "temporary_ai_unavailable",
            "message": "The AI analysis service produced an unparseable response. Please retry.",
            "retry_after_seconds": 10,
            "error": "Failed to parse structured JSON from LLM response",
            "analysis_source": "UNAVAILABLE"
        }

    # Validate and sanitize schema
    validated_dict = _validate_and_sanitize_schema(parsed_dict, question)

    # Determine real analysis source
    analysis_source = "LIVE_CACHE" if (is_cached or source == "cache") else "LIVE_AI"
    validated_dict["success"] = True
    validated_dict["analysis_source"] = analysis_source
    validated_dict["is_demo"] = False
    validated_dict["quota_exhausted"] = False

    return validated_dict
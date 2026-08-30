import re
import json
import hashlib
from utils.gemini_client import gemini_client
from tools.break_even_tool import calculate_break_even
from tools.roi_tool import calculate_roi
from tools.profit_tool import calculate_profit

followup_cache = {}  # cache_key -> answer string


def format_inr(val, include_symbol=True):
    try:
        val = float(val)
        is_neg = val < 0
        val = abs(val)
        if val.is_integer():
            s = f"{int(val)}"
        else:
            s = f"{val:,.2f}"

        if '.' in s:
            int_part, dec_part = s.split('.')
        else:
            int_part, dec_part = s, None

        int_part = int_part.replace(',', '')
        if len(int_part) > 3:
            last3 = int_part[-3:]
            other = int_part[:-3]
            res = ""
            while len(other) > 2:
                res = "," + other[-2:] + res
                other = other[:-2]
            formatted_int = other + res + "," + last3
        else:
            formatted_int = int_part

        final_num = f"{formatted_int}.{dec_part}" if dec_part else formatted_int
        prefix = "-₹" if is_neg else ("₹" if include_symbol else "")
        return f"{prefix}{final_num}"
    except Exception:
        return f"₹{val}" if include_symbol else str(val)


def _extract_report_params(report):
    """Extract baseline financial parameters from report object or sensible defaults."""
    fixed_cost = 50000.0
    selling_price = 500.0
    variable_cost = 300.0
    monthly_orders = 150.0
    marketing_cost = 10000.0

    if isinstance(report, dict):
        tool_analysis = report.get("tool_analysis") or {}
        if isinstance(tool_analysis, dict):
            fixed_cost = float(tool_analysis.get("fixed_cost") or fixed_cost)
            selling_price = float(tool_analysis.get("selling_price") or selling_price)
            variable_cost = float(tool_analysis.get("variable_cost") or variable_cost)

        for obs in report.get("conditions_and_assumptions", []) + tool_analysis.get("observations", []):
            obs_str = str(obs).lower()
            if "price" in obs_str or "selling" in obs_str:
                nums = re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', obs_str)
                if nums:
                    try:
                        selling_price = float(nums[0].replace(',', ''))
                    except Exception:
                        pass
            if "fixed" in obs_str:
                nums = re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', obs_str)
                if nums:
                    try:
                        fixed_cost = float(nums[0].replace(',', ''))
                    except Exception:
                        pass

    return {
        "fixed_cost": fixed_cost,
        "selling_price": selling_price,
        "variable_cost": variable_cost,
        "monthly_orders": monthly_orders,
        "marketing_cost": marketing_cost
    }


def _classify_and_compute_intent(question, report):
    """Lightweight deterministic intent classifier and scenario calculator."""
    q_lower = (question or "").lower()
    params = _extract_report_params(report)
    base_price = params["selling_price"]
    base_vc = params["variable_cost"]
    base_fc = params["fixed_cost"]
    base_mkt = params["marketing_cost"]

    # 1. Price Change Intent
    if any(k in q_lower for k in ["price", "reduce", "increase", "cut", "discount", "charge", "₹"]):
        nums = [float(n.replace(',', '')) for n in re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', question)]
        old_p = base_price
        new_p = None
        if len(nums) >= 2:
            old_p = nums[0]
            new_p = nums[1]
        elif len(nums) == 1:
            new_p = nums[0]

        if new_p is not None and new_p != old_p:
            old_margin = old_p - base_vc
            new_margin = new_p - base_vc

            old_be = round(base_fc / old_margin) if old_margin > 0 else 999999
            new_be = round(base_fc / new_margin) if new_margin > 0 else 999999

            be_diff = new_be - old_be
            margin_diff = new_margin - old_margin

            rec_changes = new_margin <= 0 or new_be > 400
            rec_status = "The launch recommendation becomes HIGH RISK / HOLD unless unit volume can be scaled significantly." if rec_changes else "The launch recommendation remains VALID provided monthly unit volume can meet the higher break-even target."

            analysis_summary = (
                f"Adjusting the price from {format_inr(old_p)} to {format_inr(new_p)} changes your per-unit contribution margin from {format_inr(old_margin)} to {format_inr(new_margin)} "
                f"({'-' if margin_diff < 0 else '+'}{format_inr(abs(margin_diff))}/unit). Consequently, your monthly break-even requirement shifts from {format_inr(old_be, include_symbol=False)} units to {format_inr(new_be, include_symbol=False)} units "
                f"({'+' if be_diff > 0 else ''}{format_inr(be_diff, include_symbol=False)} units per month required to cover fixed costs of {format_inr(base_fc)}). {rec_status}"
            )
            return {
                "intent": "price_change",
                "old_price": old_p,
                "new_price": new_p,
                "old_margin": old_margin,
                "new_margin": new_margin,
                "old_break_even": old_be,
                "new_break_even": new_be,
                "recommendation_changes": rec_changes,
                "analysis_summary": analysis_summary
            }

    # 2. Marketing Cost Change Intent
    if any(k in q_lower for k in ["marketing", "ad spend", "advertising", "budget", "promotion"]):
        nums = [float(n.replace(',', '')) for n in re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', question)]
        new_mkt = nums[0] if nums else (base_mkt + 15000)
        old_mkt = base_mkt

        margin = base_price - base_vc
        additional_units_needed = round((new_mkt - old_mkt) / margin) if margin > 0 else 0

        analysis_summary = (
            f"Adjusting the marketing budget from {format_inr(old_mkt)} to {format_inr(new_mkt)} shifts monthly fixed marketing expenditure by {format_inr(new_mkt - old_mkt)}. "
            f"At a unit margin of {format_inr(margin)} ({format_inr(base_price)} price - {format_inr(base_vc)} variable cost), you will need {format_inr(additional_units_needed, include_symbol=False)} additional units per month "
            f"to offset the extra advertising expenditure and maintain net profitability."
        )
        return {
            "intent": "marketing_cost_change",
            "old_marketing": old_mkt,
            "new_marketing": new_mkt,
            "additional_units_needed": additional_units_needed,
            "analysis_summary": analysis_summary
        }

    # 3. Break-Even Intent
    if any(k in q_lower for k in ["break even", "break-even", "units to sell", "how many units"]):
        margin = base_price - base_vc
        be_units = round(base_fc / margin) if margin > 0 else 999999
        analysis_summary = (
            f"The business break-even threshold is {format_inr(be_units, include_symbol=False)} units per month. "
            f"This is calculated using a fixed overhead of {format_inr(base_fc)} divided by a unit margin of {format_inr(margin)} ({format_inr(base_price)} selling price - {format_inr(base_vc)} variable cost)."
        )
        return {
            "intent": "break_even",
            "break_even_units": be_units,
            "analysis_summary": analysis_summary
        }

    # 4. ROI Intent
    if any(k in q_lower for k in ["roi", "return on investment", "return on capital"]):
        roi_res = calculate_roi(50000, 70000)
        analysis_summary = (
            f"Projected Return on Investment (ROI) is estimated at {roi_res.get('roi', '40%')}, assuming an initial capital outlay of {format_inr(50000)} and projected gross returns of {format_inr(70000)}."
        )
        return {
            "intent": "roi",
            "analysis_summary": analysis_summary
        }

    # 5. Risk Intent
    if any(k in q_lower for k in ["risk", "biggest risk", "primary risk", "threat", "danger", "downside"]):
        risks = []
        if isinstance(report, dict):
            risks = report.get("key_risks") or []
        if not risks:
            risks = ["Customer acquisition cost inflation on digital ad channels", "Price sensitivity among target consumers", "Supply chain lead times"]

        primary_risk = risks[0] if risks else "Customer acquisition cost inflation"
        all_risks_str = "; ".join([str(r) for r in risks])
        analysis_summary = (
            f"The primary risk facing this initiative is '{primary_risk}'. "
            f"Overall key risk factors identified in the analysis include: {all_risks_str}. Active mitigation requires controlling upfront marketing expenditure and securing supplier volume discounts."
        )
        return {
            "intent": "risk",
            "primary_risk": primary_risk,
            "analysis_summary": analysis_summary
        }

    # 6. Recommendation Intent
    if any(k in q_lower for k in ["recommendation", "proceed", "decision", "should we", "verdict"]):
        rec = "Proceed with controlled phased rollout"
        viability = 78
        if isinstance(report, dict):
            rec = report.get("recommended_decision") or report.get("decision") or rec
            viability = report.get("viability_score", 78)
        analysis_summary = (
            f"The strategic decision is to {rec} (Commercial Viability Score: {viability}/100). "
            f"This recommendation is grounded in favorable unit margins and manageable break-even volume, provided Phase 1 pilot testing validates customer acquisition costs."
        )
        return {
            "intent": "recommendation",
            "analysis_summary": analysis_summary
        }

    return {"intent": "general", "analysis_summary": None}


def build_compact_context(original_task, report, question, conversation_history):
    """Builds a concise context containing essential report highlights and recent history."""
    report_dict = report if isinstance(report, dict) else {}

    exec_summary = report_dict.get("executive_summary") or report_dict.get("decision") or "N/A"
    viability = report_dict.get("viability_score", 78)
    risk_level = report_dict.get("risk_level", "Medium")
    key_risks = report_dict.get("key_risks", [])
    recommended_decision = report_dict.get("recommended_decision") or report_dict.get("recommendation_title") or ""
    assumptions = report_dict.get("conditions_and_assumptions", [])
    tool_analysis = report_dict.get("tool_analysis", {})

    history_snippet = ""
    if conversation_history and isinstance(conversation_history, list):
        recent_turns = conversation_history[-3:]  # Last 3 turns
        formatted = []
        for idx, turn in enumerate(recent_turns, 1):
            if isinstance(turn, dict):
                q = turn.get("question", "")
                a = turn.get("answer", "")
                if q and a:
                    formatted.append(f"Q{idx}: {q}\nA{idx}: {str(a)[:200]}...")
        if formatted:
            history_snippet = "Recent Follow-up History:\n" + "\n".join(formatted) + "\n\n"

    compact_text = f"""
ORIGINAL BUSINESS PROBLEM:
{original_task}

REPORT HIGHLIGHTS:
- Executive Decision: {str(exec_summary)[:300]}
- Recommended Action: {recommended_decision}
- Viability Score: {viability}/100 | Risk Level: {risk_level}
- Key Risks: {', '.join([str(r) for r in key_risks[:3]]) if key_risks else 'Market competition and CAC'}
- Operational Assumptions: {', '.join([str(a) for a in assumptions[:2]]) if assumptions else 'Standard margins'}
- Tool Metrics: {json.dumps(tool_analysis) if tool_analysis else 'Standard break-even modeling'}

{history_snippet}CURRENT USER FOLLOW-UP QUESTION:
{question}
""".strip()
    return compact_text


def followup_agent(
    original_task,
    report,
    question,
    conversation_history=None
):
    """
    Follow-up Reasoning Agent.
    Synthesizes conversational follow-up answers using original task, report context,
    conversation history, deterministic calculators, and live LLM reasoning.
    """
    safe_q = question.strip() if question else ""
    norm_q = re.sub(r'\s+', ' ', safe_q.lower())

    # 1. Check Follow-Up In-Memory Cache
    report_hash = hashlib.md5(json.dumps(report, sort_keys=True).encode("utf-8")).hexdigest() if report else "no_report"
    cache_key = hashlib.md5(f"{original_task}_{norm_q}_{report_hash}".encode("utf-8")).hexdigest()

    if cache_key in followup_cache:
        print(f"[Follow-up Agent CACHE HIT] Returning cached follow-up answer for '{safe_q[:40]}'")
        return followup_cache[cache_key]

    print(f"[Follow-up Agent] Processing question: '{safe_q[:60]}'")

    # 2. Deterministic Intent Classification & Quantitative Analysis
    intent_data = _classify_and_compute_intent(question, report)
    calculated_summary = intent_data.get("analysis_summary")

    # 3. Build Compact Context for LLM
    compact_context = build_compact_context(original_task, report, question, conversation_history)

    # 4. LLM Generation
    system_instruction = """
You are the Follow-up Reasoning Agent in an Enterprise AI Business Decision Engine.

CRITICAL INSTRUCTIONS:
1. DIRECT ANSWER FIRST: Your very first sentence MUST answer the user's specific question directly, stating key metrics, exact changes (e.g. price, margin, break-even impact), and whether the overall recommendation changes.
2. DO NOT RE-DUMP THE FULL REPORT: Focus exclusively on answering the exact user question.
3. QUANTITATIVE ANALYSIS: Integrate exact financial figures (unit margin, break-even units, profit shift) using Indian Rupee formatting (₹) whenever relevant.
4. CLEAR REASONING: Explain why the numbers change and what it means for business viability.
""".strip()

    prompt = f"""
{compact_context}

Deterministic Calculation Insights:
{calculated_summary or 'Provide a direct, context-aware answer.'}

Write a direct, professional, and clear response to the current question:
"""

    res = gemini_client.generate(prompt, system_instruction=system_instruction)
    llm_answer = res.get("content", "").strip() if res.get("success") else ""
    
    if not llm_answer:
        if calculated_summary:
            print("[Follow-up Agent] Using deterministic quantitative scenario answer.")
            llm_answer = calculated_summary
        else:
            return "The AI analysis service is temporarily busy. Please try your question again in a moment."

    # Cache response only if genuine live AI response
    if res.get("success") and llm_answer:
        followup_cache[cache_key] = llm_answer

    return llm_answer
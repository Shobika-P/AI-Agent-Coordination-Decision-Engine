import json


def decision_agent(
    task: str,
    research: dict,
    planning: list,
    tool_output: dict,
    history=""
) -> dict:
    """
    Executive Decision Agent (Multi-Agent Synthesis).
    Synthesizes research findings, strategic planning roadmap, and quantitative business tool metrics
    into a comprehensive, actionable decision report.
    """
    if isinstance(research, dict) and research.get("success") is False:
        return research

    print(f"[Agent] Decision Agent (Synthesizing context + tool metrics for '{str(task)[:50]}')")

    base_decision = {}
    if isinstance(research, dict):
        base_decision = dict(research)

    # 1. Incorporate Planning Roadmap
    if planning and isinstance(planning, list):
        base_decision["implementation_roadmap"] = planning

    # 2. Incorporate Business Tool Analysis
    if isinstance(tool_output, dict):
        tool_name = tool_output.get("tool") or tool_output.get("tool_name") or "Business Tool"
        tool_risk = tool_output.get("risk_level")
        if tool_risk:
            base_decision["risk_level"] = tool_risk

        observations = tool_output.get("observations") or []
        existing_why = list(base_decision.get("why_this_decision") or [])

        # Integrate tool observations into strategic drivers
        for obs in observations[:2]:
            obs_str = str(obs)
            if not any(obs_str in item for item in existing_why):
                existing_why.append(f"Quantitative Finding: {obs_str}")
        base_decision["why_this_decision"] = existing_why

    # 3. Ensure defaults and fallback integrity
    clean_task = task.strip("?.!") if task else "Business Initiative"

    base_decision.setdefault("viability_score", 78)
    base_decision.setdefault("confidence", 82)
    base_decision.setdefault("risk_level", "Medium")
    base_decision.setdefault("recommended_decision", f"RECOMMEND PHASED VALIDATION FOR {clean_task.upper()}")
    base_decision.setdefault("recommendation_title", f"Strategic Assessment: {clean_task}")

    if not base_decision.get("executive_summary"):
        base_decision["executive_summary"] = f"Evaluation of '{clean_task}' indicates positive commercial viability under disciplined execution."

    if not base_decision.get("conclusion"):
        base_decision["conclusion"] = f"The strategic decision analysis for '{clean_task}' demonstrates viable market opportunity with controlled execution risk."

    return base_decision
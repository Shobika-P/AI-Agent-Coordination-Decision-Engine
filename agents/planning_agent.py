import json


def planning_agent(task: str, research: dict) -> list:
    """
    Business Planning Agent (Strategic Execution Roadmap).
    Extracts, structures, and validates the multi-phase execution roadmap from research context.
    Provides deterministic structure without unnecessary extra LLM latency.
    """
    if isinstance(research, dict) and research.get("success") is False:
        return []

    print(f"[Agent] Planning Agent (Structuring roadmap for: '{str(task)[:50]}')")

    if isinstance(research, dict):
        roadmap = research.get("implementation_roadmap")
        if roadmap and isinstance(roadmap, list) and len(roadmap) > 0:
            formatted_roadmap = []
            for idx, phase_item in enumerate(roadmap):
                if isinstance(phase_item, dict):
                    phase_title = phase_item.get("phase") or phase_item.get("title") or f"Phase {idx + 1}"
                    steps = phase_item.get("steps") or phase_item.get("description") or []
                    if isinstance(steps, str):
                        steps = [steps]
                    formatted_roadmap.append({
                        "phase": phase_title,
                        "steps": list(steps)
                    })
                elif isinstance(phase_item, str):
                    formatted_roadmap.append({
                        "phase": f"Phase {idx + 1}",
                        "steps": [phase_item]
                    })
            if formatted_roadmap:
                return formatted_roadmap

    clean_task = task.strip("?.!") if task else "Business Initiative"
    return [
        {
            "phase": "Phase 1 — Market Validation",
            "steps": [
                f"Validate target customer demand for {clean_task}",
                "Test baseline pricing elasticity and customer willingness to pay",
                "Conduct competitor benchmarking and differentiation analysis"
            ]
        },
        {
            "phase": "Phase 2 — Pilot Launch",
            "steps": [
                f"Execute a controlled pilot deployment for {clean_task}",
                "Track customer acquisition cost (CAC), conversion funnel, and unit economics",
                "Collect direct customer feedback and iterate on product/service offerings"
            ]
        },
        {
            "phase": "Phase 3 — Unit Margin & Break-even Optimization",
            "steps": [
                "Track monthly net profit against calculated break-even unit targets",
                "Optimize supplier contracts and variable operational expenses"
            ]
        },
        {
            "phase": "Phase 4 — Scaled Growth",
            "steps": [
                f"Scale distribution channels and marketing investment for {clean_task}",
                "Establish customer retention loops and referral incentives"
            ]
        }
    ]
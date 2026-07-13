from agents.research_agent import research_agent
from agents.planning_agent import planning_agent


def coordination_agent(task):
    """
    Coordinates multiple AI agents.
    """

    print("\nRunning Research Agent...\n")
    research_result = research_agent(task)

    print("\nRunning Planning Agent...\n")
    planning_result = planning_agent(task)

    final_output = f"""
=============================
 COORDINATION AGENT OUTPUT
=============================

Research Agent Result:

{research_result}


Planning Agent Result:

{planning_result}
"""

    return final_output
    
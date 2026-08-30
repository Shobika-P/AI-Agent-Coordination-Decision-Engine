from agents.research_agent import research_agent
from agents.planning_agent import planning_agent
from agents.decision_agent import decision_agent
from tools.calculator_tool import calculator_tool
from tools.tool_manager import execute_tool


def coordination_agent(task):
    """
    Coordinates AI agents and tools based on the task.
    """

    print("\n" + "=" * 50)
    print("COORDINATION ENGINE")
    print("=" * 50)

    print(f"\nTask: {task}")

    # Tool execution for direct arithmetic
    if any(operator in task for operator in ["+", "-", "*", "/"]) and any(c.isdigit() for c in task):
        print("\n[Tool] Calculator")
        print("-" * 50)

        result = calculator_tool(task)

        return f"""
{"=" * 50}
COORDINATION RESULT
{"=" * 50}

Task:
{task}

Tool Used:
Calculator

Result:
{result}
"""

    # Multi-Agent execution
    print("\n[Tool] Quantitative Business Tool")
    print("-" * 50)
    tool_result = execute_tool(task)

    print("\n[Agent] Research Agent")
    print("-" * 50)
    research_result = research_agent(task)

    print("\n[Agent] Planning Agent")
    print("-" * 50)
    planning_result = planning_agent(task, research_result)

    print("\n[Agent] Decision Agent")
    print("-" * 50)
    decision_result = decision_agent(task, research_result, planning_result, tool_result)

    final_output = f"""
{"=" * 50}
COORDINATION RESULT
{"=" * 50}

Task:
{task}

Tool Result:
{tool_result}

{"-" * 50}

Research Summary:
{research_result.get('executive_summary', '') if isinstance(research_result, dict) else research_result}

{"-" * 50}

Planning Roadmap:
{planning_result}

{"-" * 50}

Final Decision:
{decision_result.get('recommended_decision', '') if isinstance(decision_result, dict) else decision_result}

{"=" * 50}
"""

    return final_output
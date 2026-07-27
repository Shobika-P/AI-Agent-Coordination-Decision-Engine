from agents.research_agent import research_agent
from agents.planning_agent import planning_agent
from tools.calculator_tool import calculator_tool


def coordination_agent(task):
    """
    Coordinates AI agents and tools based on the task.
    """

    print("\n" + "=" * 50)
    print("COORDINATION ENGINE")
    print("=" * 50)

    print(f"\nTask: {task}")

    # Tool execution
    if any(operator in task for operator in ["+", "-", "*", "/"]):
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

    # Agent execution
    print("\n[Agent] Research Agent")
    print("-" * 50)
    research_result = research_agent(task)

    print("\n[Agent] Planning Agent")
    print("-" * 50)
    planning_result = planning_agent(task)

    final_output = f"""
{"=" * 50}
COORDINATION RESULT
{"=" * 50}

Task:
{task}

Research Agent:
{research_result}

{"-" * 50}

Planning Agent:
{planning_result}

{"=" * 50}
"""

    return final_output
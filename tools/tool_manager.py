from tools.profit_tool import calculate_profit
from tools.roi_tool import calculate_roi
from tools.break_even_tool import calculate_break_even
from tools.market_risk_tool import market_risk
from tools.tool_selector import select_tool

def execute_tool(task):

    task = task.lower()
    selected_tool = select_tool(task)

    print("Selected Tool :", selected_tool)
    if selected_tool == "profit":
        return calculate_profit(500,300)

    elif selected_tool == "roi":
        return calculate_roi(50000,70000)

    elif selected_tool == "break_even":
        return calculate_break_even(
        fixed_cost=50000,
        selling_price=500,
        variable_cost=300
    )

    elif selected_tool == "market_risk":
        result = market_risk(task)

        print("\nTool Output")
        print("-" * 60)
        print(f"Tool Name : {result['tool']}")
        print(f"Risk Level : {result['risk_level']}")

        print("\nObservations")
        print("-" * 20)

        for observation in result["observations"]:
            print(f"• {observation}")

        print("\nRecommendation")
        print("-" * 20)
        print(result["recommendation"])

        return result

    else:
        return None
    

    
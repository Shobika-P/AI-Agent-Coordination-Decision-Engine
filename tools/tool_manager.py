import re
from tools.profit_tool import calculate_profit
from tools.roi_tool import calculate_roi
from tools.break_even_tool import calculate_break_even
from tools.market_risk_tool import market_risk
from tools.tool_selector import select_tool


def _extract_numbers(text: str):
    """Extracts floating point numbers or integers from query text."""
    matches = re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', text)
    nums = []
    for m in matches:
        try:
            val = float(m.replace(',', ''))
            nums.append(val)
        except Exception:
            pass
    return nums


def execute_tool(task: str) -> dict:
    """
    Executes the selected business calculation or risk assessment tool.
    Extracts custom numeric parameters from task if present, otherwise applies sensible defaults.
    Returns structured output dictionary.
    """
    task = (task or "").strip()
    selected_tool = select_tool(task)
    nums = _extract_numbers(task)

    print(f"[ToolManager] Executing tool: '{selected_tool}' for query (Extracted {len(nums)} numbers)")

    if selected_tool == "profit":
        # Check for price/revenue and cost in query
        revenue = nums[0] if len(nums) >= 1 else 500.0
        cost = nums[1] if len(nums) >= 2 else (300.0 if len(nums) == 0 else revenue * 0.6)
        
        # Ensure revenue > cost for logical orientation if user gave cost first
        if len(nums) >= 2 and revenue < cost and cost > 0:
            revenue, cost = cost, revenue

        res = calculate_profit(revenue, cost)
        res["tool_name"] = "Profit & Unit Margin Tool"
        unit_profit = float(res.get("profit", 0))
        res["risk_level"] = "Low" if unit_profit > 150 else ("High" if unit_profit < 0 else "Medium")
        res["observations"] = [
            f"Baseline Unit Revenue: ₹{res.get('revenue', revenue):,.2f}".replace('.00', ''),
            f"Baseline Unit Cost: ₹{res.get('cost', cost):,.2f}".replace('.00', ''),
            f"Net Unit Profit: ₹{unit_profit:,.2f} ({res.get('profit_margin', '40%')})".replace('.00', '')
        ]
        return res

    elif selected_tool == "roi":
        investment = nums[0] if len(nums) >= 1 else 50000.0
        returns = nums[1] if len(nums) >= 2 else (investment * 1.4)
        
        if len(nums) >= 2 and investment > returns and returns > 0:
            investment, returns = returns, investment

        res = calculate_roi(investment, returns)
        res["tool_name"] = "Return on Investment (ROI) Tool"
        res["risk_level"] = "Low" if returns >= investment else "High"
        res["observations"] = [
            f"Estimated Capital Investment: ₹{investment:,.2f}".replace('.00', ''),
            f"Projected Gross Returns: ₹{returns:,.2f}".replace('.00', ''),
            f"Estimated ROI: {res.get('roi', '40%')}"
        ]
        return res

    elif selected_tool == "break_even":
        fixed_cost = 50000.0
        selling_price = 500.0
        variable_cost = 300.0

        if len(nums) >= 3:
            # e.g., price 500, cost 300, fixed cost 50000
            # Identify the largest number as likely fixed cost
            sorted_nums = sorted(nums)
            fixed_cost = sorted_nums[-1]
            selling_price = sorted_nums[1]
            variable_cost = sorted_nums[0]
        elif len(nums) == 2:
            selling_price = max(nums)
            variable_cost = min(nums)
        elif len(nums) == 1:
            if nums[0] > 5000:
                fixed_cost = nums[0]
            else:
                selling_price = nums[0]

        if selling_price <= variable_cost:
            selling_price = variable_cost + 200.0

        res = calculate_break_even(
            fixed_cost=fixed_cost,
            selling_price=selling_price,
            variable_cost=variable_cost
        )
        res["tool_name"] = "Break-Even Modeling Tool"
        margin = selling_price - variable_cost
        be_units = res.get('break_even_units', 250)
        res["risk_level"] = "Low" if be_units < 200 else ("High" if be_units > 1000 else "Medium")
        res["observations"] = [
            f"Monthly Fixed Overhead: ₹{fixed_cost:,.2f}".replace('.00', ''),
            f"Unit Contribution Margin: ₹{margin:,.2f} (Price ₹{selling_price:,.2f} - Cost ₹{variable_cost:,.2f})".replace('.00', ''),
            f"Break-Even Volume: {be_units:,.0f} units/month"
        ]
        return res

    elif selected_tool == "market_risk":
        res = market_risk(task)
        res["tool_name"] = "Market Risk & Opportunity Tool"
        return res

    else:
        return {
            "tool": "Market Risk Tool",
            "tool_name": "Market Risk Tool",
            "risk_level": "Medium",
            "observations": ["Market demand validation required prior to scaling."]
        }
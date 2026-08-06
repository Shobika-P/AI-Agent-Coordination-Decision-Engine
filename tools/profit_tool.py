def calculate_profit(revenue, cost):

    profit = revenue - cost

    margin = round((profit / revenue) * 100, 2)

    return {
        "tool": "Profit Tool",
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "profit_margin": f"{margin}%"
    }
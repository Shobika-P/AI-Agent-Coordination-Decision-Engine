def calculate_profit(price, cost):

    profit = price - cost

    return {
        "selling_price": price,
        "production_cost": cost,
        "profit_per_unit": profit
    }
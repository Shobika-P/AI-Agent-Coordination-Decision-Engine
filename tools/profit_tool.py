def calculate_profit(selling_price, production_cost):
    """
    Calculate profit or loss for a product.
    """

    # Input Validation
    if selling_price < 0 or production_cost < 0:
        return {
            "error": "Selling price and production cost cannot be negative."
        }

    # Calculate Profit
    profit = selling_price - production_cost

    # Decide Status
    if profit > 0:
        status = "PROFIT"
    elif profit < 0:
        status = "LOSS"
    else:
        status = "NO PROFIT NO LOSS"

    # Return Result
    return f"""
PROFIT ANALYSIS

Selling Price      : ₹{price}
Production Cost    : ₹{cost}
Profit Per Unit    : ₹{profit}
"""
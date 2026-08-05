def calculate_break_even(fixed_cost, selling_price, variable_cost):
    """
    Calculate Break-even Units.
    """

    # Validation
    if fixed_cost < 0 or selling_price < 0 or variable_cost < 0:
        return {
            "error": "Values cannot be negative."
        }

    if selling_price <= variable_cost:
        return {
            "error": "Selling price must be greater than variable cost."
        }

    # Formula
    break_even_units = fixed_cost / (selling_price - variable_cost)

    return f"""
BREAK-EVEN ANALYSIS

Fixed Cost            : ₹{fixed_cost}
Selling Price / Unit  : ₹{selling_price}
Variable Cost / Unit  : ₹{variable_cost}

Break-Even Units      : {break_even_units:.2f}
"""
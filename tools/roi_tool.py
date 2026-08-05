def calculate_roi(investment, expected_return):
    """
    Calculate Return on Investment (ROI).
    """

    # Validation
    if investment <= 0:
        return {
            "error": "Investment must be greater than zero."
        }

    # ROI Formula
    roi = ((expected_return - investment) / investment) * 100

    # Status
    if roi > 0:
        status = "GOOD INVESTMENT"
    elif roi < 0:
        status = "NOT PROFITABLE"
    else:
        status = "BREAK EVEN"

    return f"""
ROI ANALYSIS

Investment Amount : ₹{investment}
Revenue Generated : ₹{revenue}
ROI               : {roi:.2f}%
""" 
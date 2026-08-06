def calculate_roi(investment, returns):

    roi = ((returns - investment) / investment) * 100

    return {
        "tool": "ROI Tool",
        "investment": investment,
        "returns": returns,
        "roi": f"{round(roi,2)}%"
    }
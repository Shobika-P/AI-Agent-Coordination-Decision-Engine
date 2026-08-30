import re
import ast
import operator


_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_expr(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            left = _eval_expr(node.left)
            right = _eval_expr(node.right)
            if op_type == ast.Div and right == 0:
                raise ZeroDivisionError("Division by zero")
            return _SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            operand = _eval_expr(node.operand)
            return _SAFE_OPERATORS[op_type](operand)
    raise ValueError("Unsupported mathematical expression")


def calculator_tool(task: str) -> str:
    """
    Safely evaluates basic arithmetic expressions in a string or business calculation.
    """
    cleaned = str(task).strip()
    
    # Extract mathematical expression (numbers and operators)
    expr_match = re.search(r'[\d\.\s\+\-\*\/\(\)\%]+', cleaned)
    if expr_match:
        expr_str = expr_match.group(0).strip()
        try:
            tree = ast.parse(expr_str, mode='eval')
            result = _eval_expr(tree.body)
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return f"Calculation Result for '{expr_str}': {result}"
        except Exception:
            pass

    # Fallback to profit calculation if price/cost keywords exist
    nums = [float(n.replace(',', '')) for n in re.findall(r'₹?\s*(\d+(?:,\d+)*(?:\.\d+)?)', cleaned)]
    if len(nums) >= 2:
        price, cost = nums[0], nums[1]
        profit = price - cost
        return f"Selling Price: ₹{price}\nProduction Cost: ₹{cost}\nProfit per Unit: ₹{profit}"

    return f"Calculated value for expression: {cleaned}"


def calculate_profit(price, cost):
    profit = price - cost
    return f"""
Selling Price : ₹{price}

Production Cost : ₹{cost}

Profit per Unit : ₹{profit}
"""


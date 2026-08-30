import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.profit_tool import calculate_profit
from tools.roi_tool import calculate_roi
from tools.break_even_tool import calculate_break_even

print("=" * 50)
print("TESTING PROFIT TOOL")
print("=" * 50)
profit = calculate_profit(800, 500)
for key, value in profit.items():
    print(f"{key} : {value}")

print("\n" + "=" * 50)
print("TESTING ROI TOOL")
print("=" * 50)
roi = calculate_roi(100000, 130000)
for key, value in roi.items():
    print(f"{key} : {value}")

print("\n" + "=" * 50)
print("TESTING BREAK EVEN TOOL")
print("=" * 50)
break_even = calculate_break_even(50000, 500, 300)
for key, value in break_even.items():
    print(f"{key} : {value}")
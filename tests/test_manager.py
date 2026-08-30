import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.tool_manager import execute_tool

print("--- Testing Profit Execution ---")
print(execute_tool("calculate profit"))

print("\n--- Testing ROI Execution ---")
print(execute_tool("calculate roi"))

print("\n--- Testing Break-Even Execution ---")
print(execute_tool("calculate break even"))
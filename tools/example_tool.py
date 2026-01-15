"""
Example Tool Module

Demonstrates how to create a tool module using ToolModuleBase.
This is a template for creating new tool modules.

Usage:
    # As a library
    from shared.tools.example_tool import ExampleTool

    tool = ExampleTool()
    result = tool.greet(name="World")

    # CLI
    python example_tool.py --list-tools
    python example_tool.py --tool greet --args '{"name": "Alice"}'
    python example_tool.py --interactive
"""

from typing import Dict, Any
from .module_base import ToolModuleBase


class ExampleTool(ToolModuleBase):
    """Example tool module demonstrating the base class pattern."""

    # Module metadata
    name = "example"
    display_name = "Example Tool"
    description = "An example tool module demonstrating the pattern"
    version = "1.0.0"

    def initialize(self):
        """Initialize the tool schemas."""
        self.tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "greet",
                    "description": "Generate a greeting message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name to greet"
                            },
                            "formal": {
                                "type": "boolean",
                                "description": "Whether to use formal greeting",
                                "default": False
                            }
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform a simple calculation",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["add", "subtract", "multiply", "divide"],
                                "description": "Operation to perform"
                            },
                            "a": {
                                "type": "number",
                                "description": "First number"
                            },
                            "b": {
                                "type": "number",
                                "description": "Second number"
                            }
                        },
                        "required": ["operation", "a", "b"]
                    }
                }
            }
        ]

    def greet(self, name: str, formal: bool = False) -> str:
        """
        Generate a greeting message.

        Args:
            name: Name to greet
            formal: Whether to use formal greeting

        Returns:
            Greeting message
        """
        if formal:
            return f"Good day, {name}. How may I assist you?"
        else:
            return f"Hello, {name}!"

    def calculate(self, operation: str, a: float, b: float) -> Dict[str, Any]:
        """
        Perform a simple calculation.

        Args:
            operation: Operation to perform (add, subtract, multiply, divide)
            a: First number
            b: Second number

        Returns:
            Result dictionary with calculation result
        """
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return {"error": "Division by zero"}
            result = a / b
        else:
            return {"error": f"Unknown operation: {operation}"}

        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result
        }


# CLI entry point
if __name__ == '__main__':
    ExampleTool.main()

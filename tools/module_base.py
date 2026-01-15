"""
Base Class for Tool Modules

Provides a standardized base class for tool modules with common functionality:
- Tool schema definition
- Tool call handling
- Module registration
- CLI support
- Configuration management

Extracted and generalized from swarm/core/core_module_base.py.

Example:
    from shared.tools import ToolModuleBase

    class MyTool(ToolModuleBase):
        name = "mytool"
        display_name = "My Tool"
        description = "A custom tool module"

        def initialize(self):
            # Custom initialization
            self.tool_schemas = [{
                "type": "function",
                "function": {
                    "name": "my_function",
                    "description": "Does something useful",
                    "parameters": {...}
                }
            }]

        def my_function(self, arg1: str) -> str:
            return f"Result: {arg1}"

    # Use the tool
    tool = MyTool()
    result = tool.my_function(arg1="test")
"""

import sys
import argparse
import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class ToolModuleBase:
    """
    Base class for tool modules with standardized functionality.

    Subclasses should override:
    - name: Module identifier (lowercase, no spaces)
    - display_name: Human-readable name
    - description: Brief description of module purpose
    - initialize(): Custom initialization logic
    - Tool methods that match schema function names

    Provides:
    - Tool schema management
    - Tool call handling
    - Registry integration
    - CLI interface
    - Configuration access
    """

    # Module metadata - override in subclasses
    name = "unknown_module"
    display_name = "Unknown Module"
    description = "No description available"
    version = "1.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the module.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.tool_schemas = []
        self.tool_handlers = {}

        # Call custom initialization
        self.initialize()

        # Build handler map from methods
        self._build_handler_map()

    @staticmethod
    def _format_completion_response(response: Any) -> Dict[str, Any]:
        """
        Convert a CompletionResponse-like object into a serializable dict.

        Args:
            response: CompletionResponse or similar object

        Returns:
            Dictionary with content, model, usage, and metadata fields.
        """
        if response is None:
            return {}

        content = getattr(response, "content", "")
        model = getattr(response, "model", "")
        usage = getattr(response, "usage", {}) or {}
        metadata = getattr(response, "metadata", {}) or {}

        # Some provider responses expose finish_reason directly
        finish_reason = getattr(response, "finish_reason", None)
        if not finish_reason:
            finish_reason = metadata.get("finish_reason")

        result: Dict[str, Any] = {
            "content": content,
            "model": model,
            "usage": usage,
        }

        if metadata:
            result["metadata"] = metadata
        if finish_reason:
            result["finish_reason"] = finish_reason

        return result

    @staticmethod
    def _format_image_response(response: Any) -> Dict[str, Any]:
        """
        Convert an ImageResponse-like object into a serializable dict.

        Args:
            response: ImageResponse or similar object

        Returns:
            Dictionary with base64 image payload and metadata.
        """
        if response is None:
            return {}

        result: Dict[str, Any] = {
            "image_data": getattr(response, "image_data", ""),
            "model": getattr(response, "model", ""),
        }

        revised_prompt = getattr(response, "revised_prompt", None)
        metadata = getattr(response, "metadata", None)

        if revised_prompt:
            result["revised_prompt"] = revised_prompt
        if metadata:
            result["metadata"] = metadata

        return result

    def initialize(self):
        """
        Initialize the module - override in subclasses.

        This is where you should:
        - Set up tool_schemas
        - Initialize any resources
        - Configure tool-specific settings
        """

    def _build_handler_map(self):
        """
        Build a map of tool names to handler methods.

        Automatically maps schema function names to class methods.
        """
        for schema in self.tool_schemas:
            func_name = schema.get("function", {}).get("name")
            if func_name and hasattr(self, func_name):
                self.tool_handlers[func_name] = getattr(self, func_name)

    def get(self, attr: str, default: Any = None) -> Any:
        """
        Get an attribute from this module.

        Args:
            attr: Attribute name
            default: Default value if attribute doesn't exist

        Returns:
            Attribute value or default
        """
        return getattr(self, attr, default)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas for this module.

        Returns:
            List of OpenAI-compatible tool schemas
        """
        return self.tool_schemas.copy()

    def handle_tool_calls(
        self,
        tool_calls: List[Dict],
        config: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Handle tool calls for this module.

        Args:
            tool_calls: List of tool call objects from LLM
            config: Optional configuration dictionary

        Returns:
            List of standardized tool responses
        """
        config = config or self.config
        responses = []

        for tool_call in tool_calls:
            # Extract tool call info
            tool_id = tool_call.get("id", "unknown")
            function_name = tool_call.get("function", {}).get("name", "unknown")
            arguments = tool_call.get("function", {}).get("arguments", {})

            # Find handler
            handler = self.tool_handlers.get(function_name)

            if handler is None:
                # Unknown tool
                responses.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": function_name,
                    "content": f"Error: Unknown tool '{function_name}'"
                })
                continue

            try:
                # Call handler
                if isinstance(arguments, dict):
                    result = handler(**arguments)
                else:
                    result = handler(arguments)

                # Format response
                if isinstance(result, str):
                    content = result
                elif isinstance(result, dict):
                    import json
                    content = json.dumps(result)
                else:
                    content = str(result)

                responses.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": function_name,
                    "content": content
                })

            except Exception as e:
                logger.error(f"Error handling tool call '{function_name}': {e}")
                responses.append({
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": function_name,
                    "content": f"Error: {str(e)}"
                })

        return responses

    def register_with_registry(self, registry=None) -> Dict[str, Any]:
        """
        Register this module with a registry.

        Args:
            registry: ToolRegistry instance (uses global if None)

        Returns:
            Registration result dictionary
        """
        try:
            # Get global registry if not provided
            if registry is None:
                from .registry import get_registry
                registry = get_registry()

            # Register module
            registry.register_module(
                name=self.name,
                module=self,
                config={
                    "enabled": True,
                    "display_name": self.display_name,
                    "description": self.description,
                    "version": self.version
                }
            )

            # Register all tools
            for schema in self.get_tool_schemas():
                func_name = schema.get("function", {}).get("name")
                handler = self.tool_handlers.get(func_name)

                if handler:
                    registry.register_tool(
                        name=func_name,
                        schema=schema,
                        handler=handler,
                        module_name=self.name
                    )

            return {"success": True, "module": self.name}

        except Exception as e:
            logger.error(f"Error registering module '{self.name}': {e}")
            return {"success": False, "error": str(e)}

    def setup_cli_args(self, parser: argparse.ArgumentParser):
        """
        Setup additional CLI arguments - override in subclasses.

        Args:
            parser: ArgumentParser to add arguments to
        """

    def run_default_command(self, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Run the default command when no specific command is specified.

        Args:
            args: Parsed command-line arguments

        Returns:
            Command result dictionary
        """
        print(f"\n{self.display_name}: {self.description}\n")
        print("Use --help for usage information")
        return {"status": "success", "message": "Showed help"}

    def interactive_cli(self, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Run interactive CLI mode - override in subclasses.

        Args:
            args: Parsed command-line arguments

        Returns:
            Result of interactive session
        """
        return {
            "status": "error",
            "message": "Interactive mode not implemented for this module"
        }

    def run_cli(self, args=None) -> Dict[str, Any]:
        """
        Run the CLI interface for this module.

        Args:
            args: Command-line arguments (defaults to sys.argv[1:])

        Returns:
            Result of CLI execution
        """
        # Create argument parser
        parser = argparse.ArgumentParser(
            description=f"{self.display_name}: {self.description}"
        )

        # Add standard arguments
        parser.add_argument(
            '--list-tools',
            action='store_true',
            help='List available tools'
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Run in interactive mode'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        parser.add_argument(
            '--tool',
            type=str,
            help='Specific tool to run'
        )
        parser.add_argument(
            '--args',
            type=str,
            help='Arguments for the tool in JSON format'
        )

        # Custom argument setup
        self.setup_cli_args(parser)

        # Parse arguments
        parsed_args = parser.parse_args(args)

        # Configure logging
        if parsed_args.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # List tools mode
        if parsed_args.list_tools:
            print(f"\n{self.display_name} Tools:\n")
            for schema in self.get_tool_schemas():
                name = schema.get("function", {}).get("name", "Unknown")
                desc = schema.get("function", {}).get("description", "No description")
                print(f"  • {name}: {desc}")
            print()
            return {"status": "success", "message": "Listed tools"}

        # Interactive mode
        if parsed_args.interactive:
            return self.interactive_cli(parsed_args)

        # Run specific tool
        if parsed_args.tool:
            import json

            tool_args = {}
            if parsed_args.args:
                try:
                    tool_args = json.loads(parsed_args.args)
                except json.JSONDecodeError as e:
                    return {
                        "status": "error",
                        "message": f"Invalid JSON in --args: {e}"
                    }

            # Find the tool function
            if parsed_args.tool in self.tool_handlers:
                tool_func = self.tool_handlers[parsed_args.tool]
                try:
                    result = tool_func(**tool_args)
                    return {"status": "success", "result": result}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
            else:
                return {
                    "status": "error",
                    "message": f"Tool '{parsed_args.tool}' not found"
                }

        # Default behavior
        return self.run_default_command(parsed_args)

    @classmethod
    def main(cls):
        """
        Main entry point for module when run as script.

        Usage:
            if __name__ == '__main__':
                MyTool.main()
        """
        module = cls()
        result = module.run_cli()

        # Print result unless it's already been handled
        if isinstance(result, dict) and result.get("status") != "handled":
            import json
            print(json.dumps(result, indent=2))

        # Return appropriate exit code
        if isinstance(result, dict) and result.get("status") == "error":
            sys.exit(1)
        sys.exit(0)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', tools={len(self.tool_schemas)})"

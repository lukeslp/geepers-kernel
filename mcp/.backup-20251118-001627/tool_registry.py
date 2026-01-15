"""
Tool Registry for MCP Server

Dynamic tool registration, discovery, and execution system.
Enables extensible tool integration from hive modules and other sources.

Usage:
    from shared.mcp import ToolRegistry, ToolDefinition

    # Create registry
    registry = ToolRegistry()

    # Register tool
    @registry.register_tool(
        name="search_corpus",
        description="Search linguistic corpus",
        parameters={
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "default": 10}
        }
    )
    def search_corpus(query: str, limit: int = 10):
        # Implementation
        return results

    # List tools
    tools = registry.list_tools()

    # Execute tool
    result = registry.execute_tool("search_corpus", {"query": "linguistics"})

Author: Luke Steuber
"""

import logging
import inspect
import importlib
import pkgutil
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    """
    Tool parameter definition.

    Attributes:
        name: Parameter name
        type: Parameter type (string, integer, number, boolean, array, object)
        description: Parameter description
        required: Whether parameter is required
        default: Default value if not required
        enum: Allowed values (optional)
        items: Item schema for array types (optional)
        properties: Property schema for object types (optional)
    """
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    items: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema = {
            "type": self.type,
            "description": self.description
        }

        if self.enum:
            schema["enum"] = self.enum

        if self.items:
            schema["items"] = self.items

        if self.properties:
            schema["properties"] = self.properties

        if self.default is not None:
            schema["default"] = self.default

        return schema


@dataclass
class ToolDefinition:
    """
    Tool definition with metadata and execution function.

    Attributes:
        name: Tool name (unique identifier)
        description: Tool description
        function: Callable function to execute
        parameters: Dict of parameter definitions
        return_type: Expected return type description
        category: Tool category (optional)
        tags: List of tags for discovery (optional)
        examples: Usage examples (optional)
    """
    name: str
    description: str
    function: Callable
    parameters: Dict[str, ToolParameter] = field(default_factory=dict)
    return_type: str = "object"
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_mcp_manifest(self) -> Dict[str, Any]:
        """
        Convert to MCP tool manifest format.

        Returns:
            MCP tool definition dict
        """
        # Build input schema
        properties = {}
        required = []

        for param_name, param in self.parameters.items():
            properties[param_name] = param.to_json_schema()
            if param.required:
                required.append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required
            },
            "category": self.category,
            "tags": self.tags
        }

    def execute(self, arguments: Dict[str, Any]) -> Any:
        """
        Execute tool with provided arguments.

        Args:
            arguments: Tool arguments dict

        Returns:
            Tool execution result

        Raises:
            ValueError: If required parameters missing or validation fails
        """
        # Validate required parameters
        for param_name, param in self.parameters.items():
            if param.required and param_name not in arguments:
                raise ValueError(f"Missing required parameter: {param_name}")

        # Apply defaults
        kwargs = {}
        for param_name, param in self.parameters.items():
            if param_name in arguments:
                kwargs[param_name] = arguments[param_name]
            elif param.default is not None:
                kwargs[param_name] = param.default

        # Execute function
        try:
            return self.function(**kwargs)
        except Exception as e:
            logger.exception(f"Error executing tool {self.name}: {e}")
            raise


class ToolRegistry:
    """
    Central registry for MCP tools.

    Manages tool registration, discovery, and execution.
    Supports dynamic tool loading from modules.
    """

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, ToolDefinition] = {}
        self.categories: Dict[str, List[str]] = {}  # category -> tool_names

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        return_type: str = "object",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Callable:
        """
        Decorator to register a tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: Parameter definitions dict
            return_type: Return type description
            category: Tool category
            tags: Discovery tags

        Returns:
            Decorator function

        Example:
            @registry.register_tool(
                name="search_corpus",
                description="Search linguistic corpus",
                parameters={
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10, "required": False}
                }
            )
            def search_corpus(query: str, limit: int = 10):
                return results
        """
        def decorator(func: Callable) -> Callable:
            # Convert parameter dicts to ToolParameter objects
            tool_params = {}
            if parameters:
                for param_name, param_spec in parameters.items():
                    tool_params[param_name] = ToolParameter(
                        name=param_name,
                        type=param_spec.get('type', 'string'),
                        description=param_spec.get('description', ''),
                        required=param_spec.get('required', True),
                        default=param_spec.get('default'),
                        enum=param_spec.get('enum'),
                        items=param_spec.get('items'),
                        properties=param_spec.get('properties')
                    )

            # Create tool definition
            tool = ToolDefinition(
                name=name,
                description=description,
                function=func,
                parameters=tool_params,
                return_type=return_type,
                category=category,
                tags=tags or []
            )

            # Register tool
            self.tools[name] = tool

            # Track category
            if category:
                if category not in self.categories:
                    self.categories[category] = []
                self.categories[category].append(name)

            logger.info(f"Registered tool: {name} (category: {category})")

            return func

        return decorator

    def register_tool_object(self, tool: ToolDefinition):
        """
        Register a ToolDefinition object directly.

        Args:
            tool: ToolDefinition instance
        """
        self.tools[tool.name] = tool

        if tool.category:
            if tool.category not in self.categories:
                self.categories[tool.category] = []
            self.categories[tool.category].append(tool.name)

        logger.info(f"Registered tool: {tool.name}")

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if unregistered, False if not found
        """
        if name in self.tools:
            tool = self.tools[name]
            del self.tools[name]

            # Remove from category tracking
            if tool.category and tool.category in self.categories:
                self.categories[tool.category].remove(name)

            logger.info(f"Unregistered tool: {name}")
            return True

        return False

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Get tool definition by name.

        Args:
            name: Tool name

        Returns:
            ToolDefinition if found, None otherwise
        """
        return self.tools.get(name)

    def list_tools(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ToolDefinition]:
        """
        List registered tools with optional filtering.

        Args:
            category: Filter by category
            tags: Filter by tags (returns tools matching any tag)

        Returns:
            List of ToolDefinition objects
        """
        tools = list(self.tools.values())

        # Filter by category
        if category:
            tools = [t for t in tools if t.category == category]

        # Filter by tags
        if tags:
            tools = [t for t in tools if any(tag in t.tags for tag in tags)]

        return tools

    def list_categories(self) -> List[str]:
        """
        List all tool categories.

        Returns:
            List of category names
        """
        return list(self.categories.keys())

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a registered tool.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found or execution fails
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")

        return tool.execute(arguments)

    def get_mcp_manifest(self) -> List[Dict[str, Any]]:
        """
        Get MCP tools manifest for all registered tools.

        Returns:
            List of MCP tool definitions
        """
        return [tool.to_mcp_manifest() for tool in self.tools.values()]

    def auto_discover_module(
        self,
        module_path: str,
        category: Optional[str] = None,
        function_filter: Optional[Callable[[Callable], bool]] = None
    ):
        """
        Auto-discover and register tools from a Python module.

        Scans module for functions with tool metadata (docstrings, type hints).

        Args:
            module_path: Python module path (e.g., "shared.hive.tools")
            category: Category for discovered tools
            function_filter: Optional filter function to select which functions to register

        Example:
            registry.auto_discover_module(
                "shared.hive.tools",
                category="hive",
                function_filter=lambda f: f.__name__.startswith("tool_")
            )
        """
        try:
            module = importlib.import_module(module_path)

            # Find all functions in module
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                # Apply filter if provided
                if function_filter and not function_filter(obj):
                    continue

                # Get function metadata
                doc = inspect.getdoc(obj) or f"Tool: {name}"
                sig = inspect.signature(obj)

                # Build parameters from signature
                parameters = {}
                for param_name, param in sig.parameters.items():
                    param_type = "string"  # Default type

                    # Infer type from annotation
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == int:
                            param_type = "integer"
                        elif param.annotation == float:
                            param_type = "number"
                        elif param.annotation == bool:
                            param_type = "boolean"
                        elif param.annotation == list:
                            param_type = "array"
                        elif param.annotation == dict:
                            param_type = "object"

                    parameters[param_name] = {
                        "type": param_type,
                        "description": f"Parameter: {param_name}",
                        "required": param.default == inspect.Parameter.empty
                    }

                    if param.default != inspect.Parameter.empty:
                        parameters[param_name]["default"] = param.default

                # Register tool
                self.register_tool(
                    name=f"{module_path}.{name}",
                    description=doc,
                    parameters=parameters,
                    category=category
                )(obj)

            logger.info(f"Auto-discovered tools from module: {module_path}")

        except Exception as e:
            logger.exception(f"Error auto-discovering module {module_path}: {e}")

    def export_manifest(self, file_path: str):
        """
        Export tools manifest to JSON file.

        Args:
            file_path: Output file path
        """
        manifest = self.get_mcp_manifest()

        with open(file_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Exported tools manifest to: {file_path}")

    def import_manifest(self, file_path: str):
        """
        Import tools from JSON manifest file.

        Note: This only imports metadata, not actual function implementations.
        Use for documentation or discovery purposes.

        Args:
            file_path: Manifest file path
        """
        with open(file_path, 'r') as f:
            manifest = json.load(f)

        logger.info(f"Imported {len(manifest)} tool definitions from: {file_path}")
        return manifest


# -------------------------------------------------------------------------
# Global Registry Instance
# -------------------------------------------------------------------------

_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get global ToolRegistry instance.

    Returns:
        Global ToolRegistry singleton
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry

"""
Tool Registry System

Provides centralized registration and management of tools, modules, and their configurations.
Extracted and generalized from swarm/core/core_registry.py.

Key Features:
- Singleton pattern for global registry access
- Tool schema registration with deduplication
- Module configuration and enable/disable
- Handler registration and lookup
- Discovery status tracking
"""

from typing import Dict, List, Any, Optional, Callable, Iterable
import copy
import importlib
import inspect
import logging
import pkgutil


logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Tool registry for managing tools, schemas, and handlers.

    This registry provides a centralized location for:
    - Tool registration (name, schema, handler)
    - Module management (configuration, enable/disable)
    - Schema deduplication
    - Handler lookup

    Usage:
        # Get singleton instance
        registry = ToolRegistry.get_instance()

        # Register a tool
        registry.register_tool(
            name='search',
            schema={...},
            handler=search_function,
            module_name='search_module'
        )

        # Enable/disable modules
        registry.enable_module('search_module', enabled=True)

        # Get all enabled tools
        tools = registry.get_enabled_tools()
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton (useful for testing)."""
        cls._instance = None

    def __init__(self):
        """Initialize an empty registry."""
        # Tool storage
        self.tools = {}  # name → {schema, handler, module}
        self.tool_schemas = []  # List of all schemas
        self.tool_modules = {}  # module_name → [tool_names]

        # Module storage
        self._module_config = {}  # module_name → config dict
        self._modules = {}  # module_name → module object

        # Discovery state
        self._discovery_complete = False

        # Metrics
        self._reset_metrics()

        logger.info("ToolRegistry initialized")

    def register_tool(
        self,
        name: str,
        schema: Dict,
        handler: Callable,
        module_name: str = "unknown",
        **kwargs
    ) -> bool:
        """
        Register a tool with the registry.

        Args:
            name: Tool name (unique identifier)
            schema: OpenAI-compatible tool schema
            handler: Function to call when tool is invoked
            module_name: Name of module providing this tool
            **kwargs: Additional metadata

        Returns:
            True if registered, False if already existed
        """
        # Check if already registered
        if name in self.tools:
            logger.debug(f"Tool '{name}' already registered, skipping")
            self._metrics["duplicate_tools"] += 1
            return False

        try:
            self._validate_schema(schema)
        except ValueError as exc:
            failure = {"tool": name, "error": str(exc)}
            self._metrics["validation_failures"].append(failure)
            logger.error("Tool schema validation failed for %s: %s", name, exc)
            raise

        # Register tool
        self.tools[name] = {
            "schema": schema,
            "handler": handler,
            "module": module_name,
            **kwargs
        }

        # Add schema if not already present
        schema_name = schema.get("function", {}).get("name", name)
        if not any(
            s.get("function", {}).get("name") == schema_name
            for s in self.tool_schemas
        ):
            self.tool_schemas.append(schema)

        # Track module → tools mapping
        if module_name not in self.tool_modules:
            self.tool_modules[module_name] = []
        if name not in self.tool_modules[module_name]:
            self.tool_modules[module_name].append(name)

        self._metrics["registered_tools"] += 1
        logger.info(f"Registered tool '{name}' from module '{module_name}'")
        return True

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool from the registry.

        Args:
            name: Tool name to unregister

        Returns:
            True if unregistered, False if didn't exist
        """
        if name not in self.tools:
            return False

        tool_info = self.tools.pop(name)
        module_name = tool_info.get("module", "unknown")

        # Remove from module mapping
        if module_name in self.tool_modules:
            if name in self.tool_modules[module_name]:
                self.tool_modules[module_name].remove(name)

        # Remove schema
        schema_name = tool_info["schema"].get("function", {}).get("name", name)
        self.tool_schemas = [
            s for s in self.tool_schemas
            if s.get("function", {}).get("name") != schema_name
        ]

        logger.info(f"Unregistered tool '{name}'")
        return True

    def register_module(
        self,
        name: str,
        module: Any = None,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a module with the registry.

        Args:
            name: Module name
            module: Module object (optional)
            config: Module configuration (optional)

        Returns:
            True if registered, False if already existed
        """
        if name in self._modules:
            logger.debug(f"Module '{name}' already registered, skipping")
            return False

        self._modules[name] = module

        # Set default config if not provided
        if config is None:
            config = {
                "enabled": True,
                "priority": 100,
                "dependencies": []
            }

        self._module_config[name] = config
        logger.info(f"Registered module '{name}'")
        return True

    def enable_module(self, module_name: str, enabled: bool = True):
        """
        Enable or disable a module.

        Args:
            module_name: Name of module to enable/disable
            enabled: Whether module should be enabled
        """
        if module_name not in self._module_config:
            self._module_config[module_name] = {
                "enabled": enabled,
                "priority": 100,
                "dependencies": []
            }
        else:
            self._module_config[module_name]["enabled"] = enabled

        logger.info(f"{'Enabled' if enabled else 'Disabled'} module '{module_name}'")

    def is_module_enabled(self, module_name: str) -> bool:
        """
        Check if a module is enabled.

        Args:
            module_name: Name of module to check

        Returns:
            True if enabled, False otherwise
        """
        return self._module_config.get(module_name, {}).get("enabled", True)

    def get_module_config(self, module_name: Optional[str] = None) -> Dict:
        """
        Get module configuration.

        Args:
            module_name: Specific module name, or None for all configs

        Returns:
            Module config dict or all configs
        """
        if module_name is None:
            return self._module_config.copy()
        return self._module_config.get(module_name, {}).copy()

    def set_module_config(self, module_name: str, config: Dict[str, Any]):
        """
        Set configuration for a module.

        Args:
            module_name: Name of module
            config: Configuration dictionary
        """
        self._module_config[module_name] = config
        logger.debug(f"Updated config for module '{module_name}'")

    def get_tool(self, name: str) -> Optional[Dict]:
        """
        Get tool information by name.

        Args:
            name: Tool name

        Returns:
            Tool info dict or None if not found
        """
        return self.tools.get(name)

    def get_tool_handler(self, name: str) -> Optional[Callable]:
        """
        Get tool handler function by name.

        Args:
            name: Tool name

        Returns:
            Handler function or None if not found
        """
        tool = self.tools.get(name)
        return tool["handler"] if tool else None

    def get_all_tools(self) -> Dict[str, Dict]:
        """
        Get all registered tools.

        Returns:
            Dictionary of tool_name → tool_info
        """
        return self.tools.copy()

    def get_enabled_tools(self) -> Dict[str, Dict]:
        """
        Get all tools from enabled modules.

        Returns:
            Dictionary of tool_name → tool_info (only from enabled modules)
        """
        enabled_tools = {}
        for name, tool_info in self.tools.items():
            module_name = tool_info.get("module", "unknown")
            if self.is_module_enabled(module_name):
                enabled_tools[name] = tool_info
        return enabled_tools

    def get_tool_schemas(self, enabled_only: bool = True) -> List[Dict]:
        """
        Get all tool schemas.

        Args:
            enabled_only: If True, only return schemas from enabled modules

        Returns:
            List of tool schemas
        """
        if not enabled_only:
            return self.tool_schemas.copy()

        # Filter to enabled modules
        enabled_schemas = []
        for schema in self.tool_schemas:
            schema_name = schema.get("function", {}).get("name")
            if schema_name in self.tools:
                module_name = self.tools[schema_name].get("module", "unknown")
                if self.is_module_enabled(module_name):
                    enabled_schemas.append(schema)

        return enabled_schemas

    def get_tools_by_module(self, module_name: str) -> List[str]:
        """
        Get all tool names for a specific module.

        Args:
            module_name: Name of module

        Returns:
            List of tool names
        """
        return self.tool_modules.get(module_name, []).copy()

    def get_module_list(self, enabled_only: bool = False) -> List[str]:
        """
        Get list of registered module names.

        Args:
            enabled_only: If True, only return enabled modules

        Returns:
            List of module names
        """
        if not enabled_only:
            return list(self._modules.keys())

        return [
            name for name in self._modules.keys()
            if self.is_module_enabled(name)
        ]

    def discover_tool_modules(
        self,
        package: str = "shared.tools",
        *,
        auto_register: bool = False,
        module_names: Optional[Iterable[str]] = None,
        skip_errors: bool = True
    ) -> Dict[str, Any]:
        """
        Discover tool modules and optionally auto-register them.

        Args:
            package: Package path to scan (default 'shared.tools')
            auto_register: Instantiate ToolModuleBase subclasses and register tools
            module_names: Explicit list of modules to scan (skips package walking)
            skip_errors: Continue discovery after encountering errors

        Returns:
            Dict with 'modules' discovered and 'errors' encountered.
        """
        discovered: List[str] = []
        errors: Dict[str, str] = {}

        modules_to_scan: List[str] = list(module_names or [])
        if not modules_to_scan:
            try:
                pkg = importlib.import_module(package)
                if getattr(pkg, "__path__", None):
                    prefix = pkg.__name__ + "."
                    for _, name, _ in pkgutil.walk_packages(pkg.__path__, prefix):
                        modules_to_scan.append(name)
            except Exception as exc:
                error_msg = f"Unable to import package '{package}': {exc}"
                logger.error(error_msg)
                return {"modules": [], "errors": {package: error_msg}}

        ToolModuleBase = self._lazy_import_tool_base()

        for module_name in modules_to_scan:
            try:
                module = importlib.import_module(module_name)
                discovered.append(module_name)
            except Exception as exc:
                errors[module_name] = str(exc)
                logger.debug("Failed to import tool module %s: %s", module_name, exc)
                if not skip_errors:
                    raise
                continue

            if not auto_register:
                continue

            try:
                tool_classes = [
                    member
                    for _, member in inspect.getmembers(module, inspect.isclass)
                    if issubclass(member, ToolModuleBase)
                    and member is not ToolModuleBase
                    and getattr(member, "auto_register", True)
                ]
            except Exception as exc:
                errors[module_name] = f"Introspection error: {exc}"
                if not skip_errors:
                    raise
                continue

            for tool_cls in tool_classes:
                try:
                    instance = tool_cls()
                except Exception as exc:
                    errors[module_name] = f"{tool_cls.__name__}: {exc}"
                    logger.debug("Skipping %s due to init error: %s", tool_cls.__name__, exc)
                    if not skip_errors:
                        raise
                    continue

                self.register_module(tool_cls.name, instance)

                for schema in instance.get_tool_schemas():
                    function_def = schema.get("function", {})
                    handler_name = function_def.get("name")
                    handler = getattr(instance, handler_name, None)

                    if not callable(handler):
                        error_msg = f"Handler '{handler_name}' not found on {tool_cls.__name__}"
                        errors[module_name] = error_msg
                        if not skip_errors:
                            raise ValueError(error_msg)
                        continue

                    try:
                        self.register_tool(
                            name=function_def.get("name", tool_cls.name),
                            schema=schema,
                            handler=handler,
                            module_name=tool_cls.name,
                            module_class=tool_cls.__name__,
                        )
                    except Exception as exc:
                        errors[module_name] = str(exc)
                        if not skip_errors:
                            raise

        self._metrics["discovery"]["modules"] = discovered
        self._metrics["discovery"]["errors"] = errors
        return {"modules": discovered, "errors": errors}

    def get_metrics(self) -> Dict[str, Any]:
        """Return a snapshot of registry metrics."""
        return copy.deepcopy(self._metrics)

    def _reset_metrics(self):
        self._metrics = {
            "registered_tools": 0,
            "duplicate_tools": 0,
            "validation_failures": [],
            "discovery": {"modules": [], "errors": {}},
        }

    def _validate_schema(self, schema: Dict[str, Any]) -> None:
        if not isinstance(schema, dict):
            raise ValueError("Tool schema must be a dictionary")

        if schema.get("type") != "function":
            raise ValueError("Tool schema 'type' must be 'function'")

        function_block = schema.get("function")
        if not isinstance(function_block, dict):
            raise ValueError("Tool schema must include a 'function' definition")

        if not function_block.get("name"):
            raise ValueError("Tool schema function requires a 'name'")

        if not function_block.get("description"):
            raise ValueError("Tool schema function requires a 'description'")

        parameters = function_block.get("parameters")
        if not isinstance(parameters, dict):
            raise ValueError("Tool schema must define parameters as a dict")

        if parameters.get("type") != "object":
            raise ValueError("Tool schema parameters must be an object")

        if "properties" not in parameters or not isinstance(parameters["properties"], dict):
            raise ValueError("Tool schema parameters must include a 'properties' dictionary")

    @staticmethod
    def _lazy_import_tool_base():
        from .module_base import ToolModuleBase

        return ToolModuleBase

    def clear(self):
        """Clear all registered tools and modules."""
        self.tools.clear()
        self.tool_schemas.clear()
        self.tool_modules.clear()
        self._module_config.clear()
        self._modules.clear()
        self._discovery_complete = False
        self._reset_metrics()
        logger.info("Registry cleared")

    def mark_discovery_complete(self):
        """Mark module discovery as complete."""
        self._discovery_complete = True
        logger.info("Module discovery marked as complete")

    def is_discovery_complete(self) -> bool:
        """Check if module discovery is complete."""
        return self._discovery_complete

    def stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with counts and status
        """
        return {
            "total_tools": len(self.tools),
            "total_modules": len(self._modules),
            "enabled_modules": len([
                m for m in self._modules
                if self.is_module_enabled(m)
            ]),
            "enabled_tools": len(self.get_enabled_tools()),
            "discovery_complete": self._discovery_complete
        }

    def __repr__(self) -> str:
        stats = self.stats()
        return (
            f"ToolRegistry("
            f"tools={stats['total_tools']}, "
            f"modules={stats['total_modules']}, "
            f"enabled_tools={stats['enabled_tools']})"
        )


# Global registry access
_global_registry = None


def get_registry() -> ToolRegistry:
    """
    Get the global registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry.get_instance()
    return _global_registry


def reset_registry():
    """Reset the global registry (useful for testing)."""
    global _global_registry
    _global_registry = None
    ToolRegistry.reset_instance()

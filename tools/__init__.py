"""
Tool Registry System for Dynamic Module Loading

This module provides a registry pattern for discovering, loading, and managing
tool modules dynamically. Extracted from swarm's mature registry system.

Example:
    from shared.tools import ToolRegistry, ToolModuleBase

    # Create registry
    registry = ToolRegistry.get_instance()

    # Register a tool
    registry.register_tool(
        name='search',
        schema={...},
        handler=search_function,
        module_name='search_module'
    )

    # Get all tools
    tools = registry.get_all_tools()
"""

from .registry import ToolRegistry, get_registry
from .module_base import ToolModuleBase
from .data_tool_base import DataToolModuleBase
from .provider_registry import register_provider_tools
from .data_registry import register_data_tools, get_data_tool_status

# Gradient AI tools (optional - requires do-gradient-ai or gradient_provider_v2)
try:
    from .gradient_tools import GradientToolModule, register_gradient_tools
except ImportError:
    GradientToolModule = None
    register_gradient_tools = None

__all__ = [
    'ToolRegistry',
    'ToolModuleBase',
    'DataToolModuleBase',
    'get_registry',
    'register_provider_tools',
    'register_data_tools',
    'get_data_tool_status',
    # Gradient AI
    'GradientToolModule',
    'register_gradient_tools',
]

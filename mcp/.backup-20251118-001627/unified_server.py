"""
Unified MCP Server

Comprehensive MCP server exposing orchestrator agents for long-running workflows.
Integrates with streaming infrastructure (SSE, webhooks) and state management.

Tools provided:
- orchestrate_research: Execute Beltalowda hierarchical research workflow
- orchestrate_search: Execute Swarm multi-agent search workflow
- orchestrate_custom: Execute custom orchestrator pattern
- get_orchestration_status: Check workflow status
- list_orchestrator_patterns: List available orchestrator patterns
- cancel_orchestration: Cancel running workflow

Resources provided:
- orchestrator://{pattern}/info: Orchestrator metadata
- orchestrator://{task_id}/status: Workflow status
- orchestrator://{task_id}/results: Workflow results

Streaming:
- SSE endpoint: /stream/{task_id}
- Webhooks: Configurable per-workflow

Author: Luke Steuber
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import uuid

# Import from shared library
import sys
sys.path.insert(0, '/home/coolhand/shared')

from orchestration import (
    BeltalowdaOrchestrator,
    SwarmOrchestrator,
    BeltalowdaConfig,
    SwarmConfig,
    OrchestratorConfig,
    OrchestratorResult,
    TaskStatus,
    StreamEvent,
    EventType
)
from mcp.streaming import StreamingBridge, WebhookManager, get_streaming_bridge, get_webhook_manager
from mcp.tool_registry import ToolRegistry, get_tool_registry
from llm_providers.factory import ProviderFactory
from config import ConfigManager

logger = logging.getLogger(__name__)


class WorkflowState:
    """
    State management for running workflows.

    Tracks active orchestrations, results, and provides cleanup.
    """

    def __init__(self):
        """Initialize workflow state manager."""
        self.active_workflows: Dict[str, Dict[str, Any]] = {}  # task_id -> workflow_info
        self.completed_workflows: Dict[str, OrchestratorResult] = {}  # task_id -> result
        self.max_completed_retention = 100  # Keep last N completed workflows

    def create_workflow(
        self,
        task_id: str,
        orchestrator_type: str,
        task: str,
        config: OrchestratorConfig
    ) -> Dict[str, Any]:
        """
        Create new workflow state entry.

        Args:
            task_id: Unique task identifier
            orchestrator_type: Type of orchestrator (beltalowda, swarm, custom)
            task: Task description
            config: Orchestrator configuration

        Returns:
            Workflow info dict
        """
        workflow_info = {
            'task_id': task_id,
            'orchestrator_type': orchestrator_type,
            'task': task,
            'status': TaskStatus.PENDING,
            'created_at': datetime.utcnow().isoformat(),
            'started_at': None,
            'completed_at': None,
            'config': config.to_dict(),
            'error': None
        }

        self.active_workflows[task_id] = workflow_info
        return workflow_info

    def update_workflow_status(
        self,
        task_id: str,
        status: TaskStatus,
        error: Optional[str] = None
    ):
        """
        Update workflow status.

        Args:
            task_id: Task identifier
            status: New status
            error: Error message if failed
        """
        if task_id in self.active_workflows:
            self.active_workflows[task_id]['status'] = status

            if status == TaskStatus.RUNNING and not self.active_workflows[task_id]['started_at']:
                self.active_workflows[task_id]['started_at'] = datetime.utcnow().isoformat()

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                self.active_workflows[task_id]['completed_at'] = datetime.utcnow().isoformat()

            if error:
                self.active_workflows[task_id]['error'] = error

    def complete_workflow(self, task_id: str, result: OrchestratorResult):
        """
        Mark workflow as completed and store result.

        Args:
            task_id: Task identifier
            result: Orchestrator result
        """
        if task_id in self.active_workflows:
            self.update_workflow_status(task_id, result.status)
            self.completed_workflows[task_id] = result

            # Cleanup old completed workflows
            if len(self.completed_workflows) > self.max_completed_retention:
                # Remove oldest
                oldest = sorted(
                    self.completed_workflows.items(),
                    key=lambda x: x[1].execution_time
                )[0][0]
                del self.completed_workflows[oldest]

    def get_workflow_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow info by task_id."""
        return self.active_workflows.get(task_id)

    def get_workflow_result(self, task_id: str) -> Optional[OrchestratorResult]:
        """Get workflow result by task_id."""
        return self.completed_workflows.get(task_id)

    def list_active_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows."""
        return list(self.active_workflows.values())

    def cancel_workflow(self, task_id: str) -> bool:
        """
        Cancel a running workflow.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled, False if not found or already completed
        """
        if task_id in self.active_workflows:
            workflow = self.active_workflows[task_id]
            if workflow['status'] == TaskStatus.RUNNING:
                self.update_workflow_status(task_id, TaskStatus.CANCELLED)
                return True
        return False


class UnifiedMCPServer:
    """
    Unified MCP server for orchestrator agents.

    Exposes Beltalowda, Swarm Search, and custom orchestrator patterns
    through MCP protocol with streaming support.
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        streaming_bridge: Optional[StreamingBridge] = None,
        webhook_manager: Optional[WebhookManager] = None,
        tool_registry: Optional[ToolRegistry] = None
    ):
        """
        Initialize unified MCP server.

        Args:
            config_manager: ConfigManager instance (creates new one if None)
            streaming_bridge: StreamingBridge instance (uses global if None)
            webhook_manager: WebhookManager instance (uses global if None)
            tool_registry: ToolRegistry instance (uses global if None)
        """
        self.config = config_manager or ConfigManager(app_name='mcp_orchestrator')
        self.streaming_bridge = streaming_bridge or get_streaming_bridge()
        self.webhook_manager = webhook_manager or get_webhook_manager()
        self.tool_registry = tool_registry or get_tool_registry()
        self.workflow_state = WorkflowState()

        # Provider cache for orchestrators
        self.provider_cache = {}

    def _get_provider(self, provider_name: str = 'xai', model: Optional[str] = None):
        """
        Get or create provider instance for orchestrator.

        Args:
            provider_name: Provider name (default: xai for grok-3)
            model: Model name

        Returns:
            Provider instance
        """
        cache_key = f"{provider_name}:{model or 'default'}"

        if cache_key in self.provider_cache:
            return self.provider_cache[cache_key]

        api_key = self.config.get_api_key(provider_name)
        if not api_key:
            raise ValueError(f"No API key configured for provider: {provider_name}")

        provider = ProviderFactory.create_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model
        )

        self.provider_cache[cache_key] = provider
        return provider

    def _create_stream_callback(self, task_id: str) -> Callable:
        """
        Create streaming callback for orchestrator.

        Args:
            task_id: Task identifier

        Returns:
            Callback function for orchestrator streaming events
        """
        async def callback(event: StreamEvent):
            """Push event to streaming bridge and webhooks."""
            event_dict = {
                'event_type': event.event_type.value,
                'task_id': task_id,
                'timestamp': event.timestamp.isoformat(),
                'data': event.data
            }

            # Push to SSE stream
            await self.streaming_bridge.push_event(task_id, event_dict, create_if_missing=True)

            # Deliver to webhook if configured
            webhook_url = self.webhook_manager.get_webhook(task_id)
            if webhook_url:
                await self.webhook_manager.deliver_event(task_id, event_dict)

        return callback

    async def _execute_orchestrator(
        self,
        orchestrator,
        task: str,
        title: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> OrchestratorResult:
        """
        Execute orchestrator workflow with state tracking.

        Args:
            orchestrator: Orchestrator instance
            task: Task description
            title: Workflow title
            task_id: Task identifier
            context: Optional context dict

        Returns:
            OrchestratorResult
        """
        try:
            # Update status to running
            self.workflow_state.update_workflow_status(task_id, TaskStatus.RUNNING)

            # Create streaming callback
            stream_callback = self._create_stream_callback(task_id)

            # Execute workflow
            result = await orchestrator.execute_workflow(
                task=task,
                title=title,
                context=context,
                stream_callback=stream_callback
            )

            # Complete workflow
            self.workflow_state.complete_workflow(task_id, result)

            # Close stream
            await self.streaming_bridge.close_stream(task_id)

            return result

        except Exception as e:
            logger.exception(f"Error executing orchestrator: {e}")

            # Update status to failed
            self.workflow_state.update_workflow_status(task_id, TaskStatus.FAILED, str(e))

            # Close stream
            await self.streaming_bridge.close_stream(task_id)

            raise

    # -------------------------------------------------------------------------
    # MCP Tools
    # -------------------------------------------------------------------------

    async def tool_orchestrate_research(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: orchestrate_research

        Execute Beltalowda hierarchical research workflow.

        Arguments:
            task (str): Research task description
            title (str, optional): Workflow title
            num_agents (int, optional): Number of Belter agents (default: 8)
            enable_drummer (bool, optional): Enable Drummer synthesis (default: True)
            enable_camina (bool, optional): Enable Camina executive synthesis (default: True)
            generate_documents (bool, optional): Generate PDF/DOCX/MD reports (default: True)
            document_formats (List[str], optional): Document formats (default: ["markdown"])
            provider_name (str, optional): LLM provider (default: xai)
            model (str, optional): Model name
            webhook_url (str, optional): Webhook URL for notifications

        Returns:
            {success: bool, task_id: str, status: str, stream_url: str}
        """
        try:
            task = arguments.get('task')
            if not task:
                return {
                    "success": False,
                    "error": "Missing required argument: task"
                }

            title = arguments.get('title', f"Research: {task[:50]}...")

            # Build config
            config = BeltalowdaConfig(
                num_agents=arguments.get('num_agents', 8),
                enable_drummer=arguments.get('enable_drummer', True),
                enable_camina=arguments.get('enable_camina', True),
                generate_documents=arguments.get('generate_documents', True),
                document_formats=arguments.get('document_formats', ['markdown']),
                parallel_execution=True
            )

            # Get provider
            provider_name = arguments.get('provider_name', 'xai')
            model = arguments.get('model')
            provider = self._get_provider(provider_name, model)

            # Create orchestrator
            orchestrator = BeltalowdaOrchestrator(config=config, provider=provider, model=model)

            # Generate task ID
            task_id = f"research_{uuid.uuid4().hex[:12]}"

            # Register webhook if provided
            webhook_url = arguments.get('webhook_url')
            if webhook_url:
                self.webhook_manager.register_webhook(task_id, webhook_url)

            # Create workflow state
            self.workflow_state.create_workflow(task_id, 'beltalowda', task, config)

            # Execute asynchronously (don't block)
            asyncio.create_task(
                self._execute_orchestrator(orchestrator, task, title, task_id)
            )

            return {
                "success": True,
                "task_id": task_id,
                "status": "running",
                "stream_url": f"/stream/{task_id}",
                "orchestrator_type": "beltalowda",
                "config": config.to_dict()
            }

        except Exception as e:
            logger.exception(f"Error in orchestrate_research: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def tool_orchestrate_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: orchestrate_search

        Execute Swarm multi-agent search workflow.

        Arguments:
            query (str): Search query
            title (str, optional): Workflow title
            num_agents (int, optional): Number of specialized agents (default: 5)
            allowed_agent_types (List[str], optional): Restrict agent types
            generate_documents (bool, optional): Generate reports (default: True)
            document_formats (List[str], optional): Document formats (default: ["markdown"])
            provider_name (str, optional): LLM provider (default: xai)
            model (str, optional): Model name
            webhook_url (str, optional): Webhook URL for notifications

        Returns:
            {success: bool, task_id: str, status: str, stream_url: str}
        """
        try:
            query = arguments.get('query')
            if not query:
                return {
                    "success": False,
                    "error": "Missing required argument: query"
                }

            title = arguments.get('title', f"Search: {query[:50]}...")

            # Build config
            config = SwarmConfig(
                num_agents=arguments.get('num_agents', 5),
                allowed_agent_types=arguments.get('allowed_agent_types'),
                generate_documents=arguments.get('generate_documents', True),
                document_formats=arguments.get('document_formats', ['markdown']),
                parallel_execution=True
            )

            # Get provider
            provider_name = arguments.get('provider_name', 'xai')
            model = arguments.get('model')
            provider = self._get_provider(provider_name, model)

            # Create orchestrator
            orchestrator = SwarmOrchestrator(config=config, provider=provider, model=model)

            # Generate task ID
            task_id = f"search_{uuid.uuid4().hex[:12]}"

            # Register webhook if provided
            webhook_url = arguments.get('webhook_url')
            if webhook_url:
                self.webhook_manager.register_webhook(task_id, webhook_url)

            # Create workflow state
            self.workflow_state.create_workflow(task_id, 'swarm', query, config)

            # Execute asynchronously
            asyncio.create_task(
                self._execute_orchestrator(orchestrator, query, title, task_id)
            )

            return {
                "success": True,
                "task_id": task_id,
                "status": "running",
                "stream_url": f"/stream/{task_id}",
                "orchestrator_type": "swarm",
                "config": config.to_dict()
            }

        except Exception as e:
            logger.exception(f"Error in orchestrate_search: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def tool_get_orchestration_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: get_orchestration_status

        Get status of a running or completed orchestration.

        Arguments:
            task_id (str): Task identifier

        Returns:
            {success: bool, task_id: str, status: str, ...}
        """
        try:
            task_id = arguments.get('task_id')
            if not task_id:
                return {
                    "success": False,
                    "error": "Missing required argument: task_id"
                }

            # Check active workflows
            workflow_info = self.workflow_state.get_workflow_info(task_id)
            if not workflow_info:
                return {
                    "success": False,
                    "error": f"No workflow found with task_id: {task_id}"
                }

            # Get result if completed
            result = self.workflow_state.get_workflow_result(task_id)

            response = {
                "success": True,
                "task_id": task_id,
                "status": workflow_info['status'].value if isinstance(workflow_info['status'], TaskStatus) else workflow_info['status'],
                "orchestrator_type": workflow_info['orchestrator_type'],
                "task": workflow_info['task'],
                "created_at": workflow_info['created_at'],
                "started_at": workflow_info['started_at'],
                "completed_at": workflow_info['completed_at']
            }

            if result:
                response['result'] = {
                    'execution_time': result.execution_time,
                    'total_cost': result.total_cost,
                    'agent_count': len(result.agent_results),
                    'synthesis_count': len(result.synthesis_results),
                    'has_final_synthesis': result.final_synthesis is not None,
                    'documents_generated': len(result.generated_documents)
                }

            if workflow_info.get('error'):
                response['error'] = workflow_info['error']

            return response

        except Exception as e:
            logger.exception(f"Error in get_orchestration_status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def tool_cancel_orchestration(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: cancel_orchestration

        Cancel a running orchestration.

        Arguments:
            task_id (str): Task identifier

        Returns:
            {success: bool, task_id: str, cancelled: bool}
        """
        try:
            task_id = arguments.get('task_id')
            if not task_id:
                return {
                    "success": False,
                    "error": "Missing required argument: task_id"
                }

            cancelled = self.workflow_state.cancel_workflow(task_id)

            if cancelled:
                # Close stream
                await self.streaming_bridge.close_stream(task_id)

            return {
                "success": True,
                "task_id": task_id,
                "cancelled": cancelled
            }

        except Exception as e:
            logger.exception(f"Error in cancel_orchestration: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def tool_list_orchestrator_patterns(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: list_orchestrator_patterns

        List available orchestrator patterns.

        Arguments:
            None

        Returns:
            {success: bool, patterns: List[Dict]}
        """
        try:
            patterns = [
                {
                    'name': 'beltalowda',
                    'display_name': 'Beltalowda Hierarchical Research',
                    'description': 'Multi-tier research with Belters (workers), Drummers (mid-synthesis), and Camina (executive synthesis)',
                    'use_cases': [
                        'Comprehensive research tasks',
                        'Academic literature review',
                        'Market analysis',
                        'Strategic planning'
                    ],
                    'default_config': BeltalowdaConfig().to_dict()
                },
                {
                    'name': 'swarm',
                    'display_name': 'Swarm Multi-Agent Search',
                    'description': 'Specialized agents for different search domains (text, image, video, news, academic, etc.)',
                    'use_cases': [
                        'Multi-source information gathering',
                        'Comparative analysis',
                        'Trend analysis',
                        'Content discovery'
                    ],
                    'agent_types': [
                        'text', 'image', 'video', 'news', 'academic',
                        'social', 'product', 'technical', 'general'
                    ],
                    'default_config': SwarmConfig().to_dict()
                }
            ]

            return {
                "success": True,
                "patterns": patterns
            }

        except Exception as e:
            logger.exception(f"Error in list_orchestrator_patterns: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def tool_list_registered_tools(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: list_registered_tools

        List tools registered in the tool registry.

        Arguments:
            category (str, optional): Filter by category
            tags (List[str], optional): Filter by tags

        Returns:
            {success: bool, tools: List[Dict]}
        """
        try:
            category = arguments.get('category')
            tags = arguments.get('tags')

            tools = self.tool_registry.list_tools(category=category, tags=tags)

            return {
                "success": True,
                "tools": [tool.to_mcp_manifest() for tool in tools],
                "count": len(tools)
            }

        except Exception as e:
            logger.exception(f"Error in list_registered_tools: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def tool_execute_registered_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: execute_registered_tool

        Execute a tool registered in the tool registry.

        Arguments:
            tool_name (str): Name of the tool to execute
            tool_arguments (Dict): Arguments to pass to the tool

        Returns:
            {success: bool, result: Any}
        """
        try:
            tool_name = arguments.get('tool_name')
            tool_arguments = arguments.get('tool_arguments', {})

            if not tool_name:
                return {
                    "success": False,
                    "error": "Missing required argument: tool_name"
                }

            result = self.tool_registry.execute_tool(tool_name, tool_arguments)

            return {
                "success": True,
                "tool_name": tool_name,
                "result": result
            }

        except Exception as e:
            logger.exception(f"Error in execute_registered_tool: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Resources
    # -------------------------------------------------------------------------

    async def resource_orchestrator_info(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: orchestrator://{pattern}/info

        Returns metadata about an orchestrator pattern.

        Args:
            uri: Resource URI (e.g., "orchestrator://beltalowda/info")

        Returns:
            Orchestrator pattern metadata
        """
        try:
            # Parse URI: orchestrator://{pattern}/info
            parts = uri.replace('orchestrator://', '').split('/')
            pattern = parts[0]

            patterns_response = await self.tool_list_orchestrator_patterns({})
            patterns = {p['name']: p for p in patterns_response['patterns']}

            if pattern not in patterns:
                return {
                    "uri": uri,
                    "error": f"Unknown orchestrator pattern: {pattern}"
                }

            return {
                "uri": uri,
                **patterns[pattern]
            }

        except Exception as e:
            logger.exception(f"Error in resource_orchestrator_info: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    async def resource_workflow_status(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: orchestrator://{task_id}/status

        Returns status of a workflow.

        Args:
            uri: Resource URI (e.g., "orchestrator://research_abc123/status")

        Returns:
            Workflow status
        """
        try:
            # Parse URI: orchestrator://{task_id}/status
            parts = uri.replace('orchestrator://', '').split('/')
            task_id = parts[0]

            status_response = await self.tool_get_orchestration_status({'task_id': task_id})

            return {
                "uri": uri,
                **status_response
            }

        except Exception as e:
            logger.exception(f"Error in resource_workflow_status: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    async def resource_workflow_results(self, uri: str) -> Dict[str, Any]:
        """
        MCP Resource: orchestrator://{task_id}/results

        Returns full results of a completed workflow.

        Args:
            uri: Resource URI (e.g., "orchestrator://research_abc123/results")

        Returns:
            Workflow results
        """
        try:
            # Parse URI: orchestrator://{task_id}/results
            parts = uri.replace('orchestrator://', '').split('/')
            task_id = parts[0]

            result = self.workflow_state.get_workflow_result(task_id)
            if not result:
                return {
                    "uri": uri,
                    "error": f"No results found for task_id: {task_id}"
                }

            return {
                "uri": uri,
                "task_id": result.task_id,
                "title": result.title,
                "status": result.status.value,
                "execution_time": result.execution_time,
                "total_cost": result.total_cost,
                "final_synthesis": result.final_synthesis,
                "agent_results": [
                    {
                        'agent_id': r.agent_id,
                        'agent_type': r.agent_type.value,
                        'content': r.content,
                        'status': r.status.value,
                        'execution_time': r.execution_time,
                        'cost': r.cost
                    }
                    for r in result.agent_results
                ],
                "generated_documents": result.generated_documents
            }

        except Exception as e:
            logger.exception(f"Error in resource_workflow_results: {e}")
            return {
                "uri": uri,
                "error": str(e)
            }

    # -------------------------------------------------------------------------
    # MCP Server Interface
    # -------------------------------------------------------------------------

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP tools manifest.

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "orchestrate_research",
                "description": "Execute Beltalowda hierarchical research workflow with multi-tier synthesis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Research task description"
                        },
                        "title": {
                            "type": "string",
                            "description": "Workflow title (optional)"
                        },
                        "num_agents": {
                            "type": "integer",
                            "description": "Number of Belter agents (default: 8)"
                        },
                        "enable_drummer": {
                            "type": "boolean",
                            "description": "Enable Drummer mid-level synthesis (default: true)"
                        },
                        "enable_camina": {
                            "type": "boolean",
                            "description": "Enable Camina executive synthesis (default: true)"
                        },
                        "generate_documents": {
                            "type": "boolean",
                            "description": "Generate PDF/DOCX/MD reports (default: true)"
                        },
                        "document_formats": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Document formats: pdf, docx, markdown (default: [markdown])"
                        },
                        "provider_name": {
                            "type": "string",
                            "description": "LLM provider (default: xai)"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model name (optional)"
                        },
                        "webhook_url": {
                            "type": "string",
                            "description": "Webhook URL for async notifications (optional)"
                        }
                    },
                    "required": ["task"]
                }
            },
            {
                "name": "orchestrate_search",
                "description": "Execute Swarm multi-agent search workflow with specialized agent types",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "title": {
                            "type": "string",
                            "description": "Workflow title (optional)"
                        },
                        "num_agents": {
                            "type": "integer",
                            "description": "Number of specialized agents (default: 5)"
                        },
                        "allowed_agent_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Restrict to specific agent types (optional)"
                        },
                        "generate_documents": {
                            "type": "boolean",
                            "description": "Generate reports (default: true)"
                        },
                        "document_formats": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Document formats (default: [markdown])"
                        },
                        "provider_name": {
                            "type": "string",
                            "description": "LLM provider (default: xai)"
                        },
                        "model": {
                            "type": "string",
                            "description": "Model name (optional)"
                        },
                        "webhook_url": {
                            "type": "string",
                            "description": "Webhook URL for async notifications (optional)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_orchestration_status",
                "description": "Get status of a running or completed orchestration",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task identifier"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "cancel_orchestration",
                "description": "Cancel a running orchestration",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task identifier"
                        }
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "list_orchestrator_patterns",
                "description": "List available orchestrator patterns (Beltalowda, Swarm, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_registered_tools",
                "description": "List tools registered in the tool registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category (optional)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by tags (optional)"
                        }
                    }
                }
            },
            {
                "name": "execute_registered_tool",
                "description": "Execute a tool registered in the tool registry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool to execute"
                        },
                        "tool_arguments": {
                            "type": "object",
                            "description": "Arguments to pass to the tool"
                        }
                    },
                    "required": ["tool_name"]
                }
            }
        ]

    def get_resources_manifest(self) -> List[Dict[str, Any]]:
        """
        Return MCP resources manifest.

        Returns:
            List of resource templates
        """
        resources = [
            {
                "uri": "orchestrator://beltalowda/info",
                "name": "Beltalowda Orchestrator Info",
                "description": "Metadata about Beltalowda hierarchical research pattern",
                "mimeType": "application/json"
            },
            {
                "uri": "orchestrator://swarm/info",
                "name": "Swarm Orchestrator Info",
                "description": "Metadata about Swarm multi-agent search pattern",
                "mimeType": "application/json"
            }
        ]

        # Add resources for active workflows
        for workflow_info in self.workflow_state.list_active_workflows():
            task_id = workflow_info['task_id']
            resources.extend([
                {
                    "uri": f"orchestrator://{task_id}/status",
                    "name": f"{task_id} Status",
                    "description": f"Status of workflow {task_id}",
                    "mimeType": "application/json"
                },
                {
                    "uri": f"orchestrator://{task_id}/results",
                    "name": f"{task_id} Results",
                    "description": f"Results of workflow {task_id}",
                    "mimeType": "application/json"
                }
            ])

        return resources

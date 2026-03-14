"""
Unified MCP Server

Comprehensive MCP server exposing orchestrator agents for long-running workflows.
Integrates with streaming infrastructure (SSE, webhooks) and state management.

Tools provided:
- dream_research: Execute Dream Cascade hierarchical research workflow
- dream_search: Execute Dream Swarm multi-agent search workflow
- dreamwalker_status: Check workflow status
- dreamwalker_cancel: Cancel running workflow
- dreamwalker_patterns: List available orchestrator patterns
- dreamwalker_list_tools: List registered tools
- dreamwalker_execute_tool: Execute a registered tool

Resources provided:
- orchestrator://{pattern}/info: Orchestrator metadata
- orchestrator://{task_id}/status: Workflow status
- orchestrator://{task_id}/results: Workflow results

Streaming:
- SSE endpoint: /stream/{task_id}
- Webhooks: Configurable per-workflow

Author: Luke Steuber
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import uuid

# Import from shared library
import sys

# Import background loop for persistent async execution
try:
    from .background_loop import submit_background_task
except ImportError:
    from mcp.background_loop import submit_background_task

from shared.orchestration import (
    DreamCascadeOrchestrator,
    DreamSwarmOrchestrator,
    DreamCascadeConfig,
    DreamSwarmConfig,
    OrchestratorConfig,
    OrchestratorResult,
    TaskStatus,
    AgentResult,
    SynthesisResult,
    AgentType,
    StreamEvent
)

try:
    from .streaming import StreamingBridge, WebhookManager, get_streaming_bridge, get_webhook_manager
    from .tool_registry import ToolRegistry, get_tool_registry
except ImportError:
    from mcp.streaming import StreamingBridge, WebhookManager, get_streaming_bridge, get_webhook_manager
    from mcp.tool_registry import ToolRegistry, get_tool_registry
from shared.llm_providers.factory import ProviderFactory
from shared.llm_providers.tiered_selector import TieredProviderSelector, get_optimal_models_for_workflow
from shared.config import ConfigManager

logger = logging.getLogger(__name__)

# Constants
MAX_COMPLETED_WORKFLOW_RETENTION = 100  # Keep last N completed workflows
DEFAULT_PROVIDER = 'xai'  # Default LLM provider (for grok-3)


class WorkflowState:
    """
    State management for running workflows.

    Tracks active orchestrations, results, and provides cleanup.
    """

    MAX_ACTIVE_WORKFLOWS = 50  # Prevent unbounded growth

    def __init__(self):
        """Initialize workflow state manager."""
        self.active_workflows: Dict[str, Dict[str, Any]] = {}  # task_id -> workflow_info
        self.completed_workflows: Dict[str, OrchestratorResult] = {}  # task_id -> result
        self.active_tasks: Dict[str, Any] = {}  # task_id -> asyncio.Task object
        self.max_completed_retention = MAX_COMPLETED_WORKFLOW_RETENTION

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
            orchestrator_type: Type of orchestrator (dream-cascade, dream-swarm, custom)
            task: Task description
            config: Orchestrator configuration

        Returns:
            Workflow info dict

        Raises:
            ValueError: If maximum active workflows exceeded
        """
        # Check active workflow limit
        if len(self.active_workflows) >= self.MAX_ACTIVE_WORKFLOWS:
            raise ValueError(
                f"Maximum active workflows ({self.MAX_ACTIVE_WORKFLOWS}) exceeded. "
                f"Please wait for existing workflows to complete or cancel them."
            )

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
        logger.info(f"Completing workflow {task_id} with status {result.status}")

        # Set completion timestamp before storing
        if task_id in self.active_workflows:
            completion_time = datetime.utcnow().isoformat()
            self.active_workflows[task_id]['completed_at'] = completion_time
            self.update_workflow_status(task_id, result.status)
        else:
            completion_time = datetime.utcnow().isoformat()

        # Ensure result stores completion timestamp
        result.completed_at = completion_time

        # Store result
        self.completed_workflows[task_id] = result
        logger.info(f"Workflow {task_id} marked as completed. Active workflows: {len(self.active_workflows)}, Completed: {len(self.completed_workflows)}")

        # Clean up task reference
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

        # Cleanup old completed workflows (FIFO by completion time)
        while len(self.completed_workflows) > self.max_completed_retention:
            # Remove oldest by completion timestamp
            oldest_task_id = min(
                self.completed_workflows.keys(),
                key=lambda tid: (
                    self.completed_workflows[tid].completed_at
                    or self.active_workflows.get(tid, {}).get('completed_at')
                    or '9999-12-31T23:59:59Z'
                )
            )
            self.completed_workflows.pop(oldest_task_id, None)
            self.active_workflows.pop(oldest_task_id, None)
            self.active_tasks.pop(oldest_task_id, None)
            logger.info(
                "Evicted oldest workflow %s to maintain retention limit (%d/%d)",
                oldest_task_id,
                len(self.completed_workflows),
                self.max_completed_retention
            )

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

    def serialize_state(self) -> Dict[str, Any]:
        """
        Serialize workflow state to JSON-serializable dict.

        Returns:
            Dictionary containing active and completed workflows.
        """
        def _serialize(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, dict):
                return {key: _serialize(val) for key, val in value.items()}
            if isinstance(value, list):
                return [_serialize(item) for item in value]
            return value

        serialized_active = {}
        for task_id, info in self.active_workflows.items():
            serialized_active[task_id] = _serialize(dict(info))

        serialized_completed = {
            task_id: _serialize(result.to_dict())
            for task_id, result in self.completed_workflows.items()
        }

        return {
            "active_workflows": serialized_active,
            "completed_workflows": serialized_completed,
            "max_completed_retention": self.max_completed_retention,
            "timestamp": datetime.utcnow().isoformat()
        }

    def load_state(self, state_data: Dict[str, Any]):
        """
        Load workflow state from serialized data.

        Args:
            state_data: Serialized workflow state dictionary
        """
        if not state_data:
            return

        self.active_workflows = {}
        for task_id, info in state_data.get("active_workflows", {}).items():
            if not isinstance(info, dict):
                continue
            status = info.get("status", TaskStatus.PENDING.value)
            info_copy = dict(info)
            if not isinstance(status, TaskStatus):
                try:
                    info_copy["status"] = TaskStatus(status)
                except ValueError:
                    info_copy["status"] = TaskStatus.PENDING
            self.active_workflows[task_id] = info_copy

        self.completed_workflows = {}
        for task_id, result_data in state_data.get("completed_workflows", {}).items():
            try:
                result_obj = OrchestratorResult.from_dict(result_data)
            except AttributeError:
                # Fallback for environments without from_dict helpers
                status_value = result_data.get("status", TaskStatus.COMPLETED.value)
                if isinstance(status_value, TaskStatus):
                    status_enum = status_value
                else:
                    try:
                        status_enum = TaskStatus(status_value)
                    except ValueError:
                        status_enum = TaskStatus.COMPLETED

                agent_results = []
                for item in result_data.get("agent_results", []) or []:
                    agent_type_value = item.get("agent_type", AgentType.WORKER.value)
                    if isinstance(agent_type_value, AgentType):
                        agent_type_enum = agent_type_value
                    else:
                        try:
                            agent_type_enum = AgentType(agent_type_value)
                        except ValueError:
                            agent_type_enum = AgentType.WORKER

                    agent_status_value = item.get("status", TaskStatus.COMPLETED.value)
                    if isinstance(agent_status_value, TaskStatus):
                        agent_status_enum = agent_status_value
                    else:
                        try:
                            agent_status_enum = TaskStatus(agent_status_value)
                        except ValueError:
                            agent_status_enum = TaskStatus.COMPLETED

                    agent_results.append(
                        AgentResult(
                            agent_id=item.get("agent_id", ""),
                            agent_type=agent_type_enum,
                            subtask_id=item.get("subtask_id", ""),
                            content=item.get("content", ""),
                            status=agent_status_enum,
                            execution_time=float(item.get("execution_time", 0.0)),
                            cost=float(item.get("cost", 0.0)),
                            metadata=item.get("metadata", {}) or {},
                            error=item.get("error"),
                            citations=item.get("citations", []) or []
                        )
                    )

                synthesis_results = []
                for item in result_data.get("synthesis_results", []) or []:
                    synthesis_results.append(
                        SynthesisResult(
                            synthesis_id=item.get("synthesis_id", ""),
                            synthesis_level=item.get("synthesis_level", ""),
                            content=item.get("content", ""),
                            source_agent_ids=item.get("source_agent_ids", []) or [],
                            execution_time=float(item.get("execution_time", 0.0)),
                            cost=float(item.get("cost", 0.0)),
                            metadata=item.get("metadata", {}) or {}
                        )
                    )

                result_kwargs = {
                    "task_id": result_data.get("task_id", task_id),
                    "title": result_data.get("title", ""),
                    "status": status_enum,
                    "agent_results": agent_results,
                    "synthesis_results": synthesis_results,
                    "final_synthesis": result_data.get("final_synthesis"),
                    "execution_time": float(result_data.get("execution_time", 0.0)),
                    "total_cost": float(result_data.get("total_cost", 0.0)),
                    "metadata": result_data.get("metadata", {}) or {},
                    "generated_documents": result_data.get("generated_documents", []) or [],
                    "artifacts": result_data.get("artifacts", []) or [],
                    "error": result_data.get("error")
                }
                if hasattr(OrchestratorResult, "completed_at"):
                    result_kwargs["completed_at"] = result_data.get("completed_at")

                result_obj = OrchestratorResult(**result_kwargs)
                if not hasattr(result_obj, "completed_at") and result_data.get("completed_at"):
                    setattr(result_obj, "completed_at", result_data.get("completed_at"))
            except Exception as exc:
                logger.error("Failed to load completed workflow %s: %s", task_id, exc)
                continue

            self.completed_workflows[task_id] = result_obj

        self.max_completed_retention = state_data.get("max_completed_retention", self.max_completed_retention)
        self.active_tasks = {}


class UnifiedMCPServer:
    """
    Unified MCP server for orchestrator agents.

    Exposes Dream Cascade, Dream Swarm, and custom orchestrator patterns
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

    def _get_provider(
        self,
        provider_name: str = DEFAULT_PROVIDER,
        model: Optional[str] = None
    ):
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

        provider = ProviderFactory.get_provider(provider_name)

        self.provider_cache[cache_key] = provider
        return provider

    def _get_tiered_models(
        self,
        provider_name: str,
        budget_tier: str = 'balanced'
    ) -> Dict[str, str]:
        """
        Get tiered model assignments for orchestrator workflow.

        Uses TieredProviderSelector to map orchestrator tiers to optimal
        models based on budget preference.

        Args:
            provider_name: Provider name
            budget_tier: Budget tier ('cheap', 'balanced', 'premium')

        Returns:
            Dict with model assignments:
            {
                'worker_model': 'model_for_belters',
                'primary_model': 'model_for_drummers',
                'synthesis_model': 'model_for_camina'
            }
        """
        try:
            selector = TieredProviderSelector(provider_name)
            models = selector.get_orchestrator_models(budget_tier)

            return {
                'worker_model': models['belter'],
                'primary_model': models['drummer'],
                'synthesis_model': models['camina']
            }
        except ValueError as e:
            logger.warning(f"Tiered selection not available for {provider_name}: {e}")
            # Fall back to no tiered selection
            return {}

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
                'event_type': event.event_type,  # event_type is already a string
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
        logger.info(f"_execute_orchestrator starting for task_id={task_id}")
        try:
            # Update status to running
            self.workflow_state.update_workflow_status(task_id, TaskStatus.RUNNING)
            logger.info(f"Updated workflow status to RUNNING for {task_id}")

            # Create streaming callback
            stream_callback = self._create_stream_callback(task_id)

            # Execute workflow
            logger.info(f"Calling orchestrator.execute_workflow for {task_id}")
            result = await orchestrator.execute_workflow(
                task=task,
                title=title,
                context=context,
                stream_callback=stream_callback
            )
            logger.info(f"Orchestrator.execute_workflow completed for {task_id}, result.status={result.status}")

            # Complete workflow
            logger.info(f"Calling complete_workflow for {task_id}")
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

    async def tool_dream_orchestrate_research(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_research

        Execute Dream Cascade hierarchical research workflow.

        Arguments:
            task (str): Research task description
            title (str, optional): Workflow title
            num_agents (int, optional): Number of worker agents (default: 8)
            enable_drummer (bool, optional): Enable mid-level synthesis (default: True)
            enable_camina (bool, optional): Enable Camina executive synthesis (default: True)
            generate_documents (bool, optional): Generate PDF/DOCX/MD reports (default: True)
            document_formats (List[str], optional): Document formats (default: ["markdown"])
            provider_name (str, optional): LLM provider (default: xai)
            model (str, optional): Model name (overrides tiered selection)
            budget_tier (str, optional): Budget tier for tiered model selection
                ('cheap', 'balanced', 'premium'). Default: 'balanced'
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

            # Get provider and model configuration
            provider_name = arguments.get('provider_name', 'xai')
            model = arguments.get('model')
            budget_tier = arguments.get('budget_tier', 'balanced')

            # Get tiered model assignments if no explicit model specified
            tiered_models = {}
            if not model:
                tiered_models = self._get_tiered_models(provider_name, budget_tier)

            # Build config with tiered models
            config = DreamCascadeConfig(
                num_agents=arguments.get('num_agents', 8),
                enable_drummer=arguments.get('enable_drummer', True),
                enable_camina=arguments.get('enable_camina', True),
                generate_documents=arguments.get('generate_documents', True),
                document_formats=arguments.get('document_formats', ['markdown']),
                parallel_execution=True,
                # Tiered model assignments
                worker_model=tiered_models.get('worker_model'),
                primary_model=tiered_models.get('primary_model') or model,
                synthesis_model=tiered_models.get('synthesis_model')
            )

            # Get provider
            provider = self._get_provider(provider_name, model)

            # Create orchestrator
            orchestrator = DreamCascadeOrchestrator(config=config, provider=provider, model=model)

            # Generate task ID
            task_id = f"research_{uuid.uuid4().hex[:12]}"

            # Register webhook if provided
            webhook_url = arguments.get('webhook_url')
            if webhook_url:
                self.webhook_manager.register_webhook(task_id, webhook_url)

            # Create workflow state
            self.workflow_state.create_workflow(task_id, 'dream-cascade', task, config)

            # Execute asynchronously in persistent background loop
            task_obj = submit_background_task(
                self._execute_orchestrator(orchestrator, task, title, task_id)
            )
            self.workflow_state.active_tasks[task_id] = task_obj

            return {
                "success": True,
                "task_id": task_id,
                "status": "running",
                "stream_url": f"/stream/{task_id}",
                "orchestrator_type": "dream-cascade",
                "config": config.to_dict()
            }

        except Exception as e:
            logger.exception(f"Error in orchestrate_research: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def tool_dream_orchestrate_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Tool: dream_search

        Execute Dream Swarm multi-agent search workflow.

        Arguments:
            query (str): Search query
            title (str, optional): Workflow title
            num_agents (int, optional): Number of specialized agents (default: 5)
            allowed_agent_types (List[str], optional): Restrict agent types
            generate_documents (bool, optional): Generate reports (default: True)
            document_formats (List[str], optional): Document formats (default: ["markdown"])
            provider_name (str, optional): LLM provider (default: xai)
            model (str, optional): Model name (overrides tiered selection)
            budget_tier (str, optional): Budget tier for tiered model selection
                ('cheap', 'balanced', 'premium'). Default: 'balanced'
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

            # Get provider and model configuration
            provider_name = arguments.get('provider_name', 'xai')
            model = arguments.get('model')
            budget_tier = arguments.get('budget_tier', 'balanced')

            # Get tiered model assignments if no explicit model specified
            tiered_models = {}
            if not model:
                tiered_models = self._get_tiered_models(provider_name, budget_tier)

            # Build config with tiered models
            config = DreamSwarmConfig(
                num_agents=arguments.get('num_agents', 5),
                allowed_agent_types=arguments.get('allowed_agent_types'),
                generate_documents=arguments.get('generate_documents', True),
                document_formats=arguments.get('document_formats', ['markdown']),
                parallel_execution=True,
                # Tiered model assignments
                worker_model=tiered_models.get('worker_model'),
                primary_model=tiered_models.get('primary_model') or model,
                synthesis_model=tiered_models.get('synthesis_model')
            )

            # Get provider
            provider = self._get_provider(provider_name, model)

            # Create orchestrator
            orchestrator = DreamSwarmOrchestrator(config=config, provider=provider, model=model)

            # Generate task ID
            task_id = f"search_{uuid.uuid4().hex[:12]}"

            # Register webhook if provided
            webhook_url = arguments.get('webhook_url')
            if webhook_url:
                self.webhook_manager.register_webhook(task_id, webhook_url)

            # Create workflow state
            self.workflow_state.create_workflow(task_id, 'dream-swarm', query, config)

            # Execute asynchronously in persistent background loop
            task_obj = submit_background_task(
                self._execute_orchestrator(orchestrator, query, title, task_id)
            )
            self.workflow_state.active_tasks[task_id] = task_obj

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

    async def tool_dreamwalker_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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

    async def tool_dreamwalker_cancel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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

    async def tool_dreamwalker_patterns(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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
                    'name': 'dream-cascade',
                    'display_name': 'Dream Cascade Hierarchical Research',
                    'description': 'Three-tier cascading synthesis with workers (parallel execution), mid-level synthesis, and executive synthesis',
                    'use_cases': [
                        'Comprehensive research tasks',
                        'Academic literature review',
                        'Market analysis',
                        'Strategic planning'
                    ],
                    'default_config': DreamCascadeConfig().to_dict()
                },
                {
                    'name': 'dream-swarm',
                    'display_name': 'Dream Swarm Multi-Agent Search',
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
                    'default_config': DreamSwarmConfig().to_dict()
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

    async def tool_dreamwalker_list_tools(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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

    async def tool_dreamwalker_execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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
            uri: Resource URI (e.g., "orchestrator://dream-cascade/info")

        Returns:
            Orchestrator pattern metadata
        """
        try:
            # Parse URI: orchestrator://{pattern}/info
            parts = uri.replace('orchestrator://', '').split('/')
            pattern = parts[0]

            patterns_response = await self.tool_dreamwalker_patterns({})
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
                "name": "dream_orchestrate_research",
                "description": "Execute Dream Cascade hierarchical research workflow with three-tier synthesis",
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
                            "description": "Model name (overrides tiered selection)"
                        },
                        "budget_tier": {
                            "type": "string",
                            "enum": ["cheap", "balanced", "premium"],
                            "description": "Budget tier for tiered model selection. 'cheap' uses simpler models, 'premium' uses best models. Default: balanced"
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
                "name": "dream_orchestrate_search",
                "description": "Execute Dream Swarm multi-agent search workflow with specialized agent types",
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
                            "description": "Model name (overrides tiered selection)"
                        },
                        "budget_tier": {
                            "type": "string",
                            "enum": ["cheap", "balanced", "premium"],
                            "description": "Budget tier for tiered model selection. 'cheap' uses simpler models, 'premium' uses best models. Default: balanced"
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
                "name": "dreamwalker_status",
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
                "name": "dreamwalker_cancel",
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
                "name": "dreamwalker_patterns",
                "description": "List available orchestrator patterns (Dream Cascade, Dream Swarm, etc.)",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "dreamwalker_list_tools",
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
                "name": "dreamwalker_execute_tool",
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
                "uri": "orchestrator://dream-cascade/info",
                "name": "Dream Cascade Orchestrator Info",
                "description": "Metadata about Dream Cascade hierarchical research pattern",
                "mimeType": "application/json"
            },
            {
                "uri": "orchestrator://dream-swarm/info",
                "name": "Dream Swarm Orchestrator Info",
                "description": "Metadata about Dream Swarm multi-agent search pattern",
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

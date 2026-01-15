from datetime import datetime
from unittest.mock import MagicMock, patch

from shared.mcp.unified_server import WorkflowState
from shared.orchestration.models import OrchestratorResult, TaskStatus


def _make_result(task_id: str) -> OrchestratorResult:
    return OrchestratorResult(
        task_id=task_id,
        title=f"Title for {task_id}",
        status=TaskStatus.COMPLETED,
        agent_results=[],
        synthesis_results=[],
        metadata={},
    )


def _make_config() -> MagicMock:
    config = MagicMock()
    config.to_dict.return_value = {}
    return config


def test_workflow_state_eviction_respects_completion_timestamp():
    state = WorkflowState()
    state.max_completed_retention = 2
    config = _make_config()

    timestamps = [
        datetime(2024, 1, 1, 12, 0, 0),
        datetime(2024, 1, 1, 12, 0, 1),
        datetime(2024, 1, 1, 12, 0, 2),
    ]

    for idx, ts in enumerate(timestamps):
        task_id = f"task_{idx}"
        state.create_workflow(task_id, "swarm", f"Task {idx}", config)
        result = _make_result(task_id)
        with patch("shared.mcp.unified_server.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = ts
            state.complete_workflow(task_id, result)

    assert "task_0" not in state.completed_workflows
    assert "task_0" not in state.active_workflows
    assert set(state.completed_workflows.keys()) == {"task_1", "task_2"}

    latest_result = state.completed_workflows["task_2"]
    assert latest_result.completed_at == timestamps[2].isoformat()


def test_workflow_state_serialization_and_restore():
    state = WorkflowState()
    config = _make_config()

    with patch("shared.mcp.unified_server.datetime") as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2024, 5, 1, 8, 30, 0)
        state.create_workflow("task_a", "swarm", "Test task", config)
        result = _make_result("task_a")
        state.complete_workflow("task_a", result)

    serialized = state.serialize_state()
    assert serialized["active_workflows"]["task_a"]["status"] == TaskStatus.COMPLETED.value
    assert serialized["completed_workflows"]["task_a"]["completed_at"] is not None

    restored = WorkflowState()
    restored.load_state(serialized)

    assert "task_a" in restored.completed_workflows
    restored_result = restored.completed_workflows["task_a"]
    assert restored_result.completed_at == serialized["completed_workflows"]["task_a"]["completed_at"]
    restored_status = restored.active_workflows["task_a"]["status"]
    if hasattr(restored_status, "value"):
        assert restored_status.value == TaskStatus.COMPLETED.value
    else:
        assert restored_status == TaskStatus.COMPLETED.value


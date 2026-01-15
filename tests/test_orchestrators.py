from __future__ import annotations

import pytest

from shared.orchestration import (
    AgentType,
    IterativeOrchestrator,
    OrchestratorConfig,
    SequentialOrchestrator,
    ConditionalOrchestrator,
)
from shared.orchestration.models import TaskStatus


def _simple_handler_factory(content: str):
    def handler(_subtask, _context):
        return content

    return handler


@pytest.mark.asyncio
async def test_sequential_orchestrator_runs_in_order():
    config = OrchestratorConfig(
        parallel_execution=False,
        generate_documents=False,
        streaming=False,
    )
    orchestrator = SequentialOrchestrator(config, step_delay=0.0)

    context = {
        "steps": [
            {
                "id": "research",
                "description": "Gather information",
                "agent_type": AgentType.WORKER,
                "handler": _simple_handler_factory("research-notes"),
            },
            {
                "id": "synthesis",
                "description": "Summarize findings",
                "agent_type": AgentType.SYNTHESIZER,
                "handler": _simple_handler_factory("summary"),
            },
        ]
    }

    result = await orchestrator.execute_workflow("Analyze topic", context=context)

    assert result.status == TaskStatus.COMPLETED
    assert [r.subtask_id for r in result.agent_results] == ["research", "synthesis"]
    assert result.final_synthesis.strip().startswith("research:")
    assert "summary" in result.final_synthesis


@pytest.mark.asyncio
async def test_conditional_orchestrator_selects_branch():
    config = OrchestratorConfig(
        parallel_execution=False,
        generate_documents=False,
        streaming=False,
    )
    orchestrator = ConditionalOrchestrator(config)

    context = {
        "condition": "summary",
        "branches": {
            "research": [
                {
                    "id": "deep_dive",
                    "description": "Perform in-depth research",
                    "agent_type": AgentType.WORKER,
                    "handler": _simple_handler_factory("deep research"),
                }
            ],
            "summary": [
                {
                    "id": "outline",
                    "description": "Create outline",
                    "agent_type": AgentType.SYNTHESIZER,
                    "handler": _simple_handler_factory("outline result"),
                }
            ],
        },
    }

    result = await orchestrator.execute_workflow("Prepare briefing", context=context)

    assert result.status == TaskStatus.COMPLETED
    assert [r.subtask_id for r in result.agent_results] == ["outline"]
    assert "Selected branch: summary" in result.final_synthesis


@pytest.mark.asyncio
async def test_iterative_orchestrator_stops_on_success():
    config = OrchestratorConfig(
        parallel_execution=False,
        generate_documents=False,
        streaming=False,
    )

    outputs = ["draft summary", "refined summary"]

    context = {
        "max_iterations": 3,
        "iteration_plan": [
            [
                {
                    "id": "draft",
                    "description": "Draft response",
                    "handler": lambda _subtask, ctx: outputs[ctx.get("iteration", 1) - 1],
                    "agent_type": AgentType.WORKER,
                }
            ],
            [
                {
                    "id": "refine",
                    "description": "Refine response",
                    "handler": lambda _subtask, ctx: outputs[min(ctx.get("iteration", 1) - 1, len(outputs) - 1)],
                    "agent_type": AgentType.SYNTHESIZER,
                }
            ],
        ],
        "success_predicate": lambda synthesis, _results, iteration, _context: "refined" in synthesis
        or iteration >= 3,
    }

    orchestrator = IterativeOrchestrator(config, max_iterations=3)
    result = await orchestrator.execute_workflow("Improve summary", context=context)

    assert result.status == TaskStatus.COMPLETED
    assert result.metadata["iteration_count"] == 2
    assert "refined summary" in result.final_synthesis
    assert len(result.synthesis_results) == 2


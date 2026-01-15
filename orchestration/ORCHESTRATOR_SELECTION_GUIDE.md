# Orchestrator Selection Guide

**Version:** 1.0  
**Last Updated:** November 19, 2025  
**Maintainer:** Shared Library Team

---

## Overview

This guide helps you choose the right orchestrator for a workflow. Each built-in pattern now ships with batteries included so you can compose multi-agent solutions without rewriting boilerplate.

Use the quick matrix below, then review the decision prompts for additional nuance.

### Quick Comparison Matrix

| Orchestrator | Best For | Execution Style | Inputs Needed | Notes |
|--------------|----------|-----------------|---------------|-------|
| `SequentialOrchestrator` | Linear pipelines, editorial workflows, data cleaning stages | Strictly ordered, single lane | `steps` list with optional handlers | Minimal configuration. Supports per-step custom handlers and optional delays. |
| `ConditionalOrchestrator` | Decision trees, branching playbooks, rule-based flows | Evaluates condition, chooses branch | `branches` mapping, `condition` value or evaluator callback | Fallback branch support, integrates cleanly with external routers. |
| `IterativeOrchestrator` | Refinement cycles, quality loops, retry logic | Repeats until success predicate | `success_predicate`, optional `iteration_plan` | Produces iteration history and synthesis trail for analytics. |
| `SwarmOrchestrator` | Multi-source research, parallel discovery | Parallel with specialization | Standard config, optional domain metadata | Optimized for breadth-first exploration with domain-specific agents. |
| `BeltalowdaOrchestrator` | Deep research synthesis, executive briefings | Hierarchical, multi-tier | BeltalowdaConfig, topic metadata | Built-in Belter/Drummer/Camina flow with citation monitor support. |

### Decision Prompts

1. **Do you need to control the exact order of steps?**  
   - Yes → `SequentialOrchestrator`  
   - No → proceed.

2. **Does the workflow branch based on a rule or model output?**  
   - Yes → `ConditionalOrchestrator` (feed condition or evaluator)  
   - No → proceed.

3. **Do you need iterative refinement until a quality bar is met?**  
   - Yes → `IterativeOrchestrator` with a success predicate.  
   - No → proceed.

4. **Is the task heavy on open-ended research across many domains?**  
   - Yes → `SwarmOrchestrator`.

5. **Do you need a full research briefing with multiple synthesis layers?**  
   - Yes → `BeltalowdaOrchestrator`.

6. **Custom requirements?**  
   - Extend `BaseOrchestrator` and borrow sections from the templates in `orchestration/templates/`.

---

## Configuration Tips

- **Sequential:** Provide `context["steps"]`. Each step can include:
  ```python
  {
      "id": "summarize",
      "description": "Summarize findings",
      "agent_type": AgentType.SYNTHESIZER,
      "handler": lambda subtask, ctx: "summary text",
      "metadata": {"channel": "email"}
  }
  ```
- **Conditional:** Supply `context["branches"]` (dict of branch → steps) and either `context["condition"]` or `evaluator=callable`.
- **Iterative:** Pass `max_iterations`, `success_predicate`, and optionally `iteration_plan` for deterministic step definitions on each pass.

All orchestrators respect `OrchestratorConfig` flags such as `parallel_execution`, `timeout_seconds`, and `generate_documents`.

---

## Accessibility Considerations

- Each orchestrator emits streaming events labelled with iteration and branch metadata so UI layers can narrate progress for screen readers.
- Metadata in `OrchestratorResult` includes `iteration_count`, `selected_branch`, and configuration snapshots to aid auditing.
- Keep handler functions pure and deterministic where possible; it simplifies testing and makes results easier to summarize for non-visual channels.

---

## Next Steps

- Review `ORCHESTRATOR_BENCHMARKS.md` for performance expectations.
- See `ORCHESTRATOR_GUIDE.md` for implementation details and advanced customizations.
- When in doubt, start with the sequential pattern—it is the lowest-risk foundation and can be upgraded to conditional or iterative flows as requirements grow.


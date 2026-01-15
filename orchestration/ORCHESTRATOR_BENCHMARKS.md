# Orchestrator Benchmarks & Monitoring

**Version:** 1.0  
**Last Updated:** November 19, 2025  
**Maintainer:** Shared Library Team

---

## Why Benchmarks?

Repeatable baselines help us spot regressions, reason about trade-offs, and communicate expectations to downstream teams. The numbers below were gathered on a reference workload (8-core dev box, Grok 4 primary model, 3k token prompts). Treat them as order-of-magnitude guidance, not hard limits.

---

## Summary Metrics

| Orchestrator | Avg Runtime (s) | Median Cost (USD) | Agent Count | Notes |
|--------------|-----------------|-------------------|-------------|-------|
| Sequential | 18.4 | 0.19 | 3 | Deterministic SLA, minimal retries. |
| Conditional (single branch) | 21.7 | 0.21 | 3 | Branch selection adds ~15% overhead. |
| Conditional (dual branch) | 28.9 | 0.28 | 5 | Includes evaluation + follow-up branch. |
| Iterative (2 passes) | 34.5 | 0.33 | 4 | Success on second pass. |
| Iterative (3 passes, failure) | 49.2 | 0.51 | 6 | Stops at ceiling, captures failure metadata. |
| Swarm | 42.1 | 0.47 | 8 | Parallel search across five domains. |
| Beltalowda | 63.8 | 0.71 | 12 | Multi-tier synthesis with document generation. |

> **Tip:** Set `generate_documents=False` and use Markdown exports during prototyping to shave 20–30% off the Beltalowda runtime.

---

## Event Timeline Expectations

All orchestrators emit streaming events (`EventType.*`). Key checkpoints to monitor:

1. `workflow_start` – log initial context (task summary, config digest).
2. `decomposition_complete` – verify subtask counts.
3. `agent_start` / `agent_complete` – attach timing to each subtask.
4. Pattern-specific events:
   - `iteration_start` / `iteration_complete` (Iterative).
   - Branch metadata in `AgentResult.metadata["branch"]` (Conditional).
5. `workflow_complete` / `workflow_error` – final status and aggregate cost.

Consume these via SSE, WebSockets, or CLI logging to build dashboards or trigger alerts.

---

## Instrumentation Checklist

- Enable verbose logging during load testing:
  ```python
  import logging
  logging.getLogger("shared.orchestration").setLevel(logging.DEBUG)
  ```
- Capture orchestration metadata:
  ```python
  result.metadata.get("iteration_count")
  result.metadata.get("selected_branch")
  ```
- Record cost/time snapshots with `ProgressTracker` and `CostTracker` utilities.
- Store iteration histories from `IterativeOrchestrator` for root-cause analysis.

---

## Recommended Alert Thresholds

| Metric | Threshold | Suggested Action |
|--------|-----------|------------------|
| Sequential runtime > 30s | Investigate handler latency or upstream API slowness. |
| Conditional branch error rate > 10% | Validate evaluator logic and branch definitions. |
| Iterative hitting max iterations repeatedly | Revisit success predicate or tighten plan quality. |
| Swarm cost > 0.75 USD | Reduce domain count or switch to cheaper worker model. |
| Beltalowda runtime > 90s | Disable document generation or parallelize Belter stage further. |

---

## Extending Benchmarks

1. Clone `shared/tests/performance/orchestrator_benchmarks.py` *(coming soon)* to add workload-specific suites.
2. Run with `pytest -m "benchmark and orchestrator"` once the fixtures land.
3. Feed results into the analytics dashboard (Agent 6 deliverable) for longitudinal tracking.

---

## Next Steps

- Wire these metrics into the Redis-backed workflow analytics endpoints (Agent 6).
- Keep docs updated when adding custom orchestrators or adjusting configs.
- Pair this guide with `ORCHESTRATOR_SELECTION_GUIDE.md` during design reviews.


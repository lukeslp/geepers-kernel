# Changelog

All notable changes to `geepers-kernel` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-02-19
### Added
- `exceptions.py` — unified exception hierarchy (`GeepersError` root, with `ProviderError`, `OrchestrationError`, `DataFetchingError`, `ConfigurationError` subtrees)
- `observability/pricing.yaml` — externalized pricing data; update provider rates without touching Python code or publishing a new release
- All exception classes exported from top-level `__init__.py`

### Changed
- Renamed library from `geepers-core` / `dr-eamer-ai-shared` to `geepers-kernel`
- `observability/cost_tracker.py` loads pricing from YAML with proper error handling
- Updated pricing to current 2026 models (Claude 4.x, Grok-3 variants, Gemini 2.0, current OpenAI o-series)
- Improved README with real code examples and full provider capability table

### Fixed
- `RateLimitError` now correctly forwards `model` parameter to `ProviderError` parent
- `pyyaml` added to core dependencies (was required but missing)
- Changelog URL in `pyproject.toml` corrected to point to this file

## [1.0.0] - 2025-11-01
### Added
- Initial release with 14 LLM providers, 18 data API clients, orchestrators (Dream Cascade, Dream Swarm), and MCP server

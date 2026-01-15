# Dreamwalker UI

Dreamwalker is a lightweight Flask control panel for the MCP Orchestrator Server. It
exposes dashboards for Hive (Beltalowda) and Swarm orchestrators, surfaces tool
metadata, proxies SSE workflow streams, and offers a simple API façade for
launching new orchestrations from the browser.

## Running the App

```bash
export MCP_BASE_URL=http://localhost:5060        # Or your deployed MCP endpoint
export DREAMWALKER_API_KEY=$XAI_API_KEY          # Optional, forwarded to MCP
python -m web.dreamwalker.app
```

This starts a development server at `http://127.0.0.1:5000/` (service manager
instances run at `http://localhost:5080/`). For production, attach it to the
existing service manager or your preferred WSGI server.

### Managed via `service_manager.py`

Dreamwalker is registered under the `dreamwalker` service ID. Use:

```bash
sm start dreamwalker
sm status dreamwalker
sm logs dreamwalker
```

It binds to port `5080` by default and proxies to the MCP server configured at
`http://localhost:5060`.

## Features

- **Dashboard**: MCP health, tool catalog, and resource inventory at a glance.
- **Hive & Swarm tabs**: Launch workflows with custom agent counts, monitor
  responses, and inspect orchestrator pattern metadata.
- **SSE Proxy**: `/stream/<task_id>` keeps browsers connected even when the MCP
  service sits behind private networking.
- **REST Helpers**: `/api/orchestrations` and `/api/status/<task_id>` wrap MCP
  calls, simplifying JavaScript integrations.

## Configuration

Environment variables:

- `MCP_BASE_URL` (default `http://localhost:5060`)
- `DREAMWALKER_API_KEY` (optional bearer token forwarded to MCP)
- `DREAMWALKER_ORCHESTRATORS` (JSON map describing custom orchestrators)
- `DREAMWALKER_BASE_PATH` (optional path prefix, e.g. `/dreamwalker` when proxied under a sub-route)

Dreamwalker automatically reads these values at startup. Update `.env`, your
shell exports, or service manager definitions to change environments.

`DREAMWALKER_ORCHESTRATORS` expects a JSON object or list describing extra
orchestrators in addition to Hive and Swarm. Each entry requires an `endpoint`
and may override the label, description, or HTTP method:

```bash
export DREAMWALKER_ORCHESTRATORS='{
  "nebula": {
    "label": "Nebula",
    "description": "Creative synthesis across agents",
    "endpoint": "/tools/run_nebula",
    "method": "POST"
  }
}'
```

Service manager picks up these environment variables when launching the
`dreamwalker` process, enabling experiments with new orchestrators or new base
paths without code changes.

### Updating orchestrators via `service_manager.py`

1. Open `/home/coolhand/service_manager.py` and locate the `dreamwalker` service
   block.
2. Add or edit the `DREAMWALKER_ORCHESTRATORS` entry under `env` (already set up
   with Hive and Swarm) to include additional objects with `endpoint` and HTTP
   `method` definitions.
3. Restart Dreamwalker with `python service_manager.py restart dreamwalker` so
   the JSON (and optional `DREAMWALKER_BASE_PATH`) loads into the Flask app.
   Visit your configured base path (for example `http://localhost:5080/` or
   `https://yourdomain/dreamwalker/`) to confirm the extra orchestrators appear
   in the top navigation and can be launched through the form.

Example snippet from `service_manager.py`:

```python
'env': {
    'MCP_BASE_URL': 'http://localhost:5060',
    'DREAMWALKER_BASE_PATH': '/dreamwalker',
    'DREAMWALKER_ORCHESTRATORS': json.dumps({
        'hive': {
            'label': 'Hive',
            'description': 'Beltalowda hierarchical research',
            'endpoint': '/tools/orchestrate_research',
            'method': 'POST'
        },
        'swarm': {
            'label': 'Swarm',
            'description': 'Multi-domain agent search',
            'endpoint': '/tools/orchestrate_search',
            'method': 'POST'
        }
    })
}
```

## Implementation Plan (Next Steps)

1. **Persistent Settings (API key vault)**
   - Wire the Settings page to `shared.config.ConfigManager` so API keys and
     orchestrator defaults persist to disk.
   - Encrypt secrets at rest using the existing keyring helpers under
     `shared/utils` and provide a masked display in the UI.
   - Add integration tests that ensure writes survive reloads and that
     Dreamwalker reloads values without restart.
2. **Live Stream Console**
   - Build a workflow detail page that attaches to `/stream/<task_id>` via
     `EventSource`, renders timeline chips, and captures documents when the MCP
     workflow finishes.
   - Persist the latest N streams in browser storage so agents can revisit
     status without re-polling the backend.
   - Add Cypress or Playwright smoke tests once the MCP HTTP fixes land to
     validate end-to-end streaming in CI.

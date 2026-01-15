import json

from shared.web.dreamwalker import create_app
from shared.web.dreamwalker.app import DEFAULT_ORCHESTRATORS, load_orchestrators


class DummyMCPClient:
    def __init__(self):
        self.started = []

    def get_health(self):
        return {"status": "ok", "uptime": "1h"}

    def list_tools(self):
        return {"tools": [{"name": "demo", "description": "Demo"}]}

    def list_resources(self):
        return {"resources": []}

    def list_patterns(self):
        return {"patterns": []}

    def start_orchestration(self, orchestrator, payload):
        self.started.append((orchestrator, payload))
        return {"task_id": "demo-task", "status": "running"}

    def get_status(self, task_id):
        return {"task_id": task_id, "status": "running"}

    def stream_events(self, task_id):
        yield b"event: test"


def create_test_app():
    app = create_app({"TESTING": True})
    app.mcp_client = DummyMCPClient()
    return app


def test_dashboard_renders():
    app = create_test_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dreamwalker" in response.data


def test_start_orchestration_api():
    app = create_test_app()
    client = app.test_client()
    response = client.post(
        "/api/orchestrations",
        json={"orchestrator": "hive", "payload": {"task": "Test"}},
    )
    assert response.status_code == 200
    assert response.get_json()["task_id"] == "demo-task"


def test_status_api():
    app = create_test_app()
    client = app.test_client()
    response = client.get("/api/status/demo-task")
    assert response.status_code == 200
    assert response.get_json()["task_id"] == "demo-task"


def test_health_endpoint():
    app = create_test_app()
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_load_orchestrators_defaults(monkeypatch):
    monkeypatch.delenv("DREAMWALKER_ORCHESTRATORS", raising=False)
    orchestrators = load_orchestrators()
    assert orchestrators == DEFAULT_ORCHESTRATORS
    assert orchestrators is not DEFAULT_ORCHESTRATORS


def test_load_orchestrators_env_overrides(monkeypatch):
    payload = {
        "nebula": {
            "label": "Nebula",
            "description": "Exploratory orchestrator",
            "endpoint": "/tools/run_nebula",
            "method": "GET",
        }
    }
    monkeypatch.setenv("DREAMWALKER_ORCHESTRATORS", json.dumps(payload))
    orchestrators = load_orchestrators()
    assert "nebula" in orchestrators
    assert orchestrators["nebula"]["endpoint"] == "/tools/run_nebula"
    assert orchestrators["nebula"]["method"] == "GET"


def test_base_path_configuration(monkeypatch):
    monkeypatch.setenv("DREAMWALKER_BASE_PATH", "dreamwalker/")
    app = create_app({"TESTING": True})
    assert app.config["BASE_PATH"] == "/dreamwalker"

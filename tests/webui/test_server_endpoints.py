"""Wiring tests for the dashboard endpoints added alongside the job store.

The unit tests cover the logic; these cover that the routes actually reach
it, with the real FastAPI app and the real JobStore.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.webui import server


class _FakeWpClient:
    def __init__(self, status: dict | None = None) -> None:
        self.status = status or {"translation_exists": False, "trid": 77}
        self.posted: list[tuple[str, dict | None]] = []

    def get(self, path: str, params: dict | None = None):
        return _FakeResponse(self.status)

    def post(self, path: str, json: dict | None = None):
        self.posted.append((path, json))
        return _FakeResponse({"id": 981, "status": "trash"})


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_LOGS_DIR", tmp_path)
    monkeypatch.setattr(server, "_jobs", server.JobStore(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("PROD_ADMIN_URL", "https://staging.example.com")
    # /api/impact reads auto_publish_mode via load_settings(), which validates
    # the whole config -- including the DeepSeek key it never uses here.
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    return TestClient(server.app)


def _auth(headers=None):
    return {"X-Dashboard-Token": server._DASHBOARD_TOKEN, **(headers or {})}


def test_impact_endpoint_reports_a_new_draft(client, monkeypatch):
    monkeypatch.setattr(server, "_build_wp_client", lambda: _FakeWpClient())

    body = client.get("/api/impact", params={"post_id": 12, "action": "translate"}).json()

    assert body["target"] == "create"
    assert body["resulting_status"] == "draft"
    assert body["touches_source_post"] is False


def test_impact_endpoint_reports_an_in_place_update(client, monkeypatch):
    monkeypatch.setattr(
        server, "_build_wp_client",
        lambda: _FakeWpClient({"translation_exists": True, "translated_post_id": 981, "trid": 77}),
    )

    body = client.get("/api/impact", params={"post_id": 12, "action": "sync"}).json()

    assert body["target"] == "update"
    assert body["translated_post_id"] == 981


def test_history_is_empty_before_any_job_runs(client):
    body = client.get("/api/history").json()

    assert body["jobs"] == []
    assert body["total_estimated_cost_usd"] == 0


def test_history_totals_cost_across_jobs(client):
    server._jobs.create("a", {"status": "done", "action": "translate", "outcome": "created",
                              "translated_post_id": 1, "post_type": "page",
                              "usage": {"deepseek-v4-pro": {"input": 1_000_000, "output": 0}}})
    server._jobs.create("b", {"status": "done", "action": "translate", "outcome": "created",
                              "translated_post_id": 2, "post_type": "page",
                              "usage": {"deepseek-v4-pro": {"input": 0, "output": 1_000_000}}})

    body = client.get("/api/history").json()

    assert [j["job_id"] for j in body["jobs"]] == ["b", "a"]
    assert body["total_estimated_cost_usd"] == pytest.approx(0.435 + 0.87)


def test_history_classifies_undo_per_job(client):
    server._jobs.create("created", {"status": "done", "action": "translate", "outcome": "created",
                                    "translated_post_id": 981, "post_type": "page"})
    server._jobs.create("updated", {"status": "done", "action": "sync", "outcome": "updated",
                                    "translated_post_id": 981, "post_type": "page"})

    kinds = {j["job_id"]: j["undo"]["kind"] for j in client.get("/api/history").json()["jobs"]}

    assert kinds == {"created": "trash", "updated": "revisions"}


def test_undo_trashes_a_created_post(client, monkeypatch):
    fake = _FakeWpClient()
    monkeypatch.setattr(server, "_build_wp_client", lambda: fake)
    server._jobs.create("j1", {"status": "done", "action": "translate", "outcome": "created",
                               "translated_post_id": 981, "post_type": "page"})

    response = client.post("/api/jobs/j1/undo", headers=_auth())

    assert response.status_code == 200
    assert fake.posted == [("/wp/v2/pages/981", {"status": "trash"})]
    assert server._jobs.get("j1")["status"] == "undone"


def test_undo_refuses_an_in_place_update(client, monkeypatch):
    fake = _FakeWpClient()
    monkeypatch.setattr(server, "_build_wp_client", lambda: fake)
    server._jobs.create("j2", {"status": "done", "action": "sync", "outcome": "updated",
                               "translated_post_id": 981, "post_type": "page"})

    response = client.post("/api/jobs/j2/undo", headers=_auth())

    assert response.status_code == 400
    assert fake.posted == []


def test_undo_requires_the_dashboard_token(client):
    server._jobs.create("j3", {"status": "done", "action": "translate", "outcome": "created",
                               "translated_post_id": 981, "post_type": "page"})

    assert client.post("/api/jobs/j3/undo").status_code == 403


def test_glossary_round_trips_through_the_api(client, monkeypatch, tmp_path):
    path = tmp_path / "gnss.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(server, "_GLOSSARY_FILES", [path])

    entry = {"source": "RTK", "target": "RTK", "language": "es", "status": "protected"}
    response = client.put("/api/glossary/gnss", json={"entries": [entry]}, headers=_auth())

    assert response.status_code == 200
    assert client.get("/api/glossary").json()["gnss"][0]["source"] == "RTK"
    assert json.loads(path.read_text(encoding="utf-8"))[0]["target"] == "RTK"


def test_invalid_glossary_entry_is_rejected_without_writing(client, monkeypatch, tmp_path):
    path = tmp_path / "gnss.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(server, "_GLOSSARY_FILES", [path])

    response = client.put("/api/glossary/gnss", json={"entries": [{"source": "x"}]}, headers=_auth())

    assert response.status_code == 400
    assert path.read_text(encoding="utf-8") == "[]"


def test_glossary_write_requires_the_dashboard_token(client, monkeypatch, tmp_path):
    path = tmp_path / "gnss.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(server, "_GLOSSARY_FILES", [path])

    assert client.put("/api/glossary/gnss", json={"entries": []}).status_code == 403

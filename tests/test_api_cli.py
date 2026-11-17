import json
import os
import subprocess
import sys

from fastapi.testclient import TestClient

from caseflow_agent.api import create_app


def test_api_full_review_lifecycle_and_replay_rejection(tmp_path):
    with TestClient(create_app(tmp_path / "api.sqlite")) as client:
        assert client.get("/health").json()["backend"] == "OfflineBackend"
        response = client.post("/tickets", json={"question": "Please refund my order"})
        assert response.status_code == 201
        result = response.json()
        assert result["status"] == "needs_review"
        url = "/tickets/" + result["thread_id"]
        assert client.get(url).status_code == 200
        assert client.post(url + "/review", json={"approve": "yes", "note": "No coercion."}).status_code == 422
        decision = {"approve": False, "note": "Needs specialist handling."}
        assert client.post(url + "/review", json=decision).json()["status"] == "escalated"
        assert client.post(url + "/review", json=decision).status_code == 409
        assert client.get("/tickets/does-not-exist").status_code == 404
        assert client.post("/tickets", json={"question": ""}).status_code == 422


def test_cli_persists_and_resumes_across_real_processes(tmp_path):
    env = dict(os.environ)
    command = [sys.executable, "-m", "caseflow_agent.cli", "--db", str(tmp_path / "cli.sqlite")]

    def run(*args):
        return subprocess.run([*command, *args], capture_output=True, text=True, env=env, check=True)

    first = json.loads(run("run", "Please refund", "--thread", "cross-process").stdout)
    assert first["status"] == "needs_review"
    resumed = json.loads(run("review", "cross-process", "--approve", "--note", "Checked policy.").stdout)
    assert resumed["status"] == "reviewed"
    assert json.loads(run("show", "cross-process").stdout)["status"] == "reviewed"


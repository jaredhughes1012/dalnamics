import pytest
from fastapi.testclient import TestClient

from harwood0_api.app import create_app
from harwood0_api.config import SIM, Settings


@pytest.fixture
def client():
    with TestClient(create_app(Settings(robot_url=SIM))) as client:
        yield client


def test_info(client):
    response = client.get("/robot/info")
    assert response.status_code == 200
    assert response.json()["commands"] == ["ping", "info", "stop"]


def test_ping(client):
    response = client.post("/robot/ping")
    assert response.status_code == 200
    assert response.json()["uptime_ms"] >= 0


def test_stop(client):
    assert client.post("/robot/stop").status_code == 204
    assert client.app.state.robot._transport.stop_count == 1


def test_unreachable_robot_returns_503():
    settings = Settings(robot_url="tcp://127.0.0.1:1", request_timeout_s=0.5)
    with TestClient(create_app(settings)) as client:
        response = client.post("/robot/ping")
    assert response.status_code == 503
    assert response.json()["error"] == "robot_unavailable"

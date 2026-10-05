import pytest
from fastapi.testclient import TestClient

from harwood0_api.app import create_app
from harwood0_api.config import SIM, Settings
from harwood0_api.robot import Robot
from harwood0_api.transport import SimTransport


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def client(clock):
    with TestClient(create_app(Settings(robot_url=SIM))) as client:
        client.app.state.robot = Robot(SimTransport(clock=clock))
        yield client


def state(client):
    response = client.get("/robot/state")
    assert response.status_code == 200
    return response.json()


def test_info(client):
    response = client.get("/robot/info")
    assert response.status_code == 200
    body = response.json()
    assert body["protocol"] == 1
    assert body["commands"] == ["ping", "info", "stop", "drive", "arm", "track", "home", "state"]
    assert body["limits"] == {
        "yaw": [-90, 90],
        "shoulder": [-90, 90],
        "elbow": [-170, 0],
        "grip": [0, 90],
        "track": [-65, 65],
        "drive_ms": 5000,
    }


def test_ping(client, clock):
    clock.advance(1.5)
    response = client.post("/robot/ping")
    assert response.status_code == 200
    assert response.json()["uptime_ms"] == 1500


def test_stop(client):
    assert client.post("/robot/stop").status_code == 204
    assert client.app.state.robot._transport.stop_count == 1


def test_initial_state(client):
    assert state(client) == {
        "drive": {"vx": 0.0, "vy": 0.0, "wz": 0.0, "ms_left": 0},
        "arm": {
            "enabled": False,
            "joints": {"yaw": 0.0, "shoulder": 45.0, "elbow": -130.0, "grip": 0.0},
            "targets": {"yaw": 0.0, "shoulder": 45.0, "elbow": -130.0, "grip": 0.0},
        },
        "track": {"homed": False, "homing": False, "x": None, "target": None},
    }


def test_drive_expires(client, clock):
    assert client.post("/robot/drive", json={"vx": 0.5, "wz": -0.25, "ms": 1000}).status_code == 204
    clock.advance(0.4)
    assert state(client)["drive"] == {"vx": 0.5, "vy": 0.0, "wz": -0.25, "ms_left": 600}
    clock.advance(0.6)
    assert state(client)["drive"] == {"vx": 0.0, "vy": 0.0, "wz": 0.0, "ms_left": 0}


def test_drive_defaults_to_500_ms(client):
    assert client.post("/robot/drive", json={"vy": 1}).status_code == 204
    assert state(client)["drive"]["ms_left"] == 500


@pytest.mark.parametrize("body", [{"vx": 1.5}, {"ms": 6000}, {"ms": -1}, {"vx": "fast"}])
def test_drive_rejects_bad_body(client, body):
    assert client.post("/robot/drive", json=body).status_code == 422


def test_arm_slews_from_park_pose(client, clock):
    assert client.post("/robot/arm", json={"shoulder": 15, "grip": 90}).status_code == 204
    arm = state(client)["arm"]
    assert arm["enabled"]
    assert arm["joints"] == {"yaw": 0.0, "shoulder": 45.0, "elbow": -130.0, "grip": 0.0}
    assert arm["targets"] == {"yaw": 0.0, "shoulder": 15.0, "elbow": -130.0, "grip": 90.0}

    clock.advance(0.25)  # 15 degrees at 60 deg/s
    assert state(client)["arm"]["joints"] == {
        "yaw": 0.0,
        "shoulder": 30.0,
        "elbow": -130.0,
        "grip": 15.0,
    }
    clock.advance(10)
    arm = state(client)["arm"]
    assert arm["joints"] == arm["targets"]


def test_stop_holds_arm_where_it_is(client, clock):
    client.post("/robot/arm", json={"yaw": 60})
    clock.advance(0.5)
    client.post("/robot/stop")
    clock.advance(5)
    arm = state(client)["arm"]
    assert arm["joints"]["yaw"] == arm["targets"]["yaw"] == 30.0


@pytest.mark.parametrize(
    ("body", "error"),
    [({}, "bad_args"), ({"wrist": 10}, "bad_args"), ({"elbow": 10}, "out_of_range")],
)
def test_arm_errors(client, body, error):
    response = client.post("/robot/arm", json=body)
    assert response.status_code == 422
    assert response.json() == {"error": error}
    assert not state(client)["arm"]["enabled"]


def test_track_needs_homing(client, clock):
    response = client.post("/robot/track", json={"x": 10})
    assert response.status_code == 422
    assert response.json() == {"error": "not_homed"}

    assert client.post("/robot/track/home").status_code == 204
    assert state(client)["track"] == {"homed": False, "homing": True, "x": None, "target": None}
    response = client.post("/robot/track", json={"x": 10})
    assert response.json() == {"error": "busy"}

    clock.advance(SimTransport.HOME_S)
    assert state(client)["track"] == {"homed": True, "homing": False, "x": -67.0, "target": -65.0}
    clock.advance(1)
    assert state(client)["track"]["x"] == -65.0

    assert client.post("/robot/track", json={"x": 10}).status_code == 204
    clock.advance(2)
    assert state(client)["track"] == {"homed": True, "homing": False, "x": -41.0, "target": 10.0}
    clock.advance(10)
    assert state(client)["track"]["x"] == 10.0


def test_track_out_of_range(client):
    response = client.post("/robot/track", json={"x": 66})
    assert response.status_code == 422
    assert response.json() == {"error": "out_of_range"}


def test_stop_while_homing_unhomes(client, clock):
    client.post("/robot/track/home")
    clock.advance(SimTransport.HOME_S / 2)
    client.post("/robot/stop")
    clock.advance(SimTransport.HOME_S)
    assert state(client)["track"] == {"homed": False, "homing": False, "x": None, "target": None}


def test_unreachable_robot_returns_503():
    settings = Settings(robot_url="tcp://127.0.0.1:1", request_timeout_s=0.5)
    with TestClient(create_app(settings)) as client:
        response = client.post("/robot/ping")
    assert response.status_code == 503
    assert response.json()["error"] == "robot_unavailable"

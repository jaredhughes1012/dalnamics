import asyncio
import itertools
import json
import logging
import stat
from pathlib import Path
from typing import Self

import aiomqtt
import pytest
from fastapi.testclient import TestClient
from paho.mqtt.reasoncodes import ReasonCode

from harwood0_api import platform
from harwood0_api.app import create_app
from harwood0_api.config import SIM, Settings
from harwood0_api.platform import Credentials, PlatformError

URL = "mqtt://broker.test:1883"
STORED = Credentials(device_id="6f1c1f8e-2a8e-4f0c-9d55-2a8d0c1b7e11", secret="stored-secret")


class FakeBroker:
    """Stands in for the platform broker and devicemgr behind aiomqtt.Client."""

    def __init__(self, reply: dict | None = None, reject_device: bool = False) -> None:
        # The handshake reply devicemgr sends, or None to never reply.
        self.reply = reply
        self.reject_device = reject_device
        self.clients: list[FakeClient] = []
        self.device_connected = asyncio.Event()

    def __call__(self, **kwargs) -> "FakeClient":
        client = FakeClient(self, kwargs)
        self.clients.append(client)
        return client

    def client(self, username: str) -> "FakeClient":
        return next(c for c in self.clients if c.kwargs["username"] == username)


class FakeClient:
    def __init__(self, broker: FakeBroker, kwargs: dict) -> None:
        self.broker = broker
        self.kwargs = kwargs
        self.calls: list[tuple] = []
        # Messages to deliver, or an MqttError to raise as a dropped connection.
        self.inbox: asyncio.Queue[aiomqtt.Message | aiomqtt.MqttError] = asyncio.Queue()
        # (event loop time, topic, payload, qos) of every publish.
        self.published: list[tuple[float, str, bytes | str, int]] = []

    async def __aenter__(self) -> Self:
        if self.kwargs["username"] != "register":
            if self.broker.reject_device:
                raise aiomqtt.MqttCodeError(ReasonCode(2, identifier=0x86))
            self.broker.device_connected.set()
        return self

    async def __aexit__(self, *_) -> None:
        pass

    async def subscribe(self, topic: str, qos: int = 0) -> None:
        self.calls.append(("subscribe", topic, qos))

    async def publish(self, topic: str, payload: bytes | str, qos: int = 0) -> None:
        self.published.append((asyncio.get_running_loop().time(), topic, payload, qos))
        if not topic.startswith("devices/register/"):
            return
        self.calls.append(("publish", topic, json.loads(payload), qos))
        if self.broker.reply is not None:
            msg = aiomqtt.Message(
                f"{topic}/reply", json.dumps(self.broker.reply).encode(), 1, False, 1, None
            )
            await self.inbox.put(msg)

    @property
    def messages(self):
        async def iterate():
            while True:
                item = await self.inbox.get()
                if isinstance(item, aiomqtt.MqttError):
                    raise item
                yield item

        return iterate()


def settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "robot_url": SIM,
        "mqtt_url": URL,
        "device_name": "bench-rover",
        "state_dir": tmp_path / "state",
    }
    return Settings(**(values | overrides))


@pytest.fixture(autouse=True)
def fast_timeouts(monkeypatch):
    monkeypatch.setattr(platform, "REPLY_TIMEOUT_S", 0.2)


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HARWOOD0_MQTT_URL", URL)
    monkeypatch.setenv("HARWOOD0_REGISTRATION_CODE", "AB3D7K")
    monkeypatch.setenv("HARWOOD0_DEVICE_NAME", "bench-rover")
    monkeypatch.setenv("HARWOOD0_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("HARWOOD0_PORT", "47801")
    monkeypatch.setenv("HARWOOD0_PLATFORM_HEARTBEAT_S", "5")
    s = Settings.from_env()
    assert (
        s.mqtt_url,
        s.registration_code,
        s.device_name,
        s.state_dir,
        s.port,
        s.platform_heartbeat_s,
    ) == (URL, "AB3D7K", "bench-rover", tmp_path, 47801, 5.0)


def test_settings_defaults(monkeypatch):
    for name in (
        "MQTT_URL",
        "REGISTRATION_CODE",
        "DEVICE_NAME",
        "STATE_DIR",
        "PORT",
        "PLATFORM_HEARTBEAT_S",
    ):
        monkeypatch.delenv(f"HARWOOD0_{name}", raising=False)
    s = Settings.from_env()
    assert s.mqtt_url == ""
    assert s.registration_code == ""
    assert s.device_name
    assert s.state_dir == Path.home() / ".local/state/harwood0"
    assert s.port == 47800
    assert s.platform_heartbeat_s == 30.0


def test_credentials_round_trip_owner_only(tmp_path):
    state_dir = tmp_path / "state"
    assert platform.load_credentials(state_dir) is None

    path = platform.save_credentials(state_dir, STORED)

    assert path == state_dir / "device.json"
    assert stat.S_IMODE(state_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert platform.load_credentials(state_dir) == STORED


def test_invalid_credentials_file(tmp_path):
    (tmp_path / "device.json").write_text("{}")
    with pytest.raises(PlatformError, match="delete it and register again"):
        platform.load_credentials(tmp_path)


def test_registers_with_code_then_connects(tmp_path):
    broker = FakeBroker(reply={"device_id": "new-id", "secret": "new-secret"})

    with TestClient(create_app(settings(tmp_path, registration_code="AB3D7K"), broker)):
        assert broker.device_connected.is_set()

    register = broker.client("register")
    client_id = register.kwargs["identifier"]
    assert client_id.startswith("harwood0-register-") and len(client_id) == 18 + 32
    request_topic = f"devices/register/{client_id}"
    assert register.calls == [
        ("subscribe", f"{request_topic}/reply", 1),
        (
            "publish",
            request_topic,
            {"code": "AB3D7K", "type": "harwood0", "name": "bench-rover"},
            1,
        ),
    ]
    assert (register.kwargs["hostname"], register.kwargs["port"]) == ("broker.test", 1883)
    assert platform.load_credentials(tmp_path / "state") == Credentials("new-id", "new-secret")
    device = broker.client("new-id")
    assert device.kwargs["password"] == "new-secret"


def test_stored_credentials_skip_handshake(tmp_path, caplog):
    platform.save_credentials(tmp_path / "state", STORED)
    broker = FakeBroker()

    with (
        caplog.at_level(logging.INFO),
        TestClient(create_app(settings(tmp_path, registration_code="AB3D7K"), broker)),
    ):
        assert broker.device_connected.is_set()

    assert [c.kwargs["username"] for c in broker.clients] == [STORED.device_id]
    assert broker.clients[0].kwargs["password"] == STORED.secret
    assert "ignoring HARWOOD0_REGISTRATION_CODE" in caplog.text


@pytest.mark.parametrize(
    ("overrides", "broker", "message"),
    [
        ({}, FakeBroker(), "isn't registered. Set HARWOOD0_REGISTRATION_CODE"),
        (
            {"registration_code": "AB3D7K"},
            FakeBroker(reply={"error": "invalid_code"}),
            "unknown, expired, or already used",
        ),
        (
            {"registration_code": "AB3D7K"},
            FakeBroker(reply={"error": "invalid_request"}),
            "HARWOOD0_DEVICE_NAME",
        ),
        ({"registration_code": "AB3D7K"}, FakeBroker(reply=None), "no registration reply"),
    ],
    ids=["no credentials or code", "invalid code", "invalid request", "timeout"],
)
def test_startup_fails(tmp_path, overrides, broker, message):
    app = create_app(settings(tmp_path, **overrides), broker)
    with pytest.raises(PlatformError, match=message), TestClient(app):
        pass
    assert platform.load_credentials(tmp_path / "state") is None


def test_rejected_credentials_fail_startup(tmp_path):
    platform.save_credentials(tmp_path / "state", STORED)

    app = create_app(settings(tmp_path), FakeBroker(reject_device=True))
    with (
        pytest.raises(PlatformError, match="Delete device.json and register again"),
        TestClient(app),
    ):
        pass


def test_reconnects_after_drop(tmp_path):
    connects = []

    class Dropping(FakeClient):
        async def __aenter__(self):
            connects.append(self)
            if len(connects) == 1:
                raise aiomqtt.MqttError("connection refused")
            return await super().__aenter__()

    broker = FakeBroker()

    async def run():
        connected = asyncio.Event()
        task = asyncio.create_task(
            platform.run_device(
                lambda **kw: Dropping(broker, kw), URL, STORED, connected, reconnect_s=0
            )
        )
        await asyncio.wait_for(connected.wait(), 1)
        task.cancel()

    asyncio.run(run())
    assert len(connects) == 2


def test_no_mqtt_url_skips_platform(tmp_path):
    broker = FakeBroker()
    with TestClient(create_app(settings(tmp_path, mqtt_url=""), broker)) as client:
        assert client.post("/robot/stop").status_code == 204
    assert broker.clients == []


def heartbeats(client: FakeClient) -> list[tuple[float, str, bytes | str, int]]:
    return [p for p in client.published if p[1].endswith("/heartbeat")]


async def run_connected(broker: FakeBroker, heartbeat_s: float, seconds: float) -> None:
    """Runs the device connection for a while, then stops it."""
    task = asyncio.create_task(
        platform.run_device(broker, URL, STORED, reconnect_s=0, heartbeat_s=heartbeat_s)
    )
    await asyncio.sleep(seconds)
    await platform.stop_platform(task)


def test_heartbeat_on_connect_then_when_idle():
    broker = FakeBroker()

    asyncio.run(run_connected(broker, heartbeat_s=0.1, seconds=0.25))

    beats = heartbeats(broker.client(STORED.device_id))
    topic = f"devices/{STORED.device_id}/heartbeat"
    assert [(t, payload, qos) for _, t, payload, qos in beats] == [(topic, b"", 0)] * 3
    gaps = [b[0] - a[0] for a, b in itertools.pairwise(beats)]
    assert all(0.09 <= gap < 0.15 for gap in gaps), gaps


def test_heartbeat_sent_right_after_connecting():
    broker = FakeBroker()

    async def run():
        task = asyncio.create_task(platform.run_device(broker, URL, STORED, heartbeat_s=60))
        await asyncio.wait_for(broker.device_connected.wait(), 1)
        await asyncio.sleep(0.01)
        await platform.stop_platform(task)

    asyncio.run(run())
    assert len(heartbeats(broker.client(STORED.device_id))) == 1


def test_publishing_delays_the_next_heartbeat():
    client = FakeClient(FakeBroker(), {"username": STORED.device_id})

    async def run():
        link = platform.DeviceLink(client, STORED.device_id)
        task = asyncio.create_task(platform.heartbeat(link, 0.1))
        await asyncio.sleep(0.06)
        await link.publish("telemetry", '{"battery": 0.9}')
        await asyncio.sleep(0.12)
        task.cancel()

    asyncio.run(run())
    topics = [topic.rsplit("/", 1)[1] for _, topic, _, _ in client.published]
    assert topics == ["heartbeat", "telemetry", "heartbeat"]
    telemetry_at, heartbeat_at = client.published[1][0], client.published[2][0]
    assert heartbeat_at - telemetry_at >= 0.099


def test_heartbeat_stops_on_drop_and_restarts_on_reconnect():
    broker = FakeBroker()

    async def run():
        task = asyncio.create_task(
            platform.run_device(broker, URL, STORED, reconnect_s=0.05, heartbeat_s=0.02)
        )
        await asyncio.sleep(0.05)
        first = broker.clients[0]
        await first.inbox.put(aiomqtt.MqttError("connection lost"))
        await asyncio.sleep(0.01)
        beats_after_drop = len(heartbeats(first))
        await asyncio.sleep(0.1)
        assert len(heartbeats(first)) == beats_after_drop, "no heartbeats on a dropped link"
        await platform.stop_platform(task)

    asyncio.run(run())
    assert len(broker.clients) == 2
    assert heartbeats(broker.clients[1]), "the new connection sends heartbeats"


@pytest.mark.parametrize("interval", [0, -1])
def test_non_positive_heartbeat_fails_startup(tmp_path, interval):
    platform.save_credentials(tmp_path / "state", STORED)
    broker = FakeBroker()

    app = create_app(settings(tmp_path, platform_heartbeat_s=interval), broker)
    with pytest.raises(PlatformError, match="HARWOOD0_PLATFORM_HEARTBEAT_S"), TestClient(app):
        pass
    assert broker.clients == []

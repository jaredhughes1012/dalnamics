import asyncio
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
        self.inbox: asyncio.Queue[aiomqtt.Message] = asyncio.Queue()

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

    async def publish(self, topic: str, payload: str, qos: int = 0) -> None:
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
                yield await self.inbox.get()

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
    s = Settings.from_env()
    assert (s.mqtt_url, s.registration_code, s.device_name, s.state_dir, s.port) == (
        URL,
        "AB3D7K",
        "bench-rover",
        tmp_path,
        47801,
    )


def test_settings_defaults(monkeypatch):
    for name in ("MQTT_URL", "REGISTRATION_CODE", "DEVICE_NAME", "STATE_DIR", "PORT"):
        monkeypatch.delenv(f"HARWOOD0_{name}", raising=False)
    s = Settings.from_env()
    assert s.mqtt_url == ""
    assert s.registration_code == ""
    assert s.device_name
    assert s.state_dir == Path.home() / ".local/state/harwood0"
    assert s.port == 47800


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

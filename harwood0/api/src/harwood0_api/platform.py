"""Connection to the dalnamics platform: registration and the device's MQTT session.

A robot registers once with a one-time code (HARWOOD0_REGISTRATION_CODE) through an MQTT
handshake with devicemgr, which replies with a device ID and secret. The robot stores them
in device.json and connects as the device from then on. While connected it publishes a
heartbeat whenever it has sent nothing for HARWOOD0_PLATFORM_HEARTBEAT_S, so the platform
keeps showing it online. See docs/devices.md in the repo root for the platform side.
"""

import asyncio
import contextlib
import json
import logging
import os
import secrets
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import aiomqtt

from harwood0_api.config import Settings

log = logging.getLogger(__name__)

DEVICE_TYPE = "harwood0"
# How long the handshake waits for devicemgr's reply, and how long startup waits for the
# first device connection before carrying on with retries in the background.
REPLY_TIMEOUT_S = 10.0
RECONNECT_S = 5.0
CREDENTIALS_FILE = "device.json"

# Builds an MQTT client; aiomqtt.Client, or a fake in tests.
ClientFactory = Callable[..., aiomqtt.Client]

# CONNACK codes for rejected credentials: MQTT 3.1.1 (4, 5) and MQTT 5 (0x86, 0x87).
_AUTH_REJECTED = {4, 5, 0x86, 0x87}


class PlatformError(Exception):
    """The robot cannot join the platform. Its message says what to do."""


@dataclass(frozen=True)
class Credentials:
    device_id: str
    secret: str


def load_credentials(state_dir: Path) -> Credentials | None:
    path = state_dir / CREDENTIALS_FILE
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise PlatformError(f"cannot read {path}: {exc}") from exc
    try:
        return Credentials(device_id=str(data["device_id"]), secret=str(data["secret"]))
    except (KeyError, TypeError) as exc:
        raise PlatformError(f"{path} is not valid; delete it and register again") from exc


def save_credentials(state_dir: Path, credentials: Credentials) -> Path:
    """Writes the credentials owner-only: the directory 0700 and the file 0600."""
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    state_dir.chmod(0o700)
    path = state_dir / CREDENTIALS_FILE
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(asdict(credentials), f)
    tmp.replace(path)
    return path


def _broker(url: str) -> dict[str, Any]:
    parts = urlsplit(url)
    if parts.scheme not in ("mqtt", "tcp") or not parts.hostname:
        raise PlatformError(f"HARWOOD0_MQTT_URL must look like mqtt://host:1883, not {url!r}")
    return {
        "hostname": parts.hostname,
        "port": parts.port or 1883,
        "protocol": aiomqtt.ProtocolVersion.V5,
    }


def _is_auth_rejection(exc: aiomqtt.MqttError) -> bool:
    rc = getattr(exc, "rc", None)
    return getattr(rc, "value", rc) in _AUTH_REJECTED


_REPLY_ERRORS = {
    "invalid_code": (
        "the platform rejected HARWOOD0_REGISTRATION_CODE: it is unknown, expired, or "
        "already used. Get a new code with `cli devices register` or on studio's Devices page"
    ),
    "invalid_request": (
        "the platform rejected the registration request; HARWOOD0_DEVICE_NAME must be at "
        "most 100 characters"
    ),
}


async def register(
    client_factory: ClientFactory,
    url: str,
    code: str,
    name: str,
    timeout: float | None = None,
) -> Credentials:
    """Redeems a registration code with devicemgr and returns the device's credentials."""
    timeout = REPLY_TIMEOUT_S if timeout is None else timeout
    client_id = f"{DEVICE_TYPE}-register-{secrets.token_hex(16)}"
    request_topic = f"devices/register/{client_id}"
    request = {"code": code, "type": DEVICE_TYPE, "name": name}
    try:
        async with client_factory(
            # Any non-empty password works; the broker rejects an empty one.
            **_broker(url),
            username="register",
            password="register",
            identifier=client_id,
        ) as client:
            # Subscribe first so the reply can't arrive before anyone is listening.
            await client.subscribe(f"{request_topic}/reply", qos=1)
            await client.publish(request_topic, json.dumps(request), qos=1)
            async with asyncio.timeout(timeout):
                async for message in client.messages:
                    reply = json.loads(message.payload)
                    break
    except TimeoutError as exc:
        raise PlatformError(
            f"no registration reply from the platform within {timeout:g} s; "
            "check that devicemgr is running"
        ) from exc
    except aiomqtt.MqttError as exc:
        raise PlatformError(f"cannot reach the platform broker at {url}: {exc}") from exc
    except ValueError as exc:
        raise PlatformError("the platform sent a malformed registration reply") from exc

    if error := reply.get("error"):
        raise PlatformError(_REPLY_ERRORS.get(error, f"registration failed: {error}"))
    return Credentials(device_id=reply["device_id"], secret=reply["secret"])


class DeviceLink:
    """The device's open MQTT session. Every device publish goes through publish(), which
    records when the device last sent anything, so heartbeats fill only the silences."""

    def __init__(self, client: aiomqtt.Client, device_id: str) -> None:
        self._client = client
        self.device_id = device_id
        # Event loop time of the last publish.
        self.last_publish = float("-inf")

    async def publish(self, subtopic: str, payload: bytes | str = b"", qos: int = 0) -> None:
        """Publishes to devices/{device id}/{subtopic}."""
        await self._client.publish(f"devices/{self.device_id}/{subtopic}", payload, qos=qos)
        self.last_publish = asyncio.get_running_loop().time()


async def heartbeat(link: DeviceLink, interval_s: float) -> None:
    """Publishes a heartbeat now, then whenever the link has been silent for interval_s.

    The platform counts any message as a sign of life (docs/devices.md#connectivity), so
    the heartbeat is an empty, unretained QoS 0 message.
    """
    loop = asyncio.get_running_loop()
    await link.publish("heartbeat")
    while True:
        wait = link.last_publish + interval_s - loop.time()
        if wait > 0:
            await asyncio.sleep(wait)
        else:
            await link.publish("heartbeat")


async def _drain(client: aiomqtt.Client) -> None:
    # No inbound device traffic yet; this waits until the connection drops.
    async for _ in client.messages:
        pass


async def run_device(
    client_factory: ClientFactory,
    url: str,
    credentials: Credentials,
    connected: asyncio.Event | None = None,
    reconnect_s: float = RECONNECT_S,
    heartbeat_s: float = 30.0,
) -> None:
    """Keeps an MQTT session open as the device, reconnecting whenever it drops, and sends
    heartbeats while connected.

    Raises PlatformError if the broker rejects the credentials.
    """
    broker = _broker(url)
    while True:
        try:
            async with client_factory(
                **broker,
                username=credentials.device_id,
                password=credentials.secret,
                identifier=f"{DEVICE_TYPE}-{credentials.device_id}",
            ) as client:
                log.info("connected to the platform as device %s", credentials.device_id)
                if connected:
                    connected.set()
                link = DeviceLink(client, credentials.device_id)
                tasks = {
                    asyncio.create_task(_drain(client)),
                    asyncio.create_task(heartbeat(link, heartbeat_s)),
                }
                try:
                    done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                # Whichever stopped first ended the session; re-raise its connection error.
                for task in done:
                    task.result()
        except aiomqtt.MqttError as exc:
            if _is_auth_rejection(exc):
                raise PlatformError(
                    f"the platform broker rejected the stored credentials for device "
                    f"{credentials.device_id}. Delete device.json and register again with "
                    "HARWOOD0_REGISTRATION_CODE"
                ) from exc
            log.warning("platform connection lost (%s); retrying in %g s", exc, reconnect_s)
        await asyncio.sleep(reconnect_s)


async def start_platform(
    settings: Settings, client_factory: ClientFactory
) -> asyncio.Task[None] | None:
    """Joins the platform, registering first if needed, and returns the connection task.

    Returns None when HARWOOD0_MQTT_URL is unset. Raises PlatformError when the heartbeat
    interval isn't positive, when the robot has no credentials and no code, when
    registration fails, or when the broker rejects the stored credentials.
    """
    if not settings.mqtt_url:
        return None
    if settings.platform_heartbeat_s <= 0:
        raise PlatformError(
            "HARWOOD0_PLATFORM_HEARTBEAT_S must be greater than 0, not "
            f"{settings.platform_heartbeat_s:g}"
        )

    credentials = load_credentials(settings.state_dir)
    if credentials and settings.registration_code:
        log.info(
            "already registered as device %s; ignoring HARWOOD0_REGISTRATION_CODE",
            credentials.device_id,
        )
    elif not credentials:
        if not settings.registration_code:
            raise PlatformError(
                "this robot isn't registered. Set HARWOOD0_REGISTRATION_CODE to a code from "
                "`cli devices register` or studio's Devices page"
            )
        credentials = await register(
            client_factory, settings.mqtt_url, settings.registration_code, settings.device_name
        )
        path = save_credentials(settings.state_dir, credentials)
        log.info("registered as device %s; credentials saved to %s", credentials.device_id, path)

    connected = asyncio.Event()
    task = asyncio.create_task(
        run_device(
            client_factory,
            settings.mqtt_url,
            credentials,
            connected,
            heartbeat_s=settings.platform_heartbeat_s,
        )
    )
    waiter = asyncio.create_task(connected.wait())
    # Wait for the first connection so rejected credentials fail startup. If the broker is
    # just unreachable, carry on and keep retrying in the background.
    await asyncio.wait({task, waiter}, timeout=REPLY_TIMEOUT_S, return_when=asyncio.FIRST_COMPLETED)
    waiter.cancel()
    if task.done():
        task.result()
    task.add_done_callback(_log_failure)
    return task


def _log_failure(task: asyncio.Task[None]) -> None:
    if not task.cancelled() and (exc := task.exception()):
        log.error("platform connection stopped: %s", exc)


async def stop_platform(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError, PlatformError):
        await task

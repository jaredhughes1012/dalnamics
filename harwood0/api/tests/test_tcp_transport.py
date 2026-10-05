"""Exercises TcpTransport against a local server that mimics the firmware."""

import asyncio
import json

import pytest

from harwood0_api.transport import RobotError, RobotUnavailable, TcpTransport


async def fake_firmware(reader, writer):
    async for line in reader:
        request = json.loads(line)
        if request["cmd"] == "ping":
            response = {"id": request["id"], "ok": True, "result": {"uptime_ms": 42}}
        elif request["cmd"] == "drop":
            break
        else:
            response = {"id": request["id"], "ok": False, "error": "unknown_command"}
        writer.write(json.dumps(response).encode() + b"\n")
        await writer.drain()
    writer.close()


def run(coro):
    return asyncio.run(coro)


async def with_transport(fn):
    server = await asyncio.start_server(fake_firmware, "127.0.0.1", 0)
    async with server:
        port = server.sockets[0].getsockname()[1]
        transport = TcpTransport(f"tcp://127.0.0.1:{port}", timeout_s=1.0)
        try:
            return await fn(transport)
        finally:
            await transport.close()


def test_request_returns_result():
    result = run(with_transport(lambda t: t.request("ping")))
    assert result == {"uptime_ms": 42}


def test_concurrent_requests_match_by_id():
    async def many(t):
        return await asyncio.gather(*(t.request("ping") for _ in range(10)))

    assert run(with_transport(many)) == [{"uptime_ms": 42}] * 10


def test_error_response_raises():
    with pytest.raises(RobotError) as exc:
        run(with_transport(lambda t: t.request("fly")))
    assert exc.value.code == "unknown_command"


def test_reconnects_after_server_drops_connection():
    async def drop_then_ping(t):
        # "drop" makes the fake firmware hang up, failing the in-flight request.
        with pytest.raises(RobotUnavailable):
            await t.request("drop")
        return await t.request("ping")

    assert run(with_transport(drop_then_ping)) == {"uptime_ms": 42}


class CountingFirmware:
    """Answers every command like a ping, counting connections and pings."""

    def __init__(self):
        self.connections = 0
        self.pings = 0
        self.reject_pings = False

    async def __call__(self, reader, writer):
        self.connections += 1
        async for line in reader:
            request = json.loads(line)
            if request["cmd"] == "drop":
                break
            self.pings += request["cmd"] == "ping"
            if request["cmd"] == "ping" and self.reject_pings:
                response = {"id": request["id"], "ok": False, "error": "unknown_command"}
            else:
                response = {"id": request["id"], "ok": True, "result": {"uptime_ms": 42}}
            writer.write(json.dumps(response).encode() + b"\n")
            await writer.drain()
        writer.close()


async def with_counting_firmware(fn):
    firmware = CountingFirmware()
    server = await asyncio.start_server(firmware, "127.0.0.1", 0)
    async with server:
        port = server.sockets[0].getsockname()[1]
        transport = TcpTransport(f"tcp://127.0.0.1:{port}", timeout_s=1.0, heartbeat_s=0.02)
        try:
            await fn(transport, firmware)
        finally:
            await transport.close()
    return firmware


def test_heartbeat_pings_while_connected():
    async def idle(t, firmware):
        await t.request("state")
        await asyncio.sleep(0.2)
        assert firmware.pings >= 5

    run(with_counting_firmware(idle))


def test_heartbeat_stops_on_close():
    async def close_then_wait(t, firmware):
        await t.request("state")
        await asyncio.sleep(0.05)
        await t.close()
        pings = firmware.pings
        await asyncio.sleep(0.1)
        assert firmware.pings == pings

    run(with_counting_firmware(close_then_wait))


def test_heartbeat_stops_on_disconnect_without_reconnecting():
    async def drop_then_wait(t, firmware):
        with pytest.raises(RobotUnavailable):
            await t.request("drop")
        await asyncio.sleep(0.1)
        assert firmware.connections == 1
        assert firmware.pings == 0

    run(with_counting_firmware(drop_then_wait))


def test_heartbeat_failure_only_logs(caplog):
    async def rejected(t, firmware):
        await t.request("state")
        firmware.reject_pings = True
        await asyncio.sleep(0.1)
        assert not t._heartbeat.done()
        assert await t.request("state") == {"uptime_ms": 42}

    firmware = run(with_counting_firmware(rejected))
    assert firmware.pings >= 2
    assert "heartbeat failed: unknown_command" in caplog.text

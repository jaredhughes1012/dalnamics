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

import asyncio
import json
import socket

from harwood0_api.check import check
from harwood0_api.robot import Robot
from harwood0_api.transport import SimTransport, TcpTransport


def run_check(transport, pings=3):
    lines = []

    async def go():
        try:
            return await check(Robot(transport), pings, lines.append)
        finally:
            await transport.close()

    return asyncio.run(go()), lines


def test_passes_against_simulator():
    ok, lines = run_check(SimTransport())
    assert ok
    assert [line.split()[0] for line in lines] == ["connect", "info", "state", "ping"]
    assert "harwood0-sim firmware sim, protocol 1" in lines[1]
    assert "drive stopped, arm limp, track unhomed" in lines[2]


def test_fails_when_robot_unreachable():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # closed again before the check connects
    ok, lines = run_check(TcpTransport(f"tcp://127.0.0.1:{port}", timeout_s=0.5, heartbeat_s=0))
    assert not ok
    assert lines == [lines[0]]
    assert "FAILED" in lines[0] and "after 0 step(s)" in lines[0]


def test_fails_on_malformed_info():
    async def firmware(reader, writer):
        async for line in reader:
            request = json.loads(line)
            result = {"uptime_ms": 1} if request["cmd"] == "ping" else {"name": "harwood0"}
            response = {"id": request["id"], "ok": True, "result": result}
            writer.write(json.dumps(response).encode() + b"\n")
            await writer.drain()
        writer.close()

    async def go():
        server = await asyncio.start_server(firmware, "127.0.0.1", 0)
        async with server:
            port = server.sockets[0].getsockname()[1]
            transport = TcpTransport(f"tcp://127.0.0.1:{port}", timeout_s=1.0, heartbeat_s=0)
            lines = []
            try:
                return await check(Robot(transport), 1, lines.append), lines
            finally:
                await transport.close()

    ok, lines = asyncio.run(go())
    assert not ok
    assert lines[0].split()[0] == "connect"
    assert "after 1 step(s): ValidationError" in lines[1]

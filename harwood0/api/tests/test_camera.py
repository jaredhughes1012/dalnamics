import asyncio

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from harwood0_api import app as app_module
from harwood0_api.app import create_app
from harwood0_api.camera import Camera, Frame, mjpeg_part, parse_mjpeg
from harwood0_api.config import SIM, Settings

JPEGS = [b"\xff\xd8one\xff\xd9", b"\xff\xd8two\r\n\r\n\xff\xd9", b"\xff\xd8three\xff\xd9"]
STREAM_TYPE = "multipart/x-mixed-replace;boundary=frame"


async def chunked(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i : i + size]


async def collect(parts):
    return [part async for part in parts]


@pytest.mark.parametrize("size", [1, 7, 1 << 16])
def test_parse_mjpeg_splits_parts_across_any_chunking(size):
    body = b"".join(mjpeg_part(jpeg) for jpeg in JPEGS)
    assert asyncio.run(collect(parse_mjpeg(chunked(body, size)))) == JPEGS


def test_parse_mjpeg_needs_content_length():
    body = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8\xff\xd9\r\n"
    with pytest.raises(ValueError, match="Content-Length"):
        asyncio.run(collect(parse_mjpeg(chunked(body, 64))))


def test_parse_mjpeg_rejects_a_stream_with_no_headers():
    async def junk():
        while True:
            yield b"x" * 65536

    with pytest.raises(ValueError, match="no MJPEG part header"):
        asyncio.run(collect(parse_mjpeg(junk())))


class FakeCamera:
    """An HTTP camera that serves `JPEGS` once per connection, then hangs up."""

    def __init__(self, status: int = 200):
        self.connections = 0
        self.status = status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.connections += 1
        if self.status != 200:
            return httpx.Response(self.status)

        async def body():
            for jpeg in JPEGS:
                yield mjpeg_part(jpeg)
                await asyncio.sleep(0.01)

        return httpx.Response(200, headers={"content-type": STREAM_TYPE}, content=body())


def make_camera(fake: FakeCamera) -> Camera:
    client = httpx.AsyncClient(transport=httpx.MockTransport(fake))
    return Camera("nose", "http://cam/stream", client, timeout_s=1.0, retry_s=0.01)


async def with_camera(fake: FakeCamera, fn):
    camera = make_camera(fake)
    try:
        return await fn(camera)
    finally:
        await camera.close()


def test_frames_arrive_in_order_and_reconnect_after_stream_ends():
    fake = FakeCamera()

    async def read(camera):
        frames = []
        async for frame in camera.frames():
            frames.append(frame)
            if len(frames) == 2 * len(JPEGS):
                return frames

    frames = asyncio.run(with_camera(fake, read))
    assert [f.jpeg for f in frames] == JPEGS * 2
    assert [f.seq for f in frames] == list(range(1, 7))
    assert fake.connections == 2


def test_frame_returns_latest_and_status_reports_stream():
    async def read(camera):
        first = await camera.frame()
        status = camera.status()
        return first, status

    first, status = asyncio.run(with_camera(FakeCamera(), read))
    assert first.jpeg == JPEGS[0]
    assert status.connected and status.frames >= 1 and status.error is None


def test_status_reports_why_it_cannot_connect():
    async def read(camera):
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(camera.frame(), 0.1)
        return camera.status()

    status = asyncio.run(with_camera(FakeCamera(status=500), read))
    assert not status.connected
    assert status.frames == 0 and status.frame_age_s is None
    assert "500" in status.error


@pytest.fixture
def client():
    with TestClient(create_app(Settings(robot_url=SIM))) as client:
        yield client


def test_lists_configured_cameras(client):
    names = [c["name"] for c in client.get("/cameras").json()]
    assert names == ["nose", "arm"]
    assert client.get("/cameras/tail").status_code == 404


def test_empty_url_leaves_camera_out():
    settings = Settings(robot_url=SIM, arm_camera_url="")
    with TestClient(create_app(settings)) as client:
        assert [c["name"] for c in client.get("/cameras").json()] == ["nose"]


def test_frame_route_serves_jpeg(client):
    client.app.state.cameras["nose"] = make_camera(FakeCamera())
    response = client.get("/cameras/nose/frame")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == JPEGS[0]


def test_frame_route_fails_when_camera_unreachable(client, monkeypatch):
    monkeypatch.setattr(app_module, "FRAME_TIMEOUT_S", 0.1)
    client.app.state.cameras["nose"] = make_camera(FakeCamera(status=503))
    response = client.get("/cameras/nose/frame")
    assert response.status_code == 503
    assert response.json()["error"] == "camera_unavailable"


class FiniteCamera:
    """Stands in for a Camera whose stream ends, so the response can be read to the end."""

    async def frames(self):
        for seq, jpeg in enumerate(JPEGS, 1):
            yield Frame(jpeg, seq, 0.0)

    async def close(self):
        pass


def test_stream_route_serves_frames_as_mjpeg(client):
    client.app.state.cameras["nose"] = FiniteCamera()
    response = client.get("/cameras/nose/stream")
    assert response.headers["content-type"] == "multipart/x-mixed-replace; boundary=frame"
    assert asyncio.run(collect(parse_mjpeg(chunked(response.content, 64)))) == JPEGS


def test_viewer_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "/cameras/${name}/stream" in response.text

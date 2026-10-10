"""Reads the robot's cameras (ESP32-CAMs streaming MJPEG over HTTP; see camera/).

An ESP32-CAM serves one stream at a time, so each Camera holds a single connection to its
camera and shares the latest frame with every reader. The connection opens on first use and
reconnects if it drops.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx2 as httpx
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Bigger than any frame the camera sends (VGA JPEGs run 20-60 kB), so a stream that is not
# MJPEG fails fast instead of buffering forever.
MAX_PART_BYTES = 1 << 20


@dataclass(frozen=True)
class Frame:
    jpeg: bytes
    seq: int  # counts up from 1 for each frame this Camera receives
    time: float  # time.monotonic() when it arrived


class CameraStatus(BaseModel):
    name: str
    url: str
    connected: bool
    frames: int = Field(description="Frames received since the API started.")
    fps: float = Field(description="Recent frame rate; 0 when not connected.")
    frame_age_s: float | None = Field(description="Age of the latest frame; null before one.")
    error: str | None = Field(description="Why the last connection attempt failed, if it did.")


def _content_length(headers: bytes) -> int:
    for line in headers.split(b"\r\n"):
        name, _, value = line.partition(b":")
        if name.strip().lower() == b"content-length":
            return int(value)
    raise ValueError("MJPEG part has no Content-Length")


async def parse_mjpeg(chunks: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    """Split a multipart/x-mixed-replace body into its parts' payloads. Each part must carry a
    Content-Length header, as the harwood0 camera firmware sends."""
    buf = bytearray()
    async for chunk in chunks:
        buf += chunk
        while (end := buf.find(b"\r\n\r\n")) >= 0:
            length = _content_length(bytes(buf[:end]))
            if length > MAX_PART_BYTES:
                raise ValueError(f"MJPEG part of {length} bytes is too big")
            start = end + 4
            if len(buf) < start + length:
                break
            yield bytes(buf[start : start + length])
            del buf[: start + length]
        if len(buf) > MAX_PART_BYTES:
            raise ValueError("no MJPEG part header found")


def mjpeg_part(jpeg: bytes, boundary: str = "frame") -> bytes:
    """One part of a multipart/x-mixed-replace JPEG stream, in the camera firmware's format."""
    header = f"--{boundary}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n"
    return header.encode() + jpeg + b"\r\n"


class Camera:
    def __init__(
        self,
        name: str,
        url: str,
        client: httpx.AsyncClient,
        timeout_s: float = 5.0,
        retry_s: float = 2.0,
    ):
        self.name = name
        self.url = url
        self._client = client
        self._timeout_s = timeout_s
        self._retry_s = retry_s
        self._frame: Frame | None = None
        self._new_frame = asyncio.Condition()
        self._reader: asyncio.Task[None] | None = None
        self._connected = False
        self._error: str | None = None
        self._last_arrival: float | None = None  # None until a frame on this connection
        self._interval_s = 0.0  # smoothed time between frames

    def _start(self) -> None:
        if self._reader is None:
            self._reader = asyncio.create_task(self._read())

    async def _read(self) -> None:
        timeout = httpx.Timeout(self._timeout_s)
        while True:
            try:
                async with self._client.stream("GET", self.url, timeout=timeout) as response:
                    response.raise_for_status()
                    self._connected, self._error = True, None
                    self._last_arrival, self._interval_s = None, 0.0
                    log.info("camera %s connected", self.name)
                    async for jpeg in parse_mjpeg(response.aiter_bytes()):
                        await self._publish(jpeg)
                    raise ValueError("stream ended")
            except (httpx.HTTPError, ValueError) as e:
                self._error = str(e) or type(e).__name__
                log.warning(
                    "camera %s: %s; retrying in %s s", self.name, self._error, self._retry_s
                )
            finally:
                self._connected = False
            await asyncio.sleep(self._retry_s)

    async def _publish(self, jpeg: bytes) -> None:
        now = time.monotonic()
        if self._last_arrival is not None:
            dt = now - self._last_arrival
            # Smoothed over about ten frames.
            self._interval_s = (
                dt if not self._interval_s else self._interval_s + 0.1 * (dt - self._interval_s)
            )
        self._last_arrival = now
        async with self._new_frame:
            seq = self._frame.seq + 1 if self._frame else 1
            self._frame = Frame(jpeg, seq, now)
            self._new_frame.notify_all()

    async def _next(self, after: int) -> Frame:
        self._start()
        async with self._new_frame:
            await self._new_frame.wait_for(lambda: self._frame and self._frame.seq > after)
            return self._frame

    async def frame(self, max_age_s: float = 1.0) -> Frame:
        """The latest frame if it is fresher than `max_age_s`, else the next one to arrive."""
        latest = self._frame
        if latest is not None and time.monotonic() - latest.time <= max_age_s:
            return latest
        return await self._next(latest.seq if latest else 0)

    async def frames(self) -> AsyncIterator[Frame]:
        """Every new frame as it arrives. A slow consumer skips frames rather than lagging."""
        seq = 0
        while True:
            frame = await self._next(seq)
            seq = frame.seq
            yield frame

    def status(self) -> CameraStatus:
        latest = self._frame
        return CameraStatus(
            name=self.name,
            url=self.url,
            connected=self._connected,
            frames=latest.seq if latest else 0,
            fps=round(1 / self._interval_s, 1) if self._connected and self._interval_s else 0.0,
            frame_age_s=round(time.monotonic() - latest.time, 3) if latest else None,
            error=self._error,
        )

    async def close(self) -> None:
        if self._reader is not None:
            self._reader.cancel()
            await asyncio.gather(self._reader, return_exceptions=True)
            self._reader = None

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.resources import files
from typing import Annotated

import aiomqtt
import httpx2 as httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

from harwood0_api.camera import Camera, CameraStatus, mjpeg_part
from harwood0_api.config import Settings
from harwood0_api.platform import ClientFactory, PlatformError, start_platform, stop_platform
from harwood0_api.robot import (
    ArmTargets,
    Drive,
    Ping,
    Robot,
    RobotInfo,
    RobotState,
    TrackTarget,
)
from harwood0_api.transport import RobotError, RobotUnavailable, make_transport

log = logging.getLogger(__name__)

# How long /cameras/{name}/frame waits for a frame before giving up.
FRAME_TIMEOUT_S = 5.0


def create_app(
    settings: Settings | None = None, mqtt_client_factory: ClientFactory = aiomqtt.Client
) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            platform = await start_platform(settings, mqtt_client_factory)
        except PlatformError as exc:
            log.error("cannot join the dalnamics platform: %s", exc)
            raise
        transport = make_transport(settings)
        app.state.robot = Robot(transport)
        async with httpx.AsyncClient() as client:
            app.state.cameras = {
                name: Camera(name, url, client) for name, url in settings.camera_urls.items()
            }
            yield
            await asyncio.gather(*(camera.close() for camera in app.state.cameras.values()))
        await transport.close()
        await stop_platform(platform)

    app = FastAPI(title="harwood0", lifespan=lifespan)

    @app.exception_handler(RobotError)
    async def robot_error(_: Request, exc: RobotError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": exc.code})

    @app.exception_handler(RobotUnavailable)
    async def robot_unavailable(_: Request, exc: RobotUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"error": "robot_unavailable", "detail": str(exc)}
        )

    def get_robot(request: Request) -> Robot:
        return request.app.state.robot

    RobotDep = Annotated[Robot, Depends(get_robot)]

    @app.get("/robot/info", summary=Robot.info.__doc__)
    async def info(robot: RobotDep) -> RobotInfo:
        return await robot.info()

    @app.post("/robot/ping", summary=Robot.ping.__doc__)
    async def ping(robot: RobotDep) -> Ping:
        return await robot.ping()

    @app.post("/robot/stop", status_code=204, summary=Robot.stop.__doc__)
    async def stop(robot: RobotDep) -> None:
        await robot.stop()

    @app.post("/robot/drive", status_code=204, summary=Robot.drive.__doc__)
    async def drive(body: Drive, robot: RobotDep) -> None:
        await robot.drive(**body.model_dump())

    @app.post("/robot/arm", status_code=204, summary=Robot.move_arm.__doc__)
    async def arm(body: ArmTargets, robot: RobotDep) -> None:
        await robot.move_arm(**body.model_dump())

    @app.post("/robot/track", status_code=204, summary=Robot.move_track.__doc__)
    async def track(body: TrackTarget, robot: RobotDep) -> None:
        await robot.move_track(body.x)

    @app.post("/robot/track/home", status_code=204, summary=Robot.home_track.__doc__)
    async def home_track(robot: RobotDep) -> None:
        await robot.home_track()

    @app.get("/robot/state", summary=Robot.state.__doc__)
    async def state(robot: RobotDep) -> RobotState:
        return await robot.state()

    def get_camera(name: str, request: Request) -> Camera:
        camera = request.app.state.cameras.get(name)
        if camera is None:
            raise HTTPException(status_code=404, detail=f"no camera named {name!r}")
        return camera

    CameraDep = Annotated[Camera, Depends(get_camera)]

    @app.get("/cameras", summary="List the cameras and whether each is streaming.")
    async def cameras(request: Request) -> list[CameraStatus]:
        return [camera.status() for camera in request.app.state.cameras.values()]

    @app.get("/cameras/{name}", summary="Report one camera's connection and frame rate.")
    async def camera_status(camera: CameraDep) -> CameraStatus:
        return camera.status()

    @app.get(
        "/cameras/{name}/frame",
        summary="The camera's latest frame as a JPEG.",
        response_class=Response,
        responses={200: {"content": {"image/jpeg": {}}}},
    )
    async def camera_frame(camera: CameraDep) -> Response:
        try:
            frame = await asyncio.wait_for(camera.frame(), FRAME_TIMEOUT_S)
        except TimeoutError:
            status = camera.status()
            return JSONResponse(
                status_code=503, content={"error": "camera_unavailable", "detail": status.error}
            )
        return Response(frame.jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get(
        "/cameras/{name}/stream",
        summary="The camera's video as MJPEG (multipart/x-mixed-replace), for an <img> tag.",
        response_class=StreamingResponse,
    )
    async def camera_stream(camera: CameraDep) -> StreamingResponse:
        async def parts() -> AsyncIterator[bytes]:
            async for frame in camera.frames():
                yield mjpeg_part(frame.jpeg)

        return StreamingResponse(
            parts(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store"},
        )

    viewer = files("harwood0_api").joinpath("viewer.html").read_text()

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index() -> str:
        return viewer

    return app

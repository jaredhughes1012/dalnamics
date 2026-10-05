from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from harwood0_api.config import Settings
from harwood0_api.robot import Ping, Robot, RobotInfo
from harwood0_api.transport import RobotError, RobotUnavailable, make_transport


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        transport = make_transport(settings)
        app.state.robot = Robot(transport)
        yield
        await transport.close()

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

    return app

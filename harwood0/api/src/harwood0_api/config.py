import os
from dataclasses import dataclass

SIM = "sim"


@dataclass(frozen=True)
class Settings:
    # TCP URL (tcp://host:port) of the robot firmware, or "sim" for the in-process simulator.
    robot_url: str = "tcp://harwood0.local:7777"
    request_timeout_s: float = 2.0
    # How often to ping the firmware while connected, to keep its 1 s command timeout from
    # stopping motions that outlast a request. 0 disables it.
    heartbeat_s: float = 0.3
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            robot_url=os.environ.get("HARWOOD0_ROBOT_URL", defaults.robot_url),
            request_timeout_s=float(
                os.environ.get("HARWOOD0_REQUEST_TIMEOUT_S", defaults.request_timeout_s)
            ),
            heartbeat_s=float(os.environ.get("HARWOOD0_HEARTBEAT_S", defaults.heartbeat_s)),
            host=os.environ.get("HARWOOD0_HOST", defaults.host),
            port=int(os.environ.get("HARWOOD0_PORT", defaults.port)),
        )

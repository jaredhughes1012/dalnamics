import os
import socket
from dataclasses import dataclass, field
from pathlib import Path

SIM = "sim"


@dataclass(frozen=True)
class Settings:
    # TCP URL (tcp://host:port) of the robot firmware, or "sim" for the in-process simulator.
    robot_url: str = "tcp://harwood0.local:7777"
    request_timeout_s: float = 2.0
    # How often to ping the firmware while connected, to keep its 1 s command timeout from
    # stopping motions that outlast a request. 0 disables it.
    heartbeat_s: float = 0.3
    # MJPEG stream URLs of the cameras (camera/ firmware); empty leaves that camera out.
    nose_camera_url: str = "http://harwood0-nose.local:81/stream"
    arm_camera_url: str = "http://harwood0-arm.local:81/stream"
    host: str = "127.0.0.1"
    # Off the common dev ports (8000, 8080, ...) so the API runs beside the platform stack.
    # Set HARWOOD0_PORT to run several APIs at once.
    port: int = 47800
    # MQTT broker of the dalnamics platform (mqtt://host:port). Empty disables the platform
    # connection, so the API runs standalone.
    mqtt_url: str = ""
    # One-time code from `cli devices register` or studio's Devices page. Used only until the
    # robot has stored credentials.
    registration_code: str = ""
    device_name: str = field(default_factory=socket.gethostname)
    # How long the platform connection may go without publishing before it sends a heartbeat,
    # so the platform keeps showing the robot as online. Unrelated to heartbeat_s.
    platform_heartbeat_s: float = 30.0
    # Where the robot keeps its platform credentials (device.json).
    state_dir: Path = field(default_factory=lambda: Path.home() / ".local/state/harwood0")

    @property
    def camera_urls(self) -> dict[str, str]:
        urls = {"nose": self.nose_camera_url, "arm": self.arm_camera_url}
        return {name: url for name, url in urls.items() if url}

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            robot_url=os.environ.get("HARWOOD0_ROBOT_URL", defaults.robot_url),
            request_timeout_s=float(
                os.environ.get("HARWOOD0_REQUEST_TIMEOUT_S", defaults.request_timeout_s)
            ),
            heartbeat_s=float(os.environ.get("HARWOOD0_HEARTBEAT_S", defaults.heartbeat_s)),
            nose_camera_url=os.environ.get("HARWOOD0_NOSE_CAMERA_URL", defaults.nose_camera_url),
            arm_camera_url=os.environ.get("HARWOOD0_ARM_CAMERA_URL", defaults.arm_camera_url),
            host=os.environ.get("HARWOOD0_HOST", defaults.host),
            port=int(os.environ.get("HARWOOD0_PORT", defaults.port)),
            mqtt_url=os.environ.get("HARWOOD0_MQTT_URL", defaults.mqtt_url),
            registration_code=os.environ.get(
                "HARWOOD0_REGISTRATION_CODE", defaults.registration_code
            ),
            device_name=os.environ.get("HARWOOD0_DEVICE_NAME") or defaults.device_name,
            platform_heartbeat_s=float(
                os.environ.get("HARWOOD0_PLATFORM_HEARTBEAT_S", defaults.platform_heartbeat_s)
            ),
            state_dir=Path(os.environ["HARWOOD0_STATE_DIR"]).expanduser()
            if os.environ.get("HARWOOD0_STATE_DIR")
            else defaults.state_dir,
        )

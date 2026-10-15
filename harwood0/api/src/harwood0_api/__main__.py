import logging

import uvicorn

from harwood0_api.app import create_app
from harwood0_api.config import Settings


def main() -> None:
    settings = Settings.from_env()
    # Shows the app's own logs (such as platform registration) beside uvicorn's.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
    # Camera streams never end on their own, so don't wait long for them on shutdown.
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        timeout_graceful_shutdown=1,
    )


if __name__ == "__main__":
    main()

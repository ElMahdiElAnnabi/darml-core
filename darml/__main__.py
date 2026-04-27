"""`python -m darml` — launches the Pro web server if available, else helpful message."""

from __future__ import annotations

import sys

from darml.config import get_settings
from darml.container import get_container
from darml.plugins import hooks


def main() -> None:
    settings = get_settings()
    container = get_container()

    if hooks.server_factory is None:
        print(
            "The Darml web dashboard requires Darml Pro.\n\n"
            "  → Start a free 14-day trial:  https://darml.dev/trial\n"
            "  → The CLI works fully without Pro:\n"
            "    darml build model.tflite --target esp32-s3\n\n"
            "Learn more: https://darml.dev/pricing",
            file=sys.stderr,
        )
        sys.exit(2)

    import uvicorn  # imported lazily so Core users don't need it

    app = hooks.server_factory(container)
    uvicorn.run(
        app, host=settings.host, port=settings.port,
        log_config=None,
    )


if __name__ == "__main__":
    main()

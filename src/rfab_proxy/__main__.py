"""Serve rfab-proxy with uvicorn: ``python -m rfab_proxy`` or ``rfab-proxy``."""

import uvicorn

from rfab_proxy.config import Settings


def main():
    settings = Settings.from_env()
    uvicorn.run(
        "rfab_proxy.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        # Logging is configured by the app factory, not uvicorn.
        log_config=None,
    )


if __name__ == "__main__":  # pragma: no cover
    main()

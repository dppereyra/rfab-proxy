"""Runtime configuration, read from environment variables."""

import logging
import os
from dataclasses import dataclass

_LOG_LEVELS = frozenset(logging.getLevelNamesMapping())


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    sentry_dsn: str | None = None
    sentry_environment: str = "production"
    sentry_sample_rate: float = 1.0

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        return cls(
            host=environ.get("RFAB_HOST", cls.host),
            port=_port(environ.get("RFAB_PORT", str(cls.port))),
            log_level=_log_level(environ.get("RFAB_LOG_LEVEL", cls.log_level)),
            sentry_dsn=environ.get("SENTRY_DSN") or None,
            sentry_environment=environ.get("SENTRY_ENVIRONMENT", cls.sentry_environment),
            sentry_sample_rate=_rate(environ, "SENTRY_SAMPLE_RATE", cls.sentry_sample_rate),
        )


def _port(value):
    try:
        port = int(value)
    except ValueError:
        port = 0
    if not 0 < port < 65536:
        raise ValueError(f"RFAB_PORT must be a port number between 1 and 65535, got {value!r}")
    return port


def _log_level(value):
    level = value.upper()
    if level not in _LOG_LEVELS:
        raise ValueError(f"RFAB_LOG_LEVEL must be a logging level name, got {value!r}")
    return level


def _rate(environ, name, default):
    value = environ.get(name, str(default))
    try:
        rate = float(value)
    except ValueError:
        rate = -1.0
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"{name} must be a number between 0 and 1, got {value!r}")
    return rate

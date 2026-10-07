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

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        return cls(
            host=environ.get("RFAB_HOST", cls.host),
            port=_port(environ.get("RFAB_PORT", str(cls.port))),
            log_level=_log_level(environ.get("RFAB_LOG_LEVEL", cls.log_level)),
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

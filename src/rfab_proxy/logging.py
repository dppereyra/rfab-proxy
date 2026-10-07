"""Structured (JSON lines) logging through the standard library."""

import json
import logging
from datetime import UTC, datetime

from rfab_proxy.redaction import redact_url

# httpx logs every request URL at INFO, query strings and userinfo included;
# in a proxy those can carry upstream credentials.
_QUIET_LOGGERS = ("httpx", "httpcore")


class AccessLogRedactor(logging.Filter):
    """Redact query values in uvicorn access logs (args: client, method, path, ...)."""

    def filter(self, record):
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            record.args = (*args[:2], redact_url(args[2]), *args[3:])
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level):
    """Install a single JSON handler on the root logger.

    Repeated calls replace the handler installed earlier; handlers added by
    anything else (a test harness, an embedding server) are left alone.
    """
    root = logging.getLogger()
    for existing in [h for h in root.handlers if isinstance(h.formatter, JsonFormatter)]:
        root.removeHandler(existing)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    access = logging.getLogger("uvicorn.access")
    for existing in [f for f in access.filters if isinstance(f, AccessLogRedactor)]:
        access.removeFilter(existing)
    access.addFilter(AccessLogRedactor())

"""Sentry error monitoring.

Sentry only receives errors: OpenTelemetry owns tracing, so Sentry tracing
stays off and traces are never sent twice. Sentry's Falcon integration does
not support ASGI apps; errors reach Sentry through its logging integration,
which turns the catch-all error handler's ``log.exception`` into an event.
"""

import sentry_sdk

from rfab_proxy import __version__

_FILTERED = "[Filtered]"
_SENSITIVE_HEADERS = frozenset(
    {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key"}
)


def init_sentry(settings):
    """Initialise Sentry; a no-op returning False when no DSN is configured."""
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=f"rfab-proxy@{__version__}",
        sample_rate=settings.sentry_sample_rate,
        traces_sample_rate=None,
        send_default_pii=False,
        # Frame locals of a proxy can hold upstream credentials.
        include_local_variables=False,
        before_send=scrub_event,
    )
    return True


def scrub_event(event, _hint):
    """Strip credentials from an event before it leaves the process."""
    request = event.get("request")
    if request:
        request.pop("cookies", None)
        headers = request.get("headers") or {}
        for name in headers:
            if name.lower() in _SENSITIVE_HEADERS:
                headers[name] = _FILTERED
    return event

"""ASGI application factory."""

import logging

import falcon
import falcon.asgi

from rfab_proxy.config import Settings
from rfab_proxy.health import Liveness, Readiness
from rfab_proxy.logging import configure_logging
from rfab_proxy.monitoring import init_sentry
from rfab_proxy.openapi import api
from rfab_proxy.telemetry import instrument, telemetry_from_env

log = logging.getLogger(__name__)


def create_app(settings=None, readiness_checks=()):
    """Build the app; tests and the server both go through here."""
    settings = Settings.from_env() if settings is None else settings
    configure_logging(settings.log_level)
    init_sentry(settings)

    app = falcon.asgi.App()
    app.add_error_handler(Exception, _handle_unexpected_error)
    app.add_route("/healthz", Liveness())
    app.add_route("/readyz", Readiness(readiness_checks))
    api.register(app)  # serves the generated document under /docs/
    return app


def create_asgi_app(settings=None, environ=None):
    """Server entry point: the app, wrapped in OpenTelemetry when configured."""
    return instrument(create_app(settings), telemetry_from_env(environ))


async def _handle_unexpected_error(req, _resp, _ex, _params):
    # Falcon routes HTTPError to its own, more specific handler, so this only
    # sees unexpected exceptions: log the traceback, answer with a bare 500 and
    # keep internal details away from the client.
    log.exception("Unhandled error on %s %s", req.method, req.path)
    raise falcon.HTTPInternalServerError()

"""Liveness and readiness probes."""

import falcon
from spectree import Response

from rfab_proxy.openapi import api
from rfab_proxy.schemas import ErrorBody, Liveness as LivenessBody, Readiness as ReadinessBody


class Liveness:
    @api.validate(resp=Response(HTTP_200=LivenessBody), tags=["health"])
    async def on_get(self, req, resp):
        """Liveness probe

        Answers as long as the process is serving requests.
        """
        resp.media = {"status": "alive"}


class Readiness:
    def __init__(self, checks):
        self._checks = tuple(checks)

    @api.validate(resp=Response(HTTP_200=ReadinessBody, HTTP_503=ErrorBody), tags=["health"])
    async def on_get(self, req, resp):
        """Readiness probe

        Answers 200 once every readiness check passes, and 503 otherwise.
        """
        if not all(check() for check in self._checks):
            raise falcon.HTTPServiceUnavailable()
        resp.media = {"status": "ready"}

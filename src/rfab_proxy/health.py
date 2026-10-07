"""Liveness and readiness probes."""

import falcon


class Liveness:
    async def on_get(self, req, resp):
        resp.media = {"status": "alive"}


class Readiness:
    def __init__(self, checks):
        self._checks = tuple(checks)

    async def on_get(self, req, resp):
        if not all(check() for check in self._checks):
            raise falcon.HTTPServiceUnavailable()
        resp.media = {"status": "ready"}

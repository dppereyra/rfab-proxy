"""The OpenAPI document (spec-first: openapi.yaml is the source of truth)."""

import copy
import functools
from importlib.resources import files

import yaml

from rfab_proxy import __version__


@functools.cache
def load_spec():
    return yaml.safe_load(files("rfab_proxy").joinpath("openapi.yaml").read_text("utf-8"))


class OpenAPISpec:
    def __init__(self):
        self._spec = copy.deepcopy(load_spec())
        self._spec["info"]["version"] = __version__

    async def on_get(self, req, resp):
        resp.media = self._spec

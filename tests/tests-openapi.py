import json

import falcon.inspect
import falcon.testing
import pytest
from openapi_spec_validator import validate

import rfab_proxy
from rfab_proxy.app import create_app
from rfab_proxy.config import Settings
from rfab_proxy.openapi import DOCS_PATH, api, main

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


@pytest.fixture
def app():
    return create_app(Settings.from_env({}))


@pytest.fixture
def client(app):
    return falcon.testing.TestClient(app)


def test_generated_spec_is_a_valid_openapi_3_1_document(app):
    validate(api.spec)
    assert api.spec["openapi"].startswith("3.1.")


def test_spec_is_served_with_the_package_version_and_license(client):
    result = client.simulate_get(f"/{DOCS_PATH}/openapi.json")

    assert result.status_code == 200
    info = result.json["info"]
    assert info["title"] == "rfab-proxy"
    assert info["version"] == rfab_proxy.__version__
    assert info["license"]["name"] == "AGPL-3.0-or-later"


def test_every_exposed_route_is_documented(app):
    # Generated from the routes, so nothing can drift; this catches a route
    # added without the @api.validate decorator, which strict mode would omit.
    routes = {
        (route.path, method.method.lower())
        for route in falcon.inspect.inspect_routes(app)
        if not route.path.startswith(f"/{DOCS_PATH}/")
        for method in route.methods
        if not method.internal
    }
    documented = {
        (path, method)
        for path, item in api.spec["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }

    assert routes == documented


def test_operations_take_their_summary_from_the_docstring(app):
    operation = api.spec["paths"]["/healthz"]["get"]

    assert operation["summary"] == "Liveness probe"
    assert operation["tags"] == ["health"]


@pytest.mark.parametrize("page", ["swagger", "redoc", "scalar"])
def test_interactive_documentation_pages_are_served(client, page):
    result = client.simulate_get(f"/{DOCS_PATH}/{page}")

    assert result.status_code == 200
    assert result.headers["content-type"].startswith("text/html")


def test_export_writes_the_generated_spec_to_a_file(tmp_path):
    output = tmp_path / "openapi.json"

    main(["--output", str(output)])

    exported = json.loads(output.read_text())
    validate(exported)
    assert sorted(exported["paths"]) == ["/healthz", "/readyz"]


def test_export_prints_the_spec_by_default(capsys):
    main([])

    assert json.loads(capsys.readouterr().out)["info"]["title"] == "rfab-proxy"


def test_export_command_runs_as_a_module(tmp_path):
    # `python -m` loads this module a second time as __main__; the export must
    # still read the spec registered by the real module.
    import subprocess
    import sys

    output = tmp_path / "openapi.json"
    subprocess.run(
        [sys.executable, "-m", "rfab_proxy.openapi", "--output", str(output)], check=True
    )

    assert sorted(json.loads(output.read_text())["paths"]) == ["/healthz", "/readyz"]

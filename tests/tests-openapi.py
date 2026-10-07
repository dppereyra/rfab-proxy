import falcon.inspect
import falcon.testing
import jsonschema
import pytest
from openapi_spec_validator import validate

import rfab_proxy
from rfab_proxy.app import create_app
from rfab_proxy.config import Settings
from rfab_proxy.openapi import load_spec

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


@pytest.fixture
def app():
    return create_app(Settings.from_env({}))


@pytest.fixture
def client(app):
    return falcon.testing.TestClient(app)


def _schema_for(spec, path, status):
    operation = spec["paths"][path]["get"]
    schema = operation["responses"][str(status)]["content"]["application/json"]["schema"]
    # Resolve "#/components/..." references against the whole document.
    return {**schema, "components": spec["components"]}


def test_spec_is_a_valid_openapi_3_1_document():
    spec = load_spec()

    validate(spec)
    assert spec["openapi"].startswith("3.1.")


def test_spec_is_served_as_json_with_the_package_version(client):
    result = client.simulate_get("/openapi.json")

    assert result.status_code == 200
    assert result.json["openapi"] == load_spec()["openapi"]
    assert result.json["info"]["version"] == rfab_proxy.__version__


def test_routes_and_spec_do_not_drift(app):
    routes = {
        (route.path, method.method.lower())
        for route in falcon.inspect.inspect_routes(app)
        for method in route.methods
        if not method.internal
    }
    documented = {
        (path, method)
        for path, item in load_spec()["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }

    assert routes == documented


@pytest.mark.parametrize(
    ("path", "status", "checks"),
    [
        ("/healthz", 200, []),
        ("/readyz", 200, [lambda: True]),
        ("/readyz", 503, [lambda: False]),
    ],
)
def test_responses_match_the_documented_schemas(path, status, checks):
    client = falcon.testing.TestClient(create_app(Settings.from_env({}), readiness_checks=checks))
    result = client.simulate_get(path)

    assert result.status_code == status
    jsonschema.validate(result.json, _schema_for(load_spec(), path, status))


def test_spec_declares_the_agpl_license():
    assert load_spec()["info"]["license"] == {
        "name": "GNU Affero General Public License v3.0 or later",
        "identifier": "AGPL-3.0-or-later",
    }

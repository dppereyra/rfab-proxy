import falcon
import falcon.testing
import pytest

from rfab_proxy.app import create_app
from rfab_proxy.config import Settings


@pytest.fixture
def settings():
    return Settings.from_env({})


@pytest.fixture
def client(settings):
    return falcon.testing.TestClient(create_app(settings))


def test_create_app_builds_an_asgi_app(settings):
    assert isinstance(create_app(settings), falcon.asgi.App)


def test_create_app_reads_settings_from_the_environment(monkeypatch):
    monkeypatch.setenv("RFAB_PORT", "9000")

    assert isinstance(create_app(), falcon.asgi.App)


def test_liveness_reports_alive(client):
    result = client.simulate_get("/healthz")

    assert result.status_code == 200
    assert result.json == {"status": "alive"}


def test_readiness_reports_ready_when_every_check_passes(settings):
    client = falcon.testing.TestClient(create_app(settings, readiness_checks=[lambda: True]))

    result = client.simulate_get("/readyz")

    assert result.status_code == 200
    assert result.json == {"status": "ready"}


def test_readiness_reports_unavailable_when_a_check_fails(settings):
    checks = [lambda: True, lambda: False]
    client = falcon.testing.TestClient(create_app(settings, readiness_checks=checks))

    result = client.simulate_get("/readyz")

    assert result.status_code == 503
    assert result.json["title"] == "503 Service Unavailable"


def test_unknown_route_returns_a_json_error(client):
    result = client.simulate_get("/does-not-exist")

    assert result.status_code == 404
    assert result.headers["content-type"].startswith("application/json")
    assert result.json["title"] == "404 Not Found"


def test_unhandled_exception_returns_a_json_500_and_is_logged(settings, caplog):
    app = create_app(settings)

    class Boom:
        async def on_get(self, req, resp):
            raise RuntimeError("secret detail")

    app.add_route("/boom", Boom())
    client = falcon.testing.TestClient(app)

    result = client.simulate_get("/boom")

    assert result.status_code == 500
    assert result.json == {"title": "500 Internal Server Error"}
    assert "secret detail" not in result.text
    assert any(record.exc_info for record in caplog.records)

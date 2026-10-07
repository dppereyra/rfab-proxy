import pytest
import sentry_sdk

import rfab_proxy
from rfab_proxy import monitoring
from rfab_proxy.config import Settings


@pytest.fixture
def init_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(monitoring.sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))
    return calls


def test_init_is_a_no_op_without_a_dsn(init_calls):
    assert monitoring.init_sentry(Settings.from_env({})) is False
    assert init_calls == []
    assert not sentry_sdk.get_client().is_active()


def test_init_configures_sentry_from_settings(init_calls):
    settings = Settings.from_env(
        {
            "SENTRY_DSN": "https://public@sentry.example/1",
            "SENTRY_ENVIRONMENT": "staging",
            "SENTRY_SAMPLE_RATE": "0.5",
        }
    )

    assert monitoring.init_sentry(settings) is True

    (kwargs,) = init_calls
    assert kwargs["dsn"] == "https://public@sentry.example/1"
    assert kwargs["environment"] == "staging"
    assert kwargs["release"] == f"rfab-proxy@{rfab_proxy.__version__}"
    assert kwargs["sample_rate"] == 0.5
    assert kwargs["send_default_pii"] is False
    assert kwargs["include_local_variables"] is False
    assert kwargs["before_send"] is monitoring.scrub_event


def test_sentry_does_not_trace_because_opentelemetry_does(init_calls):
    monitoring.init_sentry(Settings.from_env({"SENTRY_DSN": "https://public@sentry.example/1"}))

    (kwargs,) = init_calls
    assert kwargs["traces_sample_rate"] is None


def test_scrub_event_filters_credentials_in_request_headers():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer abc",
                "Proxy-Authorization": "Basic xyz",
                "X-Api-Key": "k",
                "Accept": "application/json",
            },
            "cookies": {"session": "s"},
        }
    }

    scrubbed = monitoring.scrub_event(event, {})

    headers = scrubbed["request"]["headers"]
    assert headers["Authorization"] == "[Filtered]"
    assert headers["Proxy-Authorization"] == "[Filtered]"
    assert headers["X-Api-Key"] == "[Filtered]"
    assert headers["Accept"] == "application/json"
    assert "cookies" not in scrubbed["request"]


def test_scrub_event_passes_events_without_a_request_through():
    event = {"message": "hello"}

    assert monitoring.scrub_event(event, {}) == {"message": "hello"}


@pytest.fixture
def captured_events(monkeypatch):
    events = []
    real_init = sentry_sdk.init

    class CapturingTransport(sentry_sdk.transport.Transport):
        def capture_envelope(self, envelope):
            events.extend(item.payload.json for item in envelope.items if item.type == "event")

    monkeypatch.setattr(
        monitoring.sentry_sdk,
        "init",
        lambda **kwargs: real_init(transport=CapturingTransport(), **kwargs),
    )
    yield events
    real_init()  # deactivate the client again


def test_unhandled_errors_reach_sentry_through_logging(captured_events):
    import falcon.testing

    from rfab_proxy.app import create_app

    settings = Settings.from_env({"SENTRY_DSN": "https://public@sentry.example/1"})
    app = create_app(settings)

    class Boom:
        async def on_get(self, req, resp):
            raise RuntimeError("boom")

    app.add_route("/boom", Boom())
    # Built at runtime so the value can't show up via captured source lines.
    credential = "Bearer " + "-".join(["not", "in", "source"])
    falcon.testing.TestClient(app).simulate_get("/boom", headers={"Authorization": credential})
    sentry_sdk.flush()

    (event,) = captured_events
    exception = event["exception"]["values"][-1]
    assert exception["type"] == "RuntimeError"
    assert credential not in str(event)
    assert all("vars" not in frame for frame in exception["stacktrace"]["frames"])

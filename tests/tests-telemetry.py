import asyncio
import http.server
import threading

import falcon.asgi
import httpx
import pytest
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

import rfab_proxy
from rfab_proxy.app import create_app, create_asgi_app
from rfab_proxy.config import Settings
from rfab_proxy.telemetry import Telemetry, instrument, telemetry_from_env

ENDPOINT = {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector.invalid:4318"}
TRACEPARENT = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"


@pytest.fixture
def spans():
    return InMemorySpanExporter()


@pytest.fixture
def metrics():
    return InMemoryMetricReader()


@pytest.fixture
def telemetry(spans, metrics):
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(spans))
    yield Telemetry(tracer_provider, MeterProvider(metric_readers=[metrics]))
    HTTPXClientInstrumentor().uninstrument()


@pytest.fixture
def app(telemetry):
    return instrument(create_app(Settings.from_env({})), telemetry)


def get(app, path, headers=None):
    # falcon.testing hands OpenTelemetry an ASGI scope it can't parse, so the
    # instrumented app is driven through httpx's ASGI transport instead.
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path, headers=headers)

    return asyncio.run(send())


def server_spans(spans):
    return [span for span in spans.get_finished_spans() if span.kind is SpanKind.SERVER]


def test_telemetry_is_off_without_an_otlp_endpoint():
    assert telemetry_from_env({}) is None


def test_telemetry_respects_otel_sdk_disabled():
    assert telemetry_from_env({**ENDPOINT, "OTEL_SDK_DISABLED": "true"}) is None


@pytest.mark.parametrize(
    "variable",
    [
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
    ],
)
def test_telemetry_turns_on_with_any_otlp_endpoint(variable):
    telemetry = telemetry_from_env({variable: "http://collector.invalid:4318"})
    try:
        resource = telemetry.tracer_provider.resource.attributes
        assert resource["service.name"] == "rfab-proxy"
        assert resource["service.version"] == rfab_proxy.__version__
    finally:
        telemetry.shutdown()


def test_service_name_comes_from_otel_service_name():
    telemetry = telemetry_from_env({**ENDPOINT, "OTEL_SERVICE_NAME": "edge-proxy"})
    try:
        assert telemetry.tracer_provider.resource.attributes["service.name"] == "edge-proxy"
    finally:
        telemetry.shutdown()


def test_instrument_leaves_the_app_alone_without_telemetry():
    app = create_app(Settings.from_env({}))

    assert instrument(app, None) is app


def test_create_asgi_app_is_plain_falcon_when_telemetry_is_off():
    assert isinstance(create_asgi_app(Settings.from_env({}), environ={}), falcon.asgi.App)


def test_create_asgi_app_is_instrumented_when_telemetry_is_on():
    app = create_asgi_app(Settings.from_env({}), environ=ENDPOINT)
    try:
        assert isinstance(app, OpenTelemetryMiddleware)
    finally:
        HTTPXClientInstrumentor().uninstrument()


def test_requests_produce_one_server_span(app, spans):
    get(app, "/nothing-here")

    (span,) = spans.get_finished_spans()
    assert span.kind is SpanKind.SERVER
    assert span.name == "GET /nothing-here"


def test_health_probes_are_not_traced(app, spans):
    get(app, "/healthz")
    get(app, "/readyz")

    assert spans.get_finished_spans() == ()


def test_incoming_w3c_trace_context_is_continued(app, spans):
    get(app, "/nothing-here", headers={"traceparent": TRACEPARENT})

    (span,) = server_spans(spans)
    assert format(span.context.trace_id, "032x") == "0af7651916cd43dd8448eb211c80319c"


def test_credentials_never_become_span_attributes(app, spans):
    get(app, "/nothing-here?token=abc123&user=me", headers={"Authorization": "Bearer xyz"})

    (span,) = server_spans(spans)
    values = " ".join(str(value) for value in span.attributes.values())
    assert "abc123" not in values
    assert "Bearer xyz" not in values
    assert span.attributes["http.url"] == (
        "http://testserver/nothing-here?token=REDACTED&user=REDACTED"
    )


def test_request_metrics_are_recorded(app, metrics):
    get(app, "/nothing-here")

    names = {
        metric.name
        for resource in metrics.get_metrics_data().resource_metrics
        for scope in resource.scope_metrics
        for metric in scope.metrics
    }
    assert "http.server.duration" in names


@pytest.fixture
def upstream():
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            received.append(dict(self.headers))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", received
    server.shutdown()


def test_upstream_calls_carry_the_trace_context(app, telemetry, spans, upstream):
    url, received = upstream
    tracer = telemetry.tracer_provider.get_tracer("test")

    with tracer.start_as_current_span("proxying") as parent:
        httpx.get(f"{url}/resource?api_key=abc123")

    trace_id = format(parent.get_span_context().trace_id, "032x")
    (headers,) = received
    assert headers["traceparent"].split("-")[1] == trace_id

    (client,) = [span for span in spans.get_finished_spans() if span.kind is SpanKind.CLIENT]
    assert "abc123" not in " ".join(str(value) for value in client.attributes.values())


def test_async_upstream_calls_are_traced_and_redacted(app, telemetry, spans, upstream):
    url, received = upstream

    async def call():
        async with httpx.AsyncClient() as client:
            await client.get(f"{url}/resource?api_key=abc123")

    asyncio.run(call())

    (headers,) = received
    assert "traceparent" in headers
    (client,) = [span for span in spans.get_finished_spans() if span.kind is SpanKind.CLIENT]
    assert "abc123" not in " ".join(str(value) for value in client.attributes.values())


def test_stable_semantic_convention_attributes_are_redacted_too(telemetry):
    from rfab_proxy.telemetry import _redact_query

    tracer = telemetry.tracer_provider.get_tracer("test")
    with tracer.start_as_current_span(
        "span", attributes={"url.full": "http://up/r?key=abc123", "url.query": "key=abc123"}
    ) as span:
        _redact_query(span, b"key=abc123")

    assert span.attributes["url.full"] == "http://up/r?key=REDACTED"
    assert span.attributes["url.query"] == "key=REDACTED"

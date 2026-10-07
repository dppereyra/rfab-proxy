"""OpenTelemetry tracing and metrics.

Telemetry is configured through the standard OTEL_* environment variables and
stays off until an OTLP endpoint is set. OpenTelemetry owns tracing; Sentry
only reports errors (see rfab_proxy.monitoring).

Falcon's OpenTelemetry instrumentation only covers WSGI apps, so the ASGI app
is wrapped in the generic ASGI middleware instead. Upstream calls made with
httpx are instrumented so the W3C trace context propagates through the proxy.
Query strings can carry credentials in a proxy, so their values are redacted
from URL attributes on both server and client spans.
"""

import os
from dataclasses import dataclass

from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from rfab_proxy import __version__
from rfab_proxy.redaction import redact_query, redact_url

_ENDPOINT_VARIABLES = (
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
)
_UNTRACED_PATHS = "healthz,readyz"
_URL_ATTRIBUTES = ("http.url", "url.full")


@dataclass(frozen=True)
class Telemetry:
    tracer_provider: TracerProvider
    meter_provider: MeterProvider

    def shutdown(self):
        self.tracer_provider.shutdown()
        self.meter_provider.shutdown()


def telemetry_from_env(environ=None):
    """Build OTLP-exporting providers, or return None when telemetry is off."""
    environ = os.environ if environ is None else environ
    if environ.get("OTEL_SDK_DISABLED", "").strip().lower() == "true":
        return None
    if not any(environ.get(name) for name in _ENDPOINT_VARIABLES):
        return None

    resource = Resource.create(
        {
            "service.name": environ.get("OTEL_SERVICE_NAME", "rfab-proxy"),
            "service.version": __version__,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    meter_provider = MeterProvider(
        resource=resource, metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())]
    )
    return Telemetry(tracer_provider, meter_provider)


def instrument(app, telemetry):
    """Wrap the ASGI app and instrument httpx; returns the app as-is when off."""
    if telemetry is None:
        return app

    HTTPXClientInstrumentor().instrument(
        tracer_provider=telemetry.tracer_provider,
        meter_provider=telemetry.meter_provider,
        request_hook=_redact_client_request,
        async_request_hook=_redact_async_client_request,
    )
    return OpenTelemetryMiddleware(
        app,
        excluded_urls=_UNTRACED_PATHS,
        exclude_spans=["receive", "send"],
        server_request_hook=_redact_server_request,
        tracer_provider=telemetry.tracer_provider,
        meter_provider=telemetry.meter_provider,
    )


def _redact_server_request(span, scope):
    _redact_query(span, scope.get("query_string", b""))


def _redact_client_request(span, request):
    _redact_query(span, request.url.query)


async def _redact_async_client_request(span, request):
    _redact_client_request(span, request)


def _redact_query(span, query):
    attributes = getattr(span, "attributes", None)
    if not query or not attributes:
        return
    for name in _URL_ATTRIBUTES:
        if name in attributes:
            span.set_attribute(name, redact_url(attributes[name]))
    if "url.query" in attributes:
        span.set_attribute("url.query", redact_query(query.decode("latin-1")))

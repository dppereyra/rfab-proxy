# rfab-proxy

**Use [rfab.ai](https://rfab.ai) from the AI tools on your machine, through the APIs they already speak.**

Many local AI applications talk to a model server through a handful of widely used APIs, such as
the [Ollama API](https://docs.ollama.com/api). rfab-proxy is a small
service you run locally that presents rfab.ai behind those common APIs. A tool that already knows
how to talk to one of them can use rfab.ai by pointing at `http://127.0.0.1:8000`, without any
rfab.ai-specific code.

```text
 your local tools ──► rfab-proxy (localhost) ──► rfab.ai
 (apps, scripts,       common AI APIs
  integrations)        (e.g. the Ollama API)
```

Which APIs rfab-proxy will offer hasn't been decided yet. The Ollama API is the reference example,
and the others will be chosen by what the tools people want to connect actually use.

> rfab-proxy is an independent, unofficial project and is not affiliated with rfab.ai.

## Status

Early development. The service foundation is in place: the ASGI application, configuration,
health probes, structured logging, error reporting, tracing and the OpenAPI document. Choosing the
common APIs and implementing the rfab.ai proxy endpoints behind them is the next milestone (see
[Roadmap](#roadmap)).

What runs today:

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness probe: `{"status": "alive"}` |
| `GET /readyz` | Readiness probe: `{"status": "ready"}`, or 503 when not ready |
| `GET /openapi.json` | The OpenAPI 3.1 description of the API |

## Quick start

rfab-proxy needs Python 3.14. Tool versions are pinned in `mise.toml`, so the easiest setup is
[mise](https://mise.jdx.dev):

```bash
git clone https://github.com/dppereyra/rfab-proxy.git
cd rfab-proxy
mise install          # Python, uv, tox and the other pinned tools
uv sync               # install rfab-proxy and its dependencies
mise run serve        # or: uv run rfab-proxy
```

Then check it's up:

```bash
curl http://127.0.0.1:8000/healthz
```

## Configuration

Everything is configured through environment variables. Invalid values stop the service at
startup.

| Variable | Default | Description |
|---|---|---|
| `RFAB_HOST` | `127.0.0.1` | Address to listen on. Keep the default for local-only use; set `0.0.0.0` in a container |
| `RFAB_PORT` | `8000` | Port to listen on |
| `RFAB_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Logs are JSON lines on stderr |
| `SENTRY_DSN` | _(unset)_ | Report errors to Sentry. Off when unset |
| `SENTRY_ENVIRONMENT` | `production` | Sentry environment name |
| `SENTRY_SAMPLE_RATE` | `1.0` | Fraction of errors sent to Sentry (0–1) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(unset)_ | Export traces and metrics over OTLP/HTTP. Off when unset |
| `OTEL_SERVICE_NAME` | `rfab-proxy` | Service name reported with traces and metrics |

The other standard `OTEL_*` variables (such as `OTEL_SDK_DISABLED` and per-signal endpoints)
are honoured too.

## Privacy and security

A proxy handles credentials, so rfab-proxy keeps them out of every place it writes to:

- Query-string values are redacted in access logs and traces.
- Request headers such as `Authorization` are never recorded in traces.
- Error reports carry no personal data or local variables, and credential headers and cookies
  are scrubbed before they leave the process.
- Telemetry and error reporting are off unless you configure them.
- By default the service only listens on `127.0.0.1`, so it isn't reachable from other machines.

To report a vulnerability, see [SECURITY.md](.github/SECURITY.md).

## Roadmap

| Milestone | What it brings |
|---|---|
| Setup initial project | Packaging, tooling, CI, the application skeleton, observability and the OpenAPI document |
| Setup release pipeline | Automated, versioned releases |
| Road to v1 | The common APIs to support, and the rfab.ai proxy endpoints behind them |
| Setup authentication | Authentication for the proxy |
| Publish software | A public Docker image and a Helm chart |
| Create wiki on GitHub Pages | Documentation at [dppereyra.github.io/rfab-proxy](https://dppereyra.github.io/rfab-proxy) |

## Development

```bash
mise install          # pinned toolchain
tox                   # the full suite: tests on 3.14 and 3.15, lint, security, complexity, dead code, OpenAPI, lock
tox -e py314          # just the tests
mise run test         # tests on every supported Python
```

- `src/rfab_proxy/` holds the application and `tests/` the test suite (files named `tests-*.py`).
- The API is described first in `src/rfab_proxy/openapi.yaml`; a test fails if the routes and the
  spec disagree.
- Development is test-driven, with branch coverage of at least 90%.

Working agreements for contributors and coding agents are in [AGENTS.md](AGENTS.md).

## License

Copyright (C) 2026 Dennis Philippe Pereyra Jr. (DPPereyra)

rfab-proxy is free software: you can redistribute it and/or modify it under the terms of the
GNU Affero General Public License as published by the Free Software Foundation, either version 3
of the License, or (at your option) any later version. See [LICENSE](LICENSE).

Because the AGPL covers use over a network, anyone who runs a modified rfab-proxy as a service
must offer its users the corresponding source code.

"""Shared pytest fixtures for rfab-proxy."""

import os

import pytest

_APP_ENV_PREFIXES = ("RFAB_", "SENTRY_", "OTEL_")


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Keep the developer's shell (e.g. a real SENTRY_DSN) out of the tests."""
    for name in list(os.environ):
        if name.startswith(_APP_ENV_PREFIXES):
            monkeypatch.delenv(name)

import json
import logging
import sys

from rfab_proxy.logging import JsonFormatter, configure_logging


def _record(**extra):
    record = logging.LogRecord(
        "rfab_proxy.test", logging.INFO, __file__, 1, "hello %s", ("world",), None
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formats_records_as_one_json_object():
    payload = json.loads(JsonFormatter().format(_record()))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "rfab_proxy.test"
    assert payload["message"] == "hello world"
    assert "timestamp" in payload


def test_includes_the_exception_when_present():
    try:
        raise ValueError("bad")
    except ValueError:
        record = _record()
        record.exc_info = sys.exc_info()

    payload = json.loads(JsonFormatter().format(record))

    assert "ValueError: bad" in payload["exception"]


def _json_handlers():
    return [h for h in logging.getLogger().handlers if isinstance(h.formatter, JsonFormatter)]


def test_configure_logging_sets_the_level_and_a_json_handler():
    configure_logging("DEBUG")

    assert logging.getLogger().level == logging.DEBUG
    assert len(_json_handlers()) == 1


def test_configure_logging_is_idempotent():
    configure_logging("INFO")
    configure_logging("INFO")

    assert len(_json_handlers()) == 1


def test_configure_logging_keeps_handlers_it_did_not_install():
    other = logging.NullHandler()
    logging.getLogger().addHandler(other)
    try:
        configure_logging("INFO")

        assert other in logging.getLogger().handlers
    finally:
        logging.getLogger().removeHandler(other)


def test_http_client_request_logs_are_silenced():
    # httpx logs every request URL at INFO, query strings and userinfo included.
    configure_logging("DEBUG")

    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_access_log_query_values_are_redacted():
    configure_logging("INFO")
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", "/r?token=abc123", "1.1", 404),
        None,
    )

    assert logging.getLogger("uvicorn.access").filter(record)
    assert record.getMessage() == '127.0.0.1:5000 - "GET /r?token=REDACTED HTTP/1.1" 404'


def test_access_log_filter_ignores_unexpected_records():
    configure_logging("INFO")
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, "plain", (), None)

    assert logging.getLogger("uvicorn.access").filter(record)
    assert record.getMessage() == "plain"


def test_access_log_filter_is_installed_once():
    configure_logging("INFO")
    configure_logging("INFO")

    assert len(logging.getLogger("uvicorn.access").filters) == 1

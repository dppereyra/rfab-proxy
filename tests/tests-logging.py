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

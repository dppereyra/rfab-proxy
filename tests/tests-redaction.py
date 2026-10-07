import pytest

from rfab_proxy.redaction import redact_query, redact_url


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", ""),
        ("token=abc", "token=REDACTED"),
        ("a=1&b=&c", "a=REDACTED&b=REDACTED&c=REDACTED"),
    ],
)
def test_redact_query_keeps_keys_and_hides_values(query, expected):
    assert redact_query(query) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("/path", "/path"),
        ("/path?token=abc", "/path?token=REDACTED"),
        ("http://up/r?key=abc&x=1", "http://up/r?key=REDACTED&x=REDACTED"),
    ],
)
def test_redact_url_only_touches_the_query(url, expected):
    assert redact_url(url) == expected

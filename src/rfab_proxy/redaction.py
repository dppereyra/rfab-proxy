"""Hide query-string values, which can carry credentials in a proxy."""

from urllib.parse import parse_qsl, urlencode

REDACTED = "REDACTED"


def redact_query(query):
    pairs = parse_qsl(query, keep_blank_values=True)
    return urlencode([(key, REDACTED) for key, _ in pairs])


def redact_url(url):
    base, separator, query = url.partition("?")
    if not separator:
        return url
    return f"{base}?{redact_query(query)}"

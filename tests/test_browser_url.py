import pytest

from core.browser_url import normalize_http_url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("YouTube", "https://www.youtube.com/"),
        ("example.com", "https://example.com/"),
        ("example.com/path?q=jarvis#top", "https://example.com/path?q=jarvis#top"),
        ("http://example.com", "http://example.com/"),
        ("HTTPS://example.com", "https://example.com/"),
        ("localhost:8080/health", "https://localhost:8080/health"),
        ("//example.com/path", "https://example.com/path"),
    ],
)
def test_normalize_http_url_accepts_web_addresses(value, expected):
    assert normalize_http_url(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "file:///C:/secret.txt",
        "javascript:alert(1)",
        "data:text/html,hello",
        "ftp://example.com",
        "mailto:user@example.com",
        "https:example.com",
        "https://",
        "https://user:password@example.com",
        "https://example.com:70000",
        "https://example.com:not-a-port",
    ],
)
def test_normalize_http_url_rejects_unsafe_or_invalid_addresses(value):
    with pytest.raises(ValueError):
        normalize_http_url(value)


def test_normalize_http_url_rejects_non_text():
    with pytest.raises(TypeError, match="URL must be text"):
        normalize_http_url(None)

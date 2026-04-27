"""Template-injection regression tests — SSID/password/URL fed into C strings."""

from __future__ import annotations

import pytest

from darml.infrastructure.builders.platformio_builder import (
    _safe_template_ssid,
    _safe_template_url,
    _safe_template_wpa_pass,
)


# ── SSID ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("good", [
    "MyWifi",
    "café",  # NOTE: this should FAIL — multi-byte; kept here as a negative below
])
def test_ssid_accepts_plain_ascii(good: str) -> None:
    if good == "café":
        # Non-ASCII fails the [0x20-0x7e] range check.
        with pytest.raises(ValueError):
            _safe_template_ssid(good)
    else:
        assert _safe_template_ssid(good) == good


@pytest.mark.parametrize("bad, reason", [
    ('foo"; system("x"); //', "double quote breaks out of C string"),
    ('foo\\bar',              "backslash starts a C escape sequence"),
    ('foo\nbar',              "newline ends a C string"),
    ('foo\rbar',              "CR breaks lines"),
    ('a' * 33,                "33 chars exceeds IEEE 802.11 32-byte SSID limit"),
    ('',                      "empty handled separately — but treated as None"),
])
def test_ssid_rejects_dangerous(bad: str, reason: str) -> None:
    if bad == "":
        # Empty SSID is normalized to "" (no Wi-Fi configured) — no raise.
        assert _safe_template_ssid(bad) == ""
        return
    with pytest.raises(ValueError):
        _safe_template_ssid(bad)


# ── WPA password ───────────────────────────────────────────────────────────

def test_wpa_pass_accepts_typical() -> None:
    assert _safe_template_wpa_pass("hunter2hunter2") == "hunter2hunter2"


@pytest.mark.parametrize("bad", [
    "short7",                     # < 8 chars
    "a" * 64,                     # > 63 chars
    'long"enough"and"escapes',    # double quote
    'long\\enough\\backslash',    # backslash
    "passwd\nwithnewline",        # CR/LF
])
def test_wpa_pass_rejects_dangerous(bad: str) -> None:
    with pytest.raises(ValueError):
        _safe_template_wpa_pass(bad)


# ── report_url (template-side, after API-edge SSRF check) ──────────────────

def test_url_accepts_plain_https() -> None:
    out = _safe_template_url("https://example.com/path")
    assert out.startswith("https://example.com")


@pytest.mark.parametrize("bad", [
    'https://example.com/"; system("x"); //',  # quote
    "https://example.com/\\path",              # backslash
    "https://example.com/\nfoo",               # CR/LF embedded
    "https://example.com/\x00bar",             # NUL
    "ftp://example.com",                       # disallowed scheme
])
def test_url_rejects_dangerous(bad: str) -> None:
    with pytest.raises(ValueError):
        _safe_template_url(bad)


def test_url_empty_returns_empty() -> None:
    assert _safe_template_url(None) == ""
    assert _safe_template_url("") == ""

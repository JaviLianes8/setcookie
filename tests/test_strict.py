"""Strict mode against the server grammar of section 4.1.1 (cases written by hand)."""

from __future__ import annotations

import pytest

from setcookie import CookieError, parse

VALID = [
    "sid=abc",
    'sid="abc"',
    "sid=",
    'sid=""',
    " sid = abc ; Path=/",
    "sid=abc;Path=/;Secure",
    "sid=abc; Expires=Sun, 06 Nov 1994 08:49:37 GMT",
    "sid=abc; expires = Sun, 06 Nov 1994 08:49:37 GMT",
    "sid=abc; Max-Age=1",
    "sid=abc; Max-Age=86400",
    "sid=abc; Domain=sub.example.com",
    "sid=abc; Domain=127.0.0.1",
    "sid=abc; Path=",
    "sid=abc; Path=relative",
    "sid=abc; HTTPONLY; samesite=strict",
    "sid=abc; SameSite=None; Secure",
    "sid=abc; Secure; Partitioned",
    "sid=abc; Priority=High; x-flag",
    "__Secure-sid=abc; Secure; Domain=site.example",
    "__Host-sid=abc; Secure; Path=/",
    "!#$%&'*+-.^_`|~=!#$%&'()*+-./:<=>?@[]^_`{|}~",
]

INVALID = [
    ("sid", "no '='"),
    ("=abc", "not a token"),
    ("s id=abc", "not a token"),
    ("s\u00e9=abc", "not a token"),
    ("sid=a b", "outside cookie-octet"),
    ("sid=a,b", "outside cookie-octet"),
    ("sid=a\\b", "outside cookie-octet"),
    ('sid="abc', "outside cookie-octet"),
    ('sid=a"b', "outside cookie-octet"),
    ("sid=\u00e9", "outside cookie-octet"),
    ("sid=abc ", "trailing whitespace"),
    ("sid=abc;", "empty attribute"),
    ("sid=abc; ; Secure", "empty attribute"),
    ("sid=abc; Expires=Sun Nov  6 08:49:37 1994", "IMF-fixdate"),
    ("sid=abc; Expires=Sun, 31 Nov 1994 08:49:37 GMT", "IMF-fixdate"),
    ("sid=abc; Max-Age=0", "non-zero-digit"),
    ("sid=abc; Max-Age=-1", "non-zero-digit"),
    ("sid=abc; Max-Age=01", "non-zero-digit"),
    ("sid=abc; Max-Age", "needs a value"),
    ("sid=abc; Domain=.example.com", "not a host name"),
    ("sid=abc; Domain=", "not a host name"),
    ("sid=abc; Domain=-x.com", "not a host name"),
    ("sid=abc; Domain=ex_ample.com", "not a host name"),
    ("sid=abc; Path=/\u00e9", "outside av-octet"),
    ("sid=abc; Secure=yes", "takes no value"),
    ("sid=abc; HttpOnly=", "takes no value"),
    ("sid=abc; SameSite=Default", "not Strict, Lax or None"),
    ("sid=abc; Path=/; path=/x", "appears twice"),
    ("sid=abc; Priority=High; priority=Low", "appears twice"),
    ("sid=abc; x\u00e9", "outside av-octet"),
    ("sid=abc; Path=/" + "p" * 1024, "longer than 1024"),
    ("n=" + "v" * 4095 + "v", "longer than 4096"),
    ("sid=abc; SameSite=None", "SameSite=None needs"),
    ("sid=abc; Partitioned", "Partitioned needs"),
    ("__Secure-sid=abc", "__Secure- cookie needs"),
    ("__SECURE-sid=abc", "__Secure- cookie needs"),
    ("__Host-sid=abc; Path=/", "__Host- cookie needs the Secure"),
    ("__host-sid=abc; Secure", "__Host- cookie needs Path=/"),
    ("__Host-sid=abc; Secure; Path=/x", "__Host- cookie needs Path=/"),
    ("__Host-sid=abc; Secure; Path=/; Domain=site.example", "must not have a Domain"),
]


@pytest.mark.parametrize("line", VALID)
def test_strict_accepts_the_server_grammar(line: str) -> None:
    assert parse(line, strict=True) == parse(line)


@pytest.mark.parametrize(("line", "reason"), INVALID)
def test_strict_names_the_broken_rule(line: str, reason: str) -> None:
    with pytest.raises(CookieError, match=r"^strict: ") as caught:
        parse(line, strict=True)
    assert reason in str(caught.value)


def test_lenient_parse_accepts_what_strict_refuses() -> None:
    for line, reason in INVALID:
        if "4096" not in reason:
            parse(line)


@pytest.mark.parametrize("code", [*range(0x00, 0x09), *range(0x0A, 0x20), 0x7F])
def test_strict_refuses_control_characters_everywhere(code: int) -> None:
    char = chr(code)
    for line in (f"s{char}d=a", f"sid=a{char}", f"sid=a; Path=/{char}", f"sid=a; X={char}y"):
        with pytest.raises(CookieError):
            parse(line, strict=True)

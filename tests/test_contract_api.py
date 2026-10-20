"""The 1.0.0 promise: names, signatures, defaults, fields, error types and safe messages."""

from __future__ import annotations

import dataclasses
import inspect
import pickle
import typing
from datetime import date, datetime, timezone

import pytest

import setcookie
from setcookie import Cookie, CookieError, StoredCookie, build, expire, parse, parse_date, receive

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)
KW = inspect.Parameter.KEYWORD_ONLY
POS = inspect.Parameter.POSITIONAL_OR_KEYWORD
EMPTY = inspect.Parameter.empty

SIGNATURES: dict[str, list[tuple[str, inspect._ParameterKind, object]]] = {
    "build": [
        ("name", POS, EMPTY), ("value", POS, EMPTY), ("expires", KW, None),
        ("max_age", KW, None), ("domain", KW, None), ("path", KW, "/"), ("secure", KW, False),
        ("http_only", KW, False), ("same_site", KW, None), ("partitioned", KW, False),
        ("extensions", KW, ()),
    ],
    "expire": [
        ("name", POS, EMPTY), ("domain", KW, None), ("path", KW, "/"), ("secure", KW, False),
        ("http_only", KW, False), ("same_site", KW, None), ("partitioned", KW, False),
    ],
    "parse": [("line", POS, EMPTY), ("strict", KW, False)],
    "parse_date": [("text", POS, EMPTY)],
    "receive": [
        ("line", POS, EMPTY), ("url", POS, EMPTY), ("now", KW, EMPTY),
        ("cross_site", KW, False), ("is_public_suffix", KW, None),
    ],
}  # fmt: skip
COOKIE_FIELDS = [
    ("name", dataclasses.MISSING), ("value", dataclasses.MISSING), ("expires", None),
    ("max_age", None), ("domain", None), ("path", None), ("secure", False), ("http_only", False),
    ("same_site", None), ("partitioned", False), ("extensions", ()),
]  # fmt: skip
STORED_FIELDS = [
    "name", "value", "domain", "path", "host_only", "secure", "http_only", "same_site",
    "partitioned", "persistent", "expiry",
]  # fmt: skip


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_function_signatures_are_pinned(name: str) -> None:
    found = inspect.signature(getattr(setcookie, name)).parameters.values()
    assert [(p.name, p.kind, p.default) for p in found] == SIGNATURES[name]


def test_cookie_fields_and_defaults_are_pinned() -> None:
    fields = dataclasses.fields(Cookie)
    assert [(f.name, f.default) for f in fields] == COOKIE_FIELDS
    assert [f.name for f in dataclasses.fields(StoredCookie)] == STORED_FIELDS
    assert all(f.default is dataclasses.MISSING for f in dataclasses.fields(StoredCookie))


def test_records_are_frozen_hashable_and_pickle_by_public_name() -> None:
    cookie = parse("sid=abc; Path=/; x")
    stored = receive("sid=abc", "https://h.test/", now=NOW)
    for record in (cookie, stored):
        with pytest.raises(dataclasses.FrozenInstanceError):
            record.name = "x"  # type: ignore[misc]
        assert hash(record) == hash(pickle.loads(pickle.dumps(record)))
        assert pickle.loads(pickle.dumps(record)) == record
        assert type(record).__module__ == "setcookie"
    assert CookieError.__module__ == "setcookie"
    assert repr(CookieError("x")) == "CookieError('x')"


def test_same_site_is_the_three_value_literal() -> None:
    assert typing.get_args(setcookie.SameSite) == ("Lax", "Strict", "None")


def test_cookie_error_is_a_value_error_and_not_a_type_error() -> None:
    assert issubclass(CookieError, ValueError)
    assert not issubclass(CookieError, TypeError)


WRONG_TYPES = [
    (lambda: parse(b"a=b"), "line must be a str, got bytes"),  # type: ignore[arg-type]
    (lambda: parse("a=b", strict=1), "strict must be a bool, got int"),  # type: ignore[arg-type]
    (lambda: parse_date(None), "text must be a str, got NoneType"),  # type: ignore[arg-type]
    (lambda: build("a", "b", http_only=None), "http_only must be a bool"),  # type: ignore[arg-type]
    (lambda: build("a", "b", partitioned="yes"), "partitioned must be a bool"),  # type: ignore[arg-type]
    (lambda: build("a", "b", domain=b"x"), "domain must be a str or None"),  # type: ignore[arg-type]
    (lambda: build("a", "b", path=1), "path must be a str or None"),  # type: ignore[arg-type]
    (lambda: build("a", "b", same_site=1), "same_site must be a str or None"),  # type: ignore[arg-type]
    (lambda: build("a", "b", extensions=[["x", "y"]]), "a (name, value) tuple"),  # type: ignore[list-item]
    (lambda: build("a", "b", extensions=b"xy"), "an iterable of"),  # type: ignore[arg-type]
    (lambda: expire(None), "name must be a str"),  # type: ignore[arg-type]
    (lambda: receive(1, "https://h/", now=NOW), "line must be a str"),  # type: ignore[arg-type]
    (lambda: receive("a=b", None, now=NOW), "url must be a str"),  # type: ignore[arg-type]
    (lambda: receive("a=b", "https://h/", now=date(2026, 1, 1)), "now must be a datetime"),  # type: ignore[arg-type]
    (lambda: receive("a=b", "https://h/", now=NOW, cross_site=None), "cross_site must be a bool"),  # type: ignore[arg-type]
    (lambda: receive("a=b", "https://h/", now=NOW, is_public_suffix=1), "a callable"),  # type: ignore[arg-type]
]  # fmt: skip


@pytest.mark.parametrize(("call", "message"), WRONG_TYPES)
def test_wrong_argument_types_raise_type_error(call: typing.Any, message: str) -> None:
    with pytest.raises(TypeError, match=message.replace("(", r"\(").replace(")", r"\)")):
        call()


def test_stored_cookie_methods_check_their_arguments() -> None:
    stored = receive("a=b; Max-Age=5", "https://h.test/", now=NOW)
    with pytest.raises(TypeError, match="now must be a datetime"):
        stored.is_expired(NOW.date())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="aware"):
        stored.is_expired(datetime(2026, 10, 13))
    with pytest.raises(ValueError, match="aware"):
        receive("a=b", "https://h/", now=datetime(2026, 10, 13))
    with pytest.raises(TypeError, match="url must be a str"):
        stored.matches(b"https://h.test/")  # type: ignore[arg-type]
    with pytest.raises(CookieError, match="malformed"):
        stored.matches("https://[::1/")
    with pytest.raises(CookieError, match="no host"):
        stored.matches("file:///etc")


SECRET = "TOPSECRET" * 20000  # a cookie value or URL part that must never be quoted
LONG = "n" * 100000  # any other argument: quoted at most in part


@pytest.mark.parametrize(
    "call",
    [
        lambda: parse(f"sid={SECRET}\x00"),
        lambda: parse(f"sid={SECRET}\x7f; Path=/"),
        lambda: parse(f"sid={SECRET} x", strict=True),
        lambda: parse(f"sid=a{SECRET[:9]} b", strict=True),
        lambda: parse(f"{SECRET}; Path=/\x01"),
        lambda: build("sid", f"{SECRET}\r\n"),
        lambda: build("sid", f'"{SECRET}'),
        lambda: receive(f"sid={SECRET}; Secure", f"http://h.test/?t={SECRET}", now=NOW),
        lambda: receive("sid=1", f"https://[::1/?t={SECRET}", now=NOW),
        lambda: receive("sid=1", f"https:///?t={SECRET}", now=NOW),
        lambda: receive(f"sid={SECRET}; SameSite=None", "https://h.test/", now=NOW),
        lambda: receive(f"sid={SECRET}", "https://h.test/", now=NOW, cross_site=True),
    ],
)
def test_messages_never_quote_a_cookie_value_or_a_url(call: typing.Any) -> None:
    with pytest.raises(CookieError) as caught:
        call()
    assert "TOPSECRET" not in str(caught.value)
    assert len(str(caught.value)) < 200, str(caught.value)


@pytest.mark.parametrize(
    "call",
    [
        lambda: parse(f"sid=1; Expires={LONG[:1000]}", strict=True),
        lambda: parse(f"sid=1; {LONG}\x01=1", strict=True),
        lambda: parse(f"sid=1; Max-Age={LONG[:1000]}", strict=True),
        lambda: parse(f"sid=1; Domain={LONG[:1000]}_", strict=True),
        lambda: parse(f"sid=1; Path=/{LONG[:1000]}\u00e9", strict=True),
        lambda: parse(f"sid=1; SameSite={LONG[:1000]}", strict=True),
        lambda: parse(f"sid=1; Path={LONG}", strict=True),
        lambda: parse(f"s{LONG} =1", strict=True),
        lambda: build(f"s{LONG} ", "v"),
        lambda: build("sid", "v", domain=f"{LONG};"),
        lambda: build("sid", "v", path=f"/{LONG};"),
        lambda: build("sid", "v", path=LONG),
        lambda: build("sid", "v", same_site=LONG),  # type: ignore[arg-type]
        lambda: build("sid", "v", extensions=[(f"{LONG};", None)]),
        lambda: build("sid", "v", extensions=[("x", f"{LONG}\n")]),
        lambda: build("sid", "v", extensions=[(LONG, f" {LONG}")]),
        lambda: build("sid", "v", extensions=[("x", LONG)]),
        lambda: receive(f"sid=1; Domain={LONG[:1000]}.test", "https://h.test/", now=NOW),
        lambda: receive("sid=1; Domain=\u00e9.test", f"https://{LONG[:60]}.test/", now=NOW),
        lambda: receive("sid=1", f"https://xn--{LONG[:60]}.de/", now=NOW),
    ],
)
def test_messages_stay_short_whatever_the_input(call: typing.Any) -> None:
    with pytest.raises(CookieError) as caught:
        call()
    assert len(str(caught.value)) < 200, str(caught.value)


def test_the_expiry_is_clamped_at_the_end_of_the_calendar() -> None:
    late = datetime.max.replace(tzinfo=timezone.utc)
    stored = receive("a=b; Max-Age=60", "https://h.test/", now=late)
    assert stored.expiry == late
    stored = receive("a=b; Expires=Fri, 31 Dec 9999 23:59:59 GMT", "https://h.test/", now=late)
    assert stored.expiry == datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

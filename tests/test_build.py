from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from setcookie import CookieError, build, expire, parse


def test_build_minimal_pair_keeps_the_default_path() -> None:
    assert build("sid", "abc") == "sid=abc; Path=/"


def test_build_without_a_path_omits_the_attribute() -> None:
    assert build("sid", "abc", path=None) == "sid=abc"


def test_build_full_header_orders_attributes() -> None:
    header = build(
        "sid",
        "abc",
        max_age=3600,
        domain="example.com",
        path="/app",
        secure=True,
        http_only=True,
        same_site="None",
        partitioned=True,
        expires=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        extensions=[("Priority", "High"), ("x-flag", None)],
    )
    assert header == (
        "sid=abc; Expires=Fri, 02 Jan 2026 03:04:05 GMT; Max-Age=3600; "
        "Domain=example.com; Path=/app; Secure; HttpOnly; SameSite=None; Partitioned; "
        "Priority=High; x-flag"
    )


def test_build_formats_expires_in_gmt_from_a_non_utc_zone() -> None:
    moment = datetime(2026, 1, 2, 5, 4, 5, tzinfo=timezone(timedelta(hours=2)))
    header = build("sid", "abc", path=None, expires=moment)
    assert header == "sid=abc; Expires=Fri, 02 Jan 2026 03:04:05 GMT"


def test_build_accepts_quoted_and_empty_values() -> None:
    assert build("sid", '"a b"'.replace(" ", ""), path=None) == 'sid="ab"'
    assert build("sid", "", path=None) == "sid="


@pytest.mark.parametrize(
    "name", ["", "s id", "sid;", "sid=", "s\u00e9", "a\r\nSet-Cookie: x", "a,b", '"a"']
)
def test_build_rejects_names_that_are_not_tokens(name: str) -> None:
    with pytest.raises(CookieError, match="not an HTTP token"):
        build(name, "abc")


@pytest.mark.parametrize(
    "value", ["a b", "a;b", "a,b", "a\\b", '"a', "a\r\nSet-Cookie: x=y", "\u00e9", "a\tb"]
)
def test_build_rejects_values_outside_cookie_octet(value: str) -> None:
    with pytest.raises(CookieError, match="cookie-octet"):
        build("sid", value)


@pytest.mark.parametrize(
    "domain",
    ["", ".example.com", "x.com; Secure", "x.com:443", "ex ample.com", "-x.com", "x-.com", "a..b"],
)
def test_build_rejects_domains_that_are_not_host_names(domain: str) -> None:
    with pytest.raises(CookieError, match="host name"):
        build("sid", "abc", domain=domain)


@pytest.mark.parametrize("path", ["app", "/a;b", "/a\r\nX: y", "/\u00e9", "/" + "p" * 1024])
def test_build_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(CookieError):
        build("sid", "abc", path=path)


@pytest.mark.parametrize("max_age", [0, -3])
def test_build_rejects_max_age_that_is_not_a_positive_int(max_age: int) -> None:
    with pytest.raises(CookieError, match="positive int"):
        build("sid", "abc", max_age=max_age)


@pytest.mark.parametrize("max_age", [True, 1.5, "60"])
def test_build_rejects_max_age_of_the_wrong_type(max_age: object) -> None:
    with pytest.raises(TypeError, match="max_age must be an int or None"):
        build("sid", "abc", max_age=max_age)  # type: ignore[arg-type]


def test_build_rejects_expires_that_user_agents_ignore() -> None:
    with pytest.raises(CookieError, match="1601"):
        build("sid", "abc", expires=datetime(1600, 12, 31, tzinfo=timezone.utc))
    with pytest.raises(TypeError, match="expires must be a datetime or None, got str"):
        build("sid", "abc", expires="tomorrow")  # type: ignore[arg-type]


def test_build_rejects_an_unknown_same_site() -> None:
    with pytest.raises(CookieError, match="same_site"):
        build("sid", "abc", same_site="lax")  # type: ignore[arg-type]


def test_build_enforces_the_size_limits() -> None:
    assert build("n", "v" * 4095, path=None) == "n=" + "v" * 4095
    with pytest.raises(CookieError, match="4096"):
        build("n", "v" * 4096)


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"name": "__Secure-sid"}, "__Secure- cookie needs"),
        ({"name": "__secure-sid"}, "__Secure- cookie needs"),
        ({"name": "__Host-sid"}, "__Host- cookie needs the Secure"),
        ({"name": "__HOST-sid", "secure": True, "path": "/x"}, "Path=/"),
        ({"name": "__Host-sid", "secure": True, "path": None}, "Path=/"),
        ({"name": "__Host-sid", "secure": True, "domain": "a.com"}, "must not have a Domain"),
        ({"name": "sid", "same_site": "None"}, "SameSite=None needs"),
        ({"name": "sid", "partitioned": True}, "Partitioned needs"),
    ],
)
def test_build_enforces_prefix_and_secure_rules(kwargs: dict[str, object], reason: str) -> None:
    options = dict(kwargs)
    name = str(options.pop("name"))
    with pytest.raises(CookieError, match=reason):
        build(name, "abc", **options)  # type: ignore[arg-type]


def test_build_accepts_well_formed_prefixed_cookies() -> None:
    assert build("__Host-sid", "a", secure=True) == "__Host-sid=a; Path=/; Secure"
    assert build("__Secure-sid", "a", secure=True, domain="a.com", path=None).endswith("Secure")


@pytest.mark.parametrize(
    "extension",
    [("", "x"), (" x", "1"), ("a=b", "1"), ("Path", "/"), ("SECURE", None), ("x", " 1"),
     ("x", "a;b"), ("x;y", None), ("x", "\r\n")],
)  # fmt: skip
def test_build_rejects_unsafe_extensions(extension: tuple[str, str | None]) -> None:
    with pytest.raises(CookieError):
        build("sid", "abc", extensions=[extension])


def test_build_refuses_non_string_arguments() -> None:
    with pytest.raises(TypeError, match="name must be a str, got int"):
        build(1, "abc")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="value must be a str, got NoneType"):
        build("sid", None)  # type: ignore[arg-type]


def test_expire_writes_a_past_expires_and_an_empty_value() -> None:
    assert expire("sid") == "sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/"
    header = expire("__Host-sid", secure=True)
    assert parse(header, strict=True).expires == datetime(1970, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(CookieError):
        expire("__Host-sid")


def test_build_error_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        build("", "abc")

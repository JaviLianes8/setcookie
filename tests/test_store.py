"""The storage model of section 5.7 for one cookie (cases written by hand)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from setcookie import CookieError, StoredCookie, receive

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
CAP = NOW + timedelta(days=400)


def get(line: str, url: str = "https://www.example.com/a/b", **options: object) -> StoredCookie:
    return receive(line, url, now=NOW, **options)  # type: ignore[arg-type]


def test_a_plain_cookie_is_host_only_with_the_default_path() -> None:
    cookie = get("sid=abc")
    assert (cookie.domain, cookie.host_only, cookie.path) == ("www.example.com", True, "/a")
    assert not cookie.persistent and cookie.expiry is None


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://h.test", "/"),
        ("https://h.test/", "/"),
        ("https://h.test/a", "/"),
        ("https://h.test/a/", "/a"),
        ("https://h.test/a/b/c?q=/x", "/a/b"),
    ],
)
def test_default_path_is_the_request_directory(url: str, expected: str) -> None:
    assert get("sid=a", url).path == expected
    assert get("sid=a; Path=relative", url).path == expected


def test_a_domain_attribute_widens_the_cookie() -> None:
    cookie = get("sid=a; Domain=.EXAMPLE.com")
    assert (cookie.domain, cookie.host_only) == ("example.com", False)


@pytest.mark.parametrize(
    "domain", ["other.com", "ww.example.com", "xample.com", "a.www.example.com"]
)
def test_a_domain_that_does_not_match_the_host_is_rejected(domain: str) -> None:
    with pytest.raises(CookieError, match="domain-match"):
        get(f"sid=a; Domain={domain}")


def test_an_ip_host_matches_only_itself() -> None:
    assert get("sid=a; Domain=10.0.0.1", "http://10.0.0.1/").domain == "10.0.0.1"
    with pytest.raises(CookieError):
        get("sid=a; Domain=0.0.1", "http://10.0.0.1/")


def test_a_non_ascii_domain_attribute_is_rejected() -> None:
    with pytest.raises(CookieError, match="not ASCII"):
        get("sid=a; Domain=\u00e9xample.com")


def test_a_domain_that_only_folds_to_ascii_is_rejected() -> None:
    with pytest.raises(CookieError, match="not ASCII"):
        get("sid=a; Domain=\u212a.com", "https://k.com/")


def test_the_public_suffix_hook() -> None:
    def suffix(domain: str) -> bool:
        return domain in {"com", "example.com"}

    with pytest.raises(CookieError, match="public suffix"):
        get("sid=a; Domain=com", is_public_suffix=suffix)
    cookie = get("sid=a; Domain=example.com", "https://example.com/", is_public_suffix=suffix)
    assert (cookie.domain, cookie.host_only) == ("example.com", True)


def test_a_secure_cookie_needs_a_secure_url() -> None:
    assert get("sid=a; Secure").secure
    assert get("sid=a; Secure", "wss://www.example.com/").secure
    with pytest.raises(CookieError, match="insecure"):
        get("sid=a; Secure", "http://www.example.com/")


def test_same_site_none_and_partitioned_need_secure() -> None:
    assert get("sid=a; SameSite=None; Secure; Partitioned").partitioned
    for line in ("sid=a; SameSite=None", "sid=a; Partitioned"):
        with pytest.raises(CookieError, match="needs the Secure"):
            get(line)


def test_a_cross_site_request_sets_only_same_site_none() -> None:
    assert get("sid=a; SameSite=None; Secure", cross_site=True).same_site == "None"
    for line in ("sid=a", "sid=a; SameSite=Lax", "sid=a; SameSite=Strict; Secure"):
        with pytest.raises(CookieError, match="cross-site"):
            get(line, cross_site=True)


# The accepted and rejected lines below are derived by hand from the loops of
# web-platform-tests cookies/prefix/__host.header.https.html and __secure.header.https.html.
@pytest.mark.parametrize("prefix", ["__Host-", "__HoSt-", "__host-"])
@pytest.mark.parametrize("extra", ["", "Max-Age=10", "HttpOnly"])
def test_host_prefix_rules(prefix: str, extra: str) -> None:
    assert get(f"{prefix}x=1; Secure; Path=/; {extra}").host_only
    for params in ("Path=/", "Secure; Path=/; Domain=www.example.com", "Secure", "Secure; Path=/a"):
        with pytest.raises(CookieError, match="__Host-"):
            get(f"{prefix}x=1; {params}; {extra}")
    # An empty Path still counts as a Path attribute; at "/" the default path is "/".
    assert get(f"{prefix}x=1; Secure; Path=; {extra}", "https://www.example.com/").path == "/"


@pytest.mark.parametrize("prefix", ["__Secure-", "__SeCuRe-", "__SECURE-"])
def test_secure_prefix_rules(prefix: str) -> None:
    assert get(f"{prefix}x=1; Secure; Domain=example.com").secure
    with pytest.raises(CookieError, match="__Secure-"):
        get(f"{prefix}x=1; Domain=example.com")


@pytest.mark.parametrize("value", ["__Secure-abc=1", "__Host-abc", "__SeCuRe-x", "__HoSt-y=2"])
def test_a_nameless_cookie_cannot_pose_as_a_prefix(value: str) -> None:
    with pytest.raises(CookieError, match="nameless"):
        get(f"={value}; Secure; Path=/")
    with pytest.raises(CookieError, match="nameless"):
        get(f"{value.replace('=', '')}; Secure; Path=/")


def test_max_age_wins_over_expires_and_is_capped_at_400_days() -> None:
    assert get(
        "sid=a; Max-Age=60; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
    ).expiry == NOW + timedelta(seconds=60)
    assert get("sid=a; Max-Age=999999999999999999999").expiry == CAP
    assert get("sid=a; Expires=Fri, 01 Jan 9999 00:00:00 GMT").expiry == CAP
    assert get("sid=a; Expires=Fri, 01 Jan 2027 00:00:00 GMT").expiry == datetime(
        2027, 1, 1, tzinfo=timezone.utc
    )


def test_max_age_zero_or_below_expires_at_once() -> None:
    for line in ("sid=a; Max-Age=0", "sid=a; Max-Age=-5", "sid=a; Expires=Thu, 10 Apr 1980 0:0:0"):
        cookie = get(line)
        assert cookie.persistent and cookie.is_expired(NOW)
    assert get("sid=a; Max-Age=0").expiry == datetime.min.replace(tzinfo=timezone.utc)
    assert not get("sid=a; Max-Age=1").is_expired(NOW)
    assert get("sid=a; Max-Age=1").is_expired(NOW + timedelta(seconds=1))
    assert not get("sid=a").is_expired(NOW)


def test_matches_checks_host_path_and_scheme() -> None:
    host_only = get("sid=a; Path=/docs")
    assert host_only.matches("https://www.example.com/docs")
    assert host_only.matches("https://www.example.com/docs/x")
    assert not host_only.matches("https://www.example.com/docsx")
    assert not host_only.matches("https://a.www.example.com/docs")
    wide = get("sid=a; Domain=example.com; Path=/; Secure")
    assert wide.matches("https://a.b.example.com/")
    assert wide.matches("https://example.com")
    assert not wide.matches("http://example.com/")
    assert not wide.matches("https://badexample.com/")
    assert get("sid=a; Path=/a/").matches("https://www.example.com/a/b")


def test_receive_needs_an_aware_now_and_a_host() -> None:
    with pytest.raises(ValueError, match="aware"):
        receive("sid=a", "https://h.test/", now=datetime(2026, 1, 1))
    with pytest.raises(CookieError, match="no host"):
        receive("sid=a", "file:///tmp/x", now=NOW)
    with pytest.raises(CookieError, match="canonicalized"):
        receive("sid=a", "https://a..b/", now=NOW)


def test_receive_canonicalizes_an_internationalized_host() -> None:
    assert get("sid=a", "https://B\u00fccher.Example/").domain == "xn--bcher-kva.example"

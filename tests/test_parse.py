from __future__ import annotations

from datetime import datetime, timezone

import pytest

from setcookie import Cookie, CookieError, parse


def test_parse_minimal_pair() -> None:
    cookie = parse("sid=abc")
    assert (cookie.name, cookie.value, cookie.path) == ("sid", "abc", None)


def test_parse_reads_every_attribute() -> None:
    cookie = parse(
        "sid=abc; Expires=Fri, 02 Jan 2026 03:04:05 GMT; Max-Age=3600; "
        "Domain=example.com; Path=/app; Secure; HttpOnly; SameSite=Strict; Partitioned"
    )
    assert cookie == Cookie(
        name="sid",
        value="abc",
        expires=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        max_age=3600,
        domain="example.com",
        path="/app",
        secure=True,
        http_only=True,
        same_site="Strict",
        partitioned=True,
    )


def test_parse_is_case_insensitive_on_attribute_names() -> None:
    cookie = parse("sid=abc; secure; HTTPONLY; samesite=lax; max-age=10; PARTITIONED")
    assert cookie.secure and cookie.http_only and cookie.partitioned
    assert (cookie.same_site, cookie.max_age) == ("Lax", 10)


def test_domain_lower_casing_is_ascii_only() -> None:
    # U+212A KELVIN SIGN lower-cases to "k" under Unicode rules; it must stay as written.
    assert parse("sid=a; Domain=\u212aX.com").domain == "\u212ax.com"


def test_a_pair_without_equals_is_a_nameless_cookie() -> None:
    cookie = parse("test7; Path=/")
    assert (cookie.name, cookie.value, cookie.path) == ("", "test7", "/")


def test_only_the_first_equals_splits_name_and_value() -> None:
    assert (parse("a==b=c").name, parse("a==b=c").value) == ("a", "=b=c")
    assert (parse("=x=1").name, parse("=x=1").value) == ("", "x=1")


def test_whitespace_trimming_is_wsp_only() -> None:
    cookie = parse(" \tsid \t= \tabc \t; Path=/")
    assert (cookie.name, cookie.value) == ("sid", "abc")
    assert parse("sid=abc\u00a0").value == "abc\u00a0"


def test_an_empty_name_and_empty_value_is_rejected() -> None:
    for line in ("", "=", " = ; Path=/", "; Secure"):
        with pytest.raises(CookieError, match="empty name"):
            parse(line)


@pytest.mark.parametrize("code", [*range(0x00, 0x09), *range(0x0A, 0x20), 0x7F])
def test_control_characters_other_than_tab_reject_the_line(code: int) -> None:
    with pytest.raises(CookieError, match="control character"):
        parse(f"sid=a{chr(code)}b")
    with pytest.raises(CookieError, match="control character"):
        parse(f"sid=ab; Path=/{chr(code)}")


def test_a_tab_inside_the_value_is_kept() -> None:
    assert parse("sid=a\tb").value == "a\tb"


def test_name_and_value_size_limit_is_4096_octets() -> None:
    assert parse("n=" + "v" * 4095).value == "v" * 4095
    with pytest.raises(CookieError, match="4096"):
        parse("n=" + "v" * 4096)
    with pytest.raises(CookieError, match="4096"):
        parse("n=" + "\u00e9" * 2048)


def test_attribute_values_longer_than_1024_octets_are_skipped() -> None:
    assert parse("sid=a; Path=/" + "p" * 1023).path == "/" + "p" * 1023
    assert parse("sid=a; Path=/x; Path=/" + "p" * 1024).path == "/x"


def test_the_last_attribute_of_each_kind_wins() -> None:
    cookie = parse("sid=a; Path=/a; Path=/b; Max-Age=1; Max-Age=2; Domain=x.com; Domain=y.com")
    assert (cookie.path, cookie.max_age, cookie.domain) == ("/b", 2, "y.com")


def test_an_invalid_repeat_keeps_the_earlier_value() -> None:
    cookie = parse(
        "sid=a; Max-Age=5; Max-Age=soon; Expires=Fri, 02 Jan 2026 03:04:05 GMT; Expires=x"
    )
    assert cookie.max_age == 5
    assert cookie.expires == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("raw", ["+5", "1_0", "5 0", "50,399", "", "-", "5.0", "\uff15", "--5"])
def test_max_age_accepts_only_ascii_digits_with_an_optional_minus(raw: str) -> None:
    assert parse(f"sid=a; Max-Age={raw}").max_age is None


def test_max_age_keeps_zero_and_negative_values() -> None:
    assert parse("sid=a; Max-Age=0").max_age == 0
    assert parse("sid=a; Max-Age=-20").max_age == -20
    assert parse("sid=a; Max-Age=007").max_age == 7


def test_domain_drops_one_leading_dot_and_lower_cases() -> None:
    assert parse("sid=a; Domain=.Example.COM").domain == "example.com"
    assert parse("sid=a; Domain=..x.com").domain == ".x.com"


def test_an_empty_domain_resets_to_host_only() -> None:
    assert parse("sid=a; Domain=x.com; Domain=").domain is None
    assert parse("sid=a; Domain=.").domain is None


def test_an_empty_or_relative_path_means_the_default_path() -> None:
    assert parse("sid=a; Path=qux").path == ""
    assert parse("sid=a; Path=").path == ""
    assert parse("sid=a; Path").path == ""
    assert parse("sid=a; Path=/dog; Path=").path == ""


def test_an_unknown_same_site_value_resets_to_default() -> None:
    assert parse("sid=a; SameSite=Lax; SameSite=bogus").same_site is None
    assert parse("sid=a; SameSite=NONE").same_site == "None"


def test_flags_ignore_any_value_but_not_extra_words() -> None:
    assert parse("sid=a; Secure=no").secure
    assert not parse("sid=a; Secure qux").secure
    assert not parse('sid=a; "Secure"').secure


def test_unknown_attributes_are_kept_in_order() -> None:
    cookie = parse("sid=a; Priority=High; lol; x=; ;; =y")
    assert cookie.extensions == (("Priority", "High"), ("lol", None), ("x", ""))


def test_percent_encoding_is_not_decoded() -> None:
    cookie = parse("%74est=%32%33")
    assert (cookie.name, cookie.value) == ("%74est", "%32%33")


def test_parse_refuses_bytes() -> None:
    with pytest.raises(TypeError):
        parse(b"sid=a")  # type: ignore[arg-type]

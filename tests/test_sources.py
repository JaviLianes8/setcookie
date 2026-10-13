"""Check the library against RFC 6265, draft-ietf-httpbis-rfc6265bis-22 and the CHIPS draft.

The files are read from tests/upstream (URL, size and sha256 in MANIFEST.json); the tests
that read them skip until `python scripts/fetch_upstream.py` has fetched them.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from setcookie import CookieError, parse, parse_date, receive
from setcookie._chars import AV_OCTET, COOKIE_OCTET, MAX_AGE_LIMIT
from setcookie._dates import _is_delimiter

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


def _abnf(rule: str) -> set[int]:
    """Expand an ABNF alternation of %xNN and %xNN-NN terms into code points."""
    codes: set[int] = set()
    for term in re.findall(r"%x([0-9A-Fa-f]+)(?:-([0-9A-Fa-f]+))?", rule):
        low = int(term[0], 16)
        codes |= set(range(low, int(term[1] or term[0], 16) + 1))
    return codes


def _rule(text: str, name: str) -> str:
    match = re.search(rf"^\s*{re.escape(name)}\s+= ([^;\n]+)", text, flags=re.MULTILINE)
    assert match is not None, name
    return match.group(1)


def _section(text: str, start: str, end: str) -> str:
    return text.split(start)[-1].split(end)[0]


def test_cookie_octet_matches_the_draft(draft: str) -> None:
    assert {ord(c) for c in COOKIE_OCTET} == _abnf(_rule(draft, "cookie-octet"))


def test_av_octet_matches_the_draft(draft: str) -> None:
    assert {ord(c) for c in AV_OCTET} == _abnf(_rule(draft, "av-octet"))


def test_date_delimiters_match_section_5_1_1(draft: str) -> None:
    expected = _abnf(_rule(draft, "delimiter"))
    assert {code for code in range(256) if _is_delimiter(chr(code))} == expected


def test_the_lifetime_cap_is_the_400_days_of_section_5_5(draft: str) -> None:
    days, seconds = re.findall(r"(\d+)\s+days\s+\((\d+)\s+seconds\)", draft)[0]
    assert int(seconds) == MAX_AGE_LIMIT == int(days) * 86400


def test_size_limits_follow_section_5_6(draft: str) -> None:
    section = _section(draft, "5.6.  The Set-Cookie Header Field", "5.6.1.  The Expires")
    pair = re.search(r"value string\s+is more than (\d+) octets", section)
    attribute = re.search(r"attribute-value is longer than (\d+) octets", section)
    assert pair is not None and attribute is not None
    limit, cap = int(pair.group(1)), int(attribute.group(1))
    assert parse("n=" + "v" * (limit - 1)).value
    with pytest.raises(CookieError):
        parse("n=" + "v" * limit)
    assert parse("n=v; Path=/" + "p" * (cap - 1)).path
    assert parse("n=v; Path=/" + "p" * cap).path is None


def test_the_year_floor_follows_section_5_1_1(draft: str) -> None:
    floor = re.search(r"year-value is less than (\d+)", draft)
    assert floor is not None
    year = int(floor.group(1))
    assert parse_date(f"01 Jan {year} 00:00:00") is not None
    assert parse_date(f"31 Dec {year - 1} 23:59:59") is None


def test_the_prefix_examples_of_section_5_4(draft: str) -> None:
    section = _section(draft, "5.4.  Cookie Name Prefixes", "5.5.  Cookie Lifetime")
    rejected, accepted = section.split("Whereas the following")
    rejected = re.split(r"would be\s+rejected", rejected)[-1]
    rejected_lines = re.findall(r"Set-Cookie: (.+)", rejected)
    accepted_lines = re.findall(r"Set-Cookie: (.+)", accepted)
    assert (len(rejected_lines), len(accepted_lines)) == (10, 6)
    for line in rejected_lines:
        with pytest.raises(CookieError):
            receive(line, "https://site.example/", now=NOW)
        with pytest.raises(CookieError):
            parse(line, strict=True)
    for line in accepted_lines:
        assert receive(line, "https://site.example/", now=NOW).name == line.split("=")[0]
        assert parse(line, strict=True).secure


@pytest.mark.parametrize(
    ("fixture", "end"), [("rfc6265", "4.  Server Requirements"), ("draft", "3.2.  ")]
)
def test_the_examples_of_section_3_1_follow_the_grammar(
    fixture: str, end: str, request: pytest.FixtureRequest
) -> None:
    text: str = request.getfixturevalue(fixture)
    lines = re.findall(r"Set-Cookie: (.+)", _section(text, "3.1.  Examples", end))
    assert len(lines) >= 6
    for line in lines:
        assert parse(line, strict=True) == parse(line)


def test_partitioned_requires_secure_as_the_chips_draft_says(chips: str) -> None:
    assert re.search(r'"Partitioned" and the secure-only-flag is\s+\|?\s*false, abort', chips)
    with pytest.raises(CookieError, match="Partitioned"):
        receive("a=b; Partitioned", "https://site.example/", now=NOW)
    assert receive("a=b; Partitioned; Secure", "https://site.example/", now=NOW).partitioned

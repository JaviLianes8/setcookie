"""Cookie dates: the parsing algorithm of section 5.1.1 and IMF-fixdate output."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from ._errors import type_error

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip
_LOWER_MONTHS = tuple(month.lower() for month in _MONTHS)

# The productions of section 5.1.1; [0-9] rather than \d so no non-ASCII digit matches.
_TIME = re.compile(r"([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2})(?:[^0-9].*)?", re.DOTALL)
_DAY = re.compile(r"([0-9]{1,2})(?:[^0-9].*)?", re.DOTALL)
_YEAR = re.compile(r"([0-9]{2,4})(?:[^0-9].*)?", re.DOTALL)
_FIXDATE = re.compile(
    r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([0-9]{2}) "
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) ([0-9]{4}) "
    r"([0-9]{2}):([0-9]{2}):([0-9]{2}) GMT"
)


def _is_delimiter(char: str) -> bool:
    code = ord(char)
    return (
        code == 0x09
        or 0x20 <= code <= 0x2F
        or 0x3B <= code <= 0x40
        or 0x5B <= code <= 0x60
        or 0x7B <= code <= 0x7E
    )


def _tokens(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in text:
        if _is_delimiter(char):
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))
    return tokens


def parse_date(text: str) -> datetime | None:
    """Parse a cookie-date with the algorithm of section 5.1.1; None when it fails.

    The result is an aware datetime in UTC. Zone names and offsets are not read: the
    algorithm treats every time as UTC. A ``text`` that is not a str raises TypeError.

    >>> print(parse_date("Wed, 09 Jun 2021 10:18:14 GMT"))
    2021-06-09 10:18:14+00:00
    >>> print(parse_date("Fri Jan 01 2038 00:00:00 +0200"))
    2038-01-01 00:00:00+00:00
    >>> print(parse_date("1-Jan-70 0:0:0"))
    1970-01-01 00:00:00+00:00
    >>> print(parse_date("31 Feb 2030 00:00:00"), parse_date("01 Jan 1600 00:00:00"))
    None None
    """
    if not isinstance(text, str):
        raise type_error("text", "a str", text)
    text = str.__str__(text)  # a subclass cannot change what the algorithm reads
    time: tuple[int, int, int] | None = None
    day: int | None = None
    month: int | None = None
    year: int | None = None
    for token in _tokens(text):
        if time is None and (match := _TIME.fullmatch(token)):
            time = (int(match[1]), int(match[2]), int(match[3]))
        elif day is None and (match := _DAY.fullmatch(token)):
            day = int(match[1])
        elif month is None and token[:3].isascii() and token[:3].lower() in _LOWER_MONTHS:
            month = _LOWER_MONTHS.index(token[:3].lower()) + 1
        elif year is None and (match := _YEAR.fullmatch(token)):
            year = int(match[1])
    if time is None or day is None or month is None or year is None:
        return None
    if 70 <= year <= 99:
        year += 1900
    elif 0 <= year <= 69:
        year += 2000
    hour, minute, second = time
    if not 1 <= day <= 31 or year < 1601 or hour > 23 or minute > 59 or second > 59:
        return None
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    except ValueError:
        return None


def fixdate_problem(text: str) -> str | None:
    """Why ``text`` is not an IMF-fixdate of a real moment, or None when it is one."""
    if _FIXDATE.fullmatch(text) is None:
        return "is not an IMF-fixdate"
    if parse_fixdate(text) is None:
        return "is an IMF-fixdate of a moment that does not exist"
    return None


def parse_fixdate(text: str) -> datetime | None:
    """Parse an exact IMF-fixdate (RFC 9110 section 5.6.7); None for anything else.

    Only the grammar and the calendar are checked, not that the day name fits the date:
    the draft's own example in section 3.1 pairs "Wed" with 9 June 2026, a Tuesday.
    The grammar allows a leap second, 23:59:60, which is read as 23:59:59.
    """
    match = _FIXDATE.fullmatch(text)
    if match is None:
        return None
    leap = match.group(5, 6, 7) == ("23", "59", "60")
    try:
        moment = datetime(
            int(match[4]),
            _MONTHS.index(match[3]) + 1,
            int(match[2]),
            int(match[5]),
            int(match[6]),
            59 if leap else int(match[7]),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None
    return moment


def format_http_date(value: datetime) -> str:
    """Render a datetime as an IMF-fixdate in GMT, regardless of locale.

    A naive datetime, including one whose tzinfo gives no offset, is taken to be UTC.
    """
    naive = value.utcoffset() is None
    moment = value.replace(tzinfo=timezone.utc) if naive else value
    moment = moment.astimezone(timezone.utc)
    return (
        f"{_DAYS[moment.weekday()]}, "
        f"{moment.day:02d} {_MONTHS[moment.month - 1]} {moment.year:04d} "
        f"{moment.hour:02d}:{moment.minute:02d}:{moment.second:02d} GMT"
    )


parse_date.__module__ = "setcookie"

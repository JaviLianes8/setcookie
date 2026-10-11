"""Locale-independent HTTP-date formatting and tolerant parsing."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip


def format_http_date(value: datetime) -> str:
    """Render a datetime as an RFC 7231 IMF-fixdate in GMT, regardless of locale."""
    moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return (
        f"{_DAYS[moment.weekday()]}, "
        f"{moment.day:02d} {_MONTHS[moment.month - 1]} {moment.year:04d} "
        f"{moment.hour:02d}:{moment.minute:02d}:{moment.second:02d} GMT"
    )


def parse_http_date(text: str) -> datetime | None:
    """Parse an HTTP date tolerantly, returning None when it cannot be understood."""
    try:
        parsed = parsedate_to_datetime(text.strip())
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

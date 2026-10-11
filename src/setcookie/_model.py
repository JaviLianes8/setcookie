"""Typed representation of a single Set-Cookie header."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SameSite = Literal["Lax", "Strict", "None"]


@dataclass(frozen=True)
class Cookie:
    """One Set-Cookie header decomposed into its name, value and attributes."""

    name: str
    value: str
    expires: datetime | None = None
    max_age: int | None = None
    domain: str | None = None
    path: str | None = None
    secure: bool = False
    http_only: bool = False
    same_site: SameSite | None = None

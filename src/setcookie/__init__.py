"""Typed Set-Cookie codec: parse, validate and build one Set-Cookie line, and store it.

``SameSite`` is the type of the SameSite attribute, ``Literal["Lax", "Strict", "None"]``:
`parse` reads any spelling into one of the three, and `build` takes exactly one of them.

>>> from setcookie import SameSite, build, parse
>>> policy: SameSite = "Strict"
>>> parse(build("sid", "abc", same_site=policy)).same_site
'Strict'
>>> parse("sid=abc; SameSite=NONE; Secure").same_site
'None'
"""

from __future__ import annotations

from ._build import build, expire
from ._dates import parse_date
from ._errors import CookieError
from ._model import Cookie, SameSite, StoredCookie
from ._parse import parse
from ._store import receive

__version__ = "1.0.0"

__all__ = [
    "Cookie",
    "CookieError",
    "SameSite",
    "StoredCookie",
    "build",
    "expire",
    "parse",
    "parse_date",
    "receive",
]

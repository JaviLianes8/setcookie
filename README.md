# setcookie

Typed single-line Set-Cookie codec: parse and build one Set-Cookie header per RFC 6265.

## Install

```
pip install setcookie
```

## Usage

```python
from datetime import datetime, timezone

from setcookie import build, parse

header = build(
    "sid",
    "a1b2c3",
    max_age=3600,
    domain="example.com",
    path="/app",
    secure=True,
    http_only=True,
    same_site="Lax",
    expires=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
)
# "sid=a1b2c3; Expires=Fri, 02 Jan 2026 03:04:05 GMT; Max-Age=3600; "
# "Domain=example.com; Path=/app; Secure; HttpOnly; SameSite=Lax"

cookie = parse(header)
cookie.name  # "sid"
cookie.max_age  # 3600
cookie.same_site  # "Lax"
cookie.expires  # datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
cookie.secure  # True
```

`build` returns a string. `parse` returns a frozen `Cookie` with typed fields:
`name`, `value`, `expires` (an aware `datetime` in UTC), `max_age` (`int`), `domain`,
`path`, `secure`, `http_only` and `same_site` (a `Literal["Lax", "Strict", "None"]`).
Attribute names are read case-insensitively, and unknown or malformed attributes are
ignored the way a client would read them. A line with no `name=value` pair raises
`CookieError`.

## Why

The standard library offers `http.cookies.SimpleCookie`, but it is awkward for a single
Set-Cookie line and it is loose with modern attributes: it accepts the comma inside the
`Expires` date as a cookie separator, keeps the date as an unparsed string, and treats
`SameSite` as a free-form key with no notion of the valid values. The other option,
`cookies` by sashahart, has not been released since 2014.

`setcookie` is a small, zero-dependency, fully typed codec for exactly one Set-Cookie
line. It parses into a frozen dataclass, formats `Expires` as a locale-independent RFC
7231 GMT date, models `SameSite` as a `Literal`, and round-trips cleanly between string
and object. Reach for it when you produce or inspect one Set-Cookie header and want a
typed result rather than a legacy container.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

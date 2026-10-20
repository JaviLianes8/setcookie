# setcookie

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Typed Set-Cookie codec for Python: parse one Set-Cookie line the way browsers do, check
it against the server grammar, build lines that cannot inject headers or break prefix
rules, and see what a user agent would store. Zero dependencies.

It follows the current cookie specification, draft-ietf-httpbis-rfc6265bis (revision 22,
the successor of RFC 6265), plus the Partitioned attribute, and is checked against the
web-platform-tests cookie parser cases.

## Install

```
pip install setcookie
```

## Build a header

```python
from setcookie import build, expire

print(build("sid", "a1b2c3", max_age=3600, secure=True, http_only=True, same_site="Lax"))
# sid=a1b2c3; Max-Age=3600; Path=/; Secure; HttpOnly; SameSite=Lax
print(build("__Host-session", "x9", secure=True, partitioned=True, same_site="None"))
# __Host-session=x9; Path=/; Secure; SameSite=None; Partitioned
print(expire("sid"))
# sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/
```

Every argument is checked on its own before it is joined, and anything a user agent
would drop or misread raises `CookieError` (a `ValueError`). Its message names the rule
and the position, never quotes the cookie value, and cuts any other quoted text to 40
characters, so it can go to a log. An argument of the wrong type raises `TypeError`.

```python
from setcookie import CookieError, build

for name, value, options in [
    ("sid", "a\r\nSet-Cookie: admin=1", {}),
    ("sid", "abc", {"domain": "example.com; Secure"}),
    ("__Host-sid", "abc", {"secure": True, "domain": "example.com"}),
    ("sid", "abc", {"same_site": "None"}),
]:
    try:
        build(name, value, **options)
    except CookieError as error:
        print(error)
# cookie value has U+000D at index 1, outside cookie-octet; encode it first
# domain 'example.com; Secure' is not a host name (no leading dot, no port)
# a __Host- cookie must not have a Domain attribute
# SameSite=None needs the Secure attribute
```

Names must be HTTP tokens and values cookie-octets (encode arbitrary data, for example
with Base64). `max_age` must be a positive int: the grammar has no `Max-Age=0`, so use
`expire` to delete a cookie. `expires` is written as an IMF-fixdate in GMT whatever the
locale or time zone of the datetime; a naive datetime is taken to be UTC, not local time.

## Parse a header

`parse` runs the user agent algorithm: whitespace is trimmed, the last attribute of each
kind wins, malformed attributes are skipped, dates are read with the cookie date
algorithm, and unknown attributes are kept.

```python
from setcookie import parse

cookie = parse(
    "sid=abc; expires=Fri Jan 01 2038 00:00:00 GMT; Domain=.Example.com; "
    "Max-Age=+5; samesite=lax; Priority=High"
)
print(cookie.expires, cookie.domain, cookie.max_age, cookie.same_site)
# 2038-01-01 00:00:00+00:00 example.com None Lax
print(cookie.extensions)
# (('Priority', 'High'),)
print(parse("nameless").name == "", parse("nameless").value)
# True nameless
```

A line a user agent ignores entirely (a control character, an empty name and value, a
name and value over 4096 octets) raises `CookieError`. With `strict=True` the line must
also follow the server grammar, and the error names the rule:

```python
from setcookie import CookieError, parse

for line in ["sid=a b", "sid=abc; Max-Age=0", "__Secure-id=1", "sid=abc; Path=/; path=/x"]:
    try:
        parse(line, strict=True)
    except CookieError as error:
        print(error)
# strict: the cookie-value has U+0020 at index 1, outside cookie-octet
# strict: Max-Age='0' is not a non-zero-digit followed by DIGITs
# strict: a __Secure- cookie needs the Secure attribute
# strict: the path attribute appears twice
```

## What a browser stores

`receive` runs the storage model for one line received from a URL. It returns a
`StoredCookie` with the resolved domain, path and expiry, or raises `CookieError` with
the rule that makes a user agent ignore the line.

```python
from datetime import datetime, timezone

from setcookie import CookieError, receive

now = datetime(2026, 10, 13, tzinfo=timezone.utc)
stored = receive(
    "sid=1; Domain=example.com; Max-Age=999999999", "https://www.example.com/app/login", now=now
)
print(stored.domain, stored.host_only, stored.path, stored.expiry)
# example.com False /app 2027-11-17 00:00:00+00:00
print(
    stored.matches("https://shop.example.com/app/cart"), stored.matches("https://example.org/app")
)
# True False
try:
    receive("sid=1; Secure", "http://www.example.com/", now=now)
except CookieError as error:
    print(error)
# a Secure cookie cannot be set from an insecure URL
```

Expiry follows Max-Age over Expires and is capped at 400 days. Pass
`is_public_suffix` to reject domains such as `co.uk`, and `cross_site=True` for a
cross-site request that is not a top-level navigation. Rules that need the rest of the
cookie store (overwriting, eviction, secure cookie shadowing) are left to the caller.
Non-ASCII hosts are converted with the standard library's IDNA 2003 codec, which differs
from IDNA 2008 for a few characters. As in browsers, a host with a trailing dot
(`example.com.`) is a host of its own, and a host that ends in a number is read as an
IPv4 address (`127.1` is `127.0.0.1`).

## Command line

```
$ curl -sI https://github.com | setcookie --strict
$ setcookie --url https://www.example.com/app "sid=1; Domain=example.com"
```

`setcookie` reads lines from its arguments or from stdin, as UTF-8, and prints JSON.
Stdin is a header dump when its first non-empty line starts with `HTTP/` or any line is
a `Set-Cookie:` field (as `grep -i set-cookie` prints them); then only the Set-Cookie
fields are read, every other line is ignored, and a dump without one prints `[]`.
`--strict` checks the server grammar, `--url` adds what a user agent would store, `--now`
fixes the clock. The exit status is 1 when any line is refused and 2 when there is no
input at all. `python -m setcookie` works too.

## API

| Name | What it does |
| --- | --- |
| `build(name, value, *, expires, max_age, domain, path="/", secure, http_only, same_site, partitioned, extensions)` | One safe Set-Cookie line |
| `expire(name, *, domain, path="/", secure, ...)` | A line that deletes the cookie |
| `parse(line, *, strict=False)` | A frozen `Cookie`, read the way user agents read it |
| `receive(line, url, *, now, cross_site=False, is_public_suffix=None)` | The `StoredCookie` a user agent keeps |
| `parse_date(text)` | The cookie date algorithm, an aware UTC datetime or `None` |
| `Cookie` | Name, value, attributes, `extensions`, and `header()` to render it again |
| `StoredCookie` | Domain, path, flags, expiry, `is_expired(now)` and `matches(url)` |
| `SameSite` | `Literal["Lax", "Strict", "None"]` |
| `CookieError` | The `ValueError` raised for ignored, ungrammatical or unsafe lines |

## Why

The problem: a Set-Cookie line is easy to write wrong and hard to read right. A value
with a line break injects a header, a `;` in a Domain smuggles an attribute, a `__Host-`
cookie with a Domain or a `SameSite=None` cookie without Secure is silently dropped by
browsers, and the date and attribute rules browsers apply are not the ones most code
guesses. The alternatives in Python, checked on 2026-10-20:

- `http.cookies.SimpleCookie` (standard library, Python 3.10 to 3.14) was written for the
  old Cookie header, not for one Set-Cookie line: it keeps `Expires` as a string, keeps
  any `SameSite` value (`Bogus` is read and written back), reads an unknown attribute such
  as `Priority=High` as a second cookie, drops the whole line when it meets a flag it does
  not know (`Foo`, and `Partitioned` before Python 3.14), drops nameless cookies, and
  writes a control character in a value as an octal escape that browsers do not decode.
- `werkzeug.http.dump_cookie` (Werkzeug 3.1.9) builds a line but writes a Domain as given,
  so `domain="ex.com; Secure"` adds a Secure attribute; it writes a `__Host-` cookie with a
  Domain and `SameSite=None` without Secure (both dropped by browsers), and turns a line
  break in a value into an octal escape.
- `http.cookiejar` is a client cookie jar for `urllib`; it does not build lines and has no
  SameSite, Partitioned or prefix rules.

`setcookie` follows the current draft step by step (it is tested against the draft text,
the web-platform-tests cases and two JavaScript implementations), refuses to build what
browsers would drop, and gives typed results. It stays a codec for one line: it is not a
cookie jar, and it has no runtime dependencies.

## More

- [GUIDE](https://github.com/JaviLianes8/setcookie/blob/main/GUIDE.md): every rule, every
  error, and what changed since 0.2.0.
- [CHANGELOG](https://github.com/JaviLianes8/setcookie/blob/main/CHANGELOG.md)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/setcookie/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

# setcookie

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
would drop or misread raises `CookieError` (a `ValueError`):

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
# cookie value 'a\r\nSet-Cookie: admin=1' has characters outside cookie-octet; encode it first
# domain 'example.com; Secure' is not a host name (no leading dot, no port)
# a __Host- cookie must not have a Domain attribute
# SameSite=None needs the Secure attribute
```

Names must be HTTP tokens and values cookie-octets (encode arbitrary data, for example
with Base64). `max_age` must be a positive int: the grammar has no `Max-Age=0`, so use
`expire` to delete a cookie. `expires` is written as an IMF-fixdate in GMT whatever the
locale or time zone of the datetime.

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
# strict: the cookie-value 'a b' has characters outside cookie-octet
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

## Command line

```
$ curl -sI https://example.com | setcookie --strict
$ setcookie --url https://www.example.com/app "sid=1; Domain=example.com"
```

`setcookie` reads lines from its arguments or from stdin (from a header dump only the
Set-Cookie fields are used) and prints JSON. `--strict` checks the server grammar,
`--url` adds what a user agent would store, `--now` fixes the clock. The exit status is
1 when any line is refused. `python -m setcookie` works too.

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

`http.cookies.SimpleCookie` was written for the old Cookie header, not for one
Set-Cookie line: it keeps `Expires` as a string, accepts any `SameSite` value, reads an
unknown attribute such as `Priority=High` as a second cookie, silently drops the whole
line when it meets a flag it does not know (`Partitioned`), drops nameless cookies, and
writes a control character in a value as an octal escape that browsers do not decode.
`setcookie` follows the current draft step by step, refuses to build what browsers would
drop, and gives typed results.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

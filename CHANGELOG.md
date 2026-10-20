# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-20

The public API is now stable: the nine names in `setcookie.__all__`, their parameters,
defaults and the error types below follow Semantic Versioning from this release on.
Every change against 0.2.0 is listed here; the
[GUIDE](https://github.com/JaviLianes8/setcookie/blob/main/GUIDE.md) has the details.

### Changed

- An argument of the wrong type raises `TypeError` instead of `CookieError`: in `build`
  and `expire` a name, value, domain, path or SameSite that is not a `str`, an `expires`
  that is not a `datetime`, a `max_age` that is not an `int` (a `bool` included), a
  `secure`, `http_only` or `partitioned` that is not a `bool`, an extension that is not a
  `(str, str | None)` tuple, or `extensions` given as a string. `parse` also checks that
  `strict` is a `bool`; `parse_date` raises `TypeError` with a clear message for a
  non-string; `receive` checks `line`, `url`, `now`, `cross_site` and `is_public_suffix`;
  `StoredCookie.matches` checks `url`. Values that have the right type but break a rule
  still raise `CookieError`.
- `StoredCookie.is_expired` raises `ValueError` for a naive `now` (it raised the
  comparison `TypeError` before) and `TypeError` for something that is not a datetime.
- Error messages never quote a cookie value, a whole line or a request URL, and cut any
  other quoted text to 40 characters. A bad character is named by code point and index,
  for example `cookie value has U+000D at index 1, outside cookie-octet`.
- `receive` returns the latest representable time as the expiry when `now` plus the
  lifetime does not fit a `datetime`, instead of raising `OverflowError`.
- The request host keeps a trailing dot, as browsers do: `www.example.com.` is a host of
  its own for `receive` and `StoredCookie.matches`, and only a dotted Domain matches it.
  0.2.0 dropped the dot.
- A request host whose last label is a number is read as an IPv4 address the way the
  WHATWG URL parser reads it (`127.1`, `0x7f.0.0.1` and `2130706433` are `127.0.0.1`), so
  the IP rules of domain-match apply; a host such as `1.2.3.4.5` raises `CookieError`.
- A request host the IDNA codec cannot decode raises `CookieError` on every Python
  version; on 3.13 and 3.14 a huge punycode label raised `OverflowError`.
- `build` and `expire` write the plain value of a `str` or `int` subclass: an Enum
  member gives its value, and a subclass with its own `__format__` cannot add text.
- `build` takes an `expires` whose `tzinfo` gives no offset as UTC, like a naive one,
  instead of as local time.
- The command line reads stdin as UTF-8 (a byte order mark skipped, undecodable bytes
  kept as escapes) instead of the locale encoding, and a header dump without any
  Set-Cookie field prints `[]` and exits 0 instead of failing with a usage error.
- `scripts/release.ps1` checks that the version in `pyproject.toml` is not on PyPI yet,
  instead of refusing any name that already exists there.
- `Cookie`, `StoredCookie` and `CookieError` report `setcookie` as their module, so
  their repr, pickles and documentation point at the public name.
- Development status is Production/Stable.

### Added

- A runnable example in the docstring of every public name and method, run as tests.
- GUIDE.md: the parsing, building, strict and storage rules, the full error list, and
  the move from 0.2.0.

## [0.2.0]

### Changed

- `parse` follows the user agent algorithm of draft-ietf-httpbis-rfc6265bis-22: a pair
  without `=` is a nameless cookie instead of an error, only spaces and tabs are trimmed,
  a line with a control character other than tab, an empty name and value, or a name and
  value over 4096 octets raises `CookieError`, attribute values over 1024 octets are
  skipped, and the last valid attribute of each kind wins.
- Expires is read with the cookie date algorithm (any token order, two digit years,
  zones ignored, nothing before 1601). Max-Age accepts only digits with an optional
  leading minus. Domain loses its leading dot and is lower-cased. An empty or relative
  Path reads as `""`, meaning the default path. An unknown SameSite value resets it.
- `build` checks every part before joining it and raises `CookieError` (still a
  `ValueError`) for names that are not tokens, values outside cookie-octet, domains that
  are not host names, relative paths, control characters or `;` in attribute values,
  a `max_age` below 1, Expires before 1601, size limits, broken `__Secure-` and `__Host-`
  prefix rules, and SameSite=None or Partitioned without Secure.

### Added

- `parse(line, strict=True)` checks the server grammar and names the broken rule.
- `Cookie.partitioned`, `Cookie.extensions` for unknown attributes, and `Cookie.header()`.
- `build(partitioned=..., extensions=...)` and `expire()` for deleting a cookie.
- `receive()` runs the storage model for one line and returns a `StoredCookie` with the
  resolved domain, path and expiry (Max-Age over Expires, capped at 400 days), with
  `is_expired()` and `matches(url)`.
- `parse_date()`, the cookie date algorithm.
- The `setcookie` command and `python -m setcookie`: JSON output, `--strict`, `--url`.

## [0.1.0]

- First release.
- `build` assembles one Set-Cookie line from a name, value and the RFC 6265 attributes
  (Expires, Max-Age, Domain, Path, Secure, HttpOnly, SameSite), formatting Expires as a
  locale-independent RFC 7231 GMT date.
- `parse` decodes one Set-Cookie line into a frozen, typed `Cookie`, reading attribute
  names case-insensitively and tolerating unknown or malformed attributes.
- `SameSite` is modelled as a `Literal`, closing the gap left by
  `http.cookies.SimpleCookie`, which mishandles the Expires comma and treats SameSite as
  a free-form value.

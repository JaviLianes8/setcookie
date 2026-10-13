# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

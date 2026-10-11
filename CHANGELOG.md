# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

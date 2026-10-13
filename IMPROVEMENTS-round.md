# setcookie improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 6265 and errata, draft-ietf-httpbis-rfc6265bis-22, the partitioned cookies draft, web-platform-tests cookie parser tests
- [x] Parser on the user agent algorithm (section 5.6): CTL rejection, nameless cookies, WSP trimming, size limits, last attribute wins
- [x] Cookie date algorithm (section 5.1.1) and Max-Age digits (section 5.6.2)
- [x] Strict mode: the server grammar of section 4.1.1 with reasons
- [x] Safe builder: token names, cookie-octet values, attribute guards, prefix, SameSite=None and Partitioned rules, `expire`
- [x] Storage model: `receive` with default-path, domain and path matching, secure origin, prefixes, 400 day cap
- [x] Command line
- [x] Contracts: pinned sources, web-platform-tests corpus, README examples, installed wheel
- [x] Docs and packaging: README, CHANGELOG, metadata, sdist contents
- [x] Gates: ruff format, ruff check, mypy --strict, pytest
- [x] Mutation run: removing guarded logic makes the suite fail
- [x] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `parse`, `build` and a frozen `Cookie`. Probed against the sources below:

- A line with no `=` raises `CookieError`. Section 5.6 step 3 of the draft reads it as a
  nameless cookie whose value is the whole pair (`test7` is a cookie with an empty name).
- Whitespace is trimmed with `str.strip`, so a trailing NO-BREAK SPACE or form feed is
  removed; the algorithm trims WSP only (space and tab).
- CTL characters are kept: `sid=a\x00b` parses. Section 5.6 step 1 ignores the whole line.
- No size limits: a 5000 byte value is accepted by `parse` and written by `build`. The
  draft ignores a cookie whose name plus value exceeds 4096 octets and any attribute whose
  value exceeds 1024 octets.
- Max-Age is read with `int()`: `+5` gives 5 and `1_0` gives 10. Section 5.6.2 accepts
  only DIGITs with an optional leading `-`.
- Expires goes through `email.utils`: a year of 1500 is accepted (the algorithm fails below
  1601) and `+0200` shifts the time by two hours (the algorithm ignores zones, the time is
  UTC).
- Domain is returned as written (`.Example.COM`); section 5.6.3 drops the leading dot and
  lower-cases it. A relative `Path=qux` is kept, where section 5.6.4 falls back to the
  default path.
- `Partitioned` and unknown attributes such as `Priority` are silently dropped.
- `build` writes anything: `a\r\nSet-Cookie: x=y` injects a header, `s id;` is used as a
  name, `Domain=x.com; Secure` smuggles an attribute, `__Host-sid` goes out with a Domain,
  `__Secure-sid` without Secure, `SameSite=None` without Secure, and `Max-Age=-3`.
- No strict validation, no user agent view (where the cookie lands, whether it is
  rejected), no command line.

## Sources (fetched 2026-10-13)

- RFC 6265, https://www.rfc-editor.org/rfc/rfc6265.txt. Errata page
  https://www.rfc-editor.org/errata/rfc6265 read: verified 3444 (path-value and
  extension-av may be empty), 4148 (the trailing part of day-of-month, year and time is
  optional), 6093 and 7604 (Set-Cookie folding and 1xx responses), 5518 (editorial); 3663
  and 8242 held for document update; 8877 reported, about the month production.
- draft-ietf-httpbis-rfc6265bis-22, 1 December 2025, the latest revision listed by
  https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/ (no RFC number yet):
  server grammar (4.1.1), prefixes (4.1.3, 5.4), dates (5.1.1), domain match (5.1.3),
  default path and path match (5.1.4), lifetime cap of 400 days (5.5), the parsing
  algorithm (5.6 to 5.6.7) and the storage model (5.7).
- draft-cutler-httpbis-partitioned-cookies-01, the latest revision on the datatracker:
  the Partitioned attribute (2.3) and its Secure requirement (3.1).
- web-platform-tests at commit 1b67fafba1d46d158b45a831bb604d86c9b5c5a8:
  `cookies/name/name.html`, `cookies/value/value.html`, `cookies/attributes/max-age.html`,
  `invalid.html`, `expires.html`, `path.html` and `cookies/size/name-and-value.html`.
- None of these files is committed. `tests/upstream/MANIFEST.json` records URL, revision,
  size, sha256 and licence; `scripts/fetch_upstream.py` fetches and checks them into the
  ignored `tests/upstream/` folder, and their tests skip while they are absent.

## Ranked improvements

1. **Parser on the user agent algorithm.** Section 5.6 step by step: reject CTLs other
   than HTAB, split at the first `;` and the first `=`, accept nameless cookies, trim WSP
   only, reject name plus value above 4096 octets and empty name with empty value, skip
   attributes above 1024 octets, last attribute of each kind wins, an empty or relative
   Path resets to the default path, Domain loses its leading dot and is lower-cased,
   unknown SameSite values reset to the default. `Partitioned` is read and unknown
   attributes are kept in order in `extensions`.
2. **Cookie dates and Max-Age.** The section 5.1.1 tokenizer with the found flags, the two
   digit year rule, the 1601 floor and calendar validation, exposed as `parse_date`.
   Max-Age accepts DIGITs with an optional leading `-` and nothing else.
3. **Safe builder.** `build` refuses names that are not tokens, values outside
   cookie-octet (optionally in DQUOTEs), domains that are not hostnames, paths that are
   not absolute or contain CTLs or `;`, Max-Age below 1 (the grammar has no zero),
   name plus value above 4096 octets and attribute values above 1024. Prefix rules are
   enforced case-insensitively as user agents do: `__Secure-` needs Secure, `__Host-`
   needs Secure, Path=/ and no Domain. SameSite=None and Partitioned need Secure. `expire`
   writes a deletion line with a past Expires. `parse(build(...), strict=True)` returns the
   same values.
4. **Strict mode.** `parse(line, strict=True)` checks the server grammar of section
   4.1.1 and raises `CookieError` naming the rule: token name, cookie-octet value,
   IMF-fixdate Expires, Max-Age digits, hostname Domain, av-octet Path, flags without a
   value, SameSite values, duplicate attributes, prefixes, SameSite=None and Partitioned
   without Secure, size limits.
5. **Storage model.** `receive(line, url, now=...)` runs section 5.7 for one cookie and
   returns a `StoredCookie` (domain, path, host-only, secure, HttpOnly, SameSite,
   Partitioned, persistent, expiry) or raises `CookieError` with the step that rejected
   it: domain mismatch, secure cookie from an insecure origin, SameSite=None or Partitioned
   without Secure, prefix rules, nameless cookies posing as prefixes, cross-site rules,
   an optional public suffix check. Expiry follows Max-Age over Expires and the 400 day
   cap. `StoredCookie.matches(url)` answers the domain, path and secure checks of the
   retrieval model.
6. **Typed API.** Frozen dataclasses, `SameSite` as a `Literal`, keyword-only options, one
   error type that is a `ValueError`, `py.typed`.
7. **Command line.** `setcookie` reads lines or a `curl -sI` dump and prints the parsed
   cookies as JSON; `--strict` lints them and exits 1 with the reasons; `--url` shows
   what a user agent would store. It fits: checking what a server sends is a shell task.
8. **Contracts.** Character sets and limits are read from the pinned draft, the prefix
   examples of section 5.4 run through `receive`, the web-platform-tests cases run through
   `receive` and a small cookie jar; README examples run; the installed wheel and its
   console script are driven from an empty folder.
9. **Docs and packaging.** README with executed examples and an API table, CHANGELOG,
   keywords and classifiers, an sdist without planning notes or fetched files.

## Out of scope

- A cookie jar with eviction and the Cookie request header: this is a codec for one line.
  Storage model steps 16, 23 and 24 need a store and are left to the caller.
- A bundled public suffix list: `receive` takes a callable instead.
- The `__Http-` and `__Host-Http-` prefixes tested by web-platform-tests: they are not in
  draft 22.

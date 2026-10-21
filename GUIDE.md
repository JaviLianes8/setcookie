# setcookie guide

This guide states what each public name promises. The rules come from
[draft-ietf-httpbis-rfc6265bis-22](https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/)
(the successor of RFC 6265, section numbers below refer to it) and
[draft-cutler-httpbis-partitioned-cookies-01](https://datatracker.ietf.org/doc/draft-cutler-httpbis-partitioned-cookies/)
for the Partitioned attribute.

## Reading a line: `parse(line, *, strict=False)`

`parse` runs the user agent algorithm of section 5.6 and returns a frozen `Cookie`.

- The whole line is ignored, and `CookieError` raised, when it holds a control character
  other than tab (%x00-08, %x0A-1F, %x7F), when the name and the value are both empty, or
  when the name and value are longer than 4096 octets together (UTF-8).
- The pair is split at the first `;`, then at the first `=`. A pair without `=` is a
  nameless cookie: `parse("abc")` has name `""` and value `"abc"`.
- Only spaces and tabs are trimmed, never other whitespace.
- An attribute whose value is longer than 1024 octets is skipped. Attribute names are
  matched without case (A to Z only).
- When an attribute repeats, the last one wins. An unreadable Expires or Max-Age is
  skipped, so an earlier valid one stays; an empty Domain and an unknown SameSite value
  reset the earlier one to `None`.
- Expires is read with the cookie date algorithm (`parse_date`). Max-Age keeps only
  digits with an optional leading `-` (`+5`, `1_0` and ` 5x` are skipped). Domain loses
  one leading dot and is lower-cased. Path is kept when it starts with `/`; an empty or
  relative Path reads as `""`, meaning "use the default path". SameSite is read without
  case into `"Lax"`, `"Strict"` or `"None"`.
- Secure, HttpOnly and Partitioned are flags; anything after `=` is ignored for them.
- Any other attribute goes to `extensions`, in order, as `(name, value)`, with `None`
  when it had no `=`.

`Cookie.header()` renders the cookie with `build`, so it raises `CookieError` for a
cookie a server may not send (a nameless one, for example).

### Strict mode

`parse(line, strict=True)` also checks the server grammar of section 4.1.1 first and
raises `CookieError` with a message that starts with `strict:` and names the first rule
broken: the name is a token, the value is cookie-octets (optionally in one pair of
double quotes), Expires is an IMF-fixdate of a moment that exists, Max-Age is a
non-zero digit followed by digits, Domain is a host name, Path and extensions are av-octets, flags have no value,
SameSite is Strict, Lax or None, no attribute appears twice, no empty attribute, no
trailing whitespace, the size limits, the `__Secure-` and `__Host-` prefix rules, and
Secure on SameSite=None and Partitioned cookies.

Expires is checked in two steps, each with its own message: the text must follow the
IMF-fixdate grammar (`is not an IMF-fixdate`), and the date and time must exist in the
calendar (`is an IMF-fixdate of a moment that does not exist`, for 31 Feb or the year
0000). The day name is not compared with the date. A leap second, `23:59:60`, is
allowed by the grammar and passes, but the cookie date algorithm of section 5.1.1 refuses
a second over 59, so `parse` then reads no Expires at all, as user agents do.

## Dates: `parse_date(text)`

The algorithm of section 5.1.1: the text is cut at delimiters, the first token that
looks like a time, a day, a month and a year is taken, two-digit years 70 to 99 mean
19xx and 0 to 69 mean 20xx, and the date fails (`None`) before 1601, with an hour over
23, a minute or second over 59, or a day that does not exist. Zone names and offsets are
not read: the result is an aware datetime in UTC.

## Writing a line: `build` and `expire`

`build(name, value, *, expires, max_age, domain, path="/", secure, http_only, same_site,
partitioned, extensions)` returns one line that `parse(..., strict=True)` reads back to
the same values, with three exceptions: the Domain reads back lower-cased, Expires is
written to the whole second, so microseconds are dropped, and a naive `expires` (or one
whose `tzinfo` gives no offset) reads back as the same instant, aware, in UTC. A `str` or `int` subclass,
such as an Enum member, is written as the plain value it holds. It writes the attributes in this order: Expires, Max-Age, Domain, Path,
Secure, HttpOnly, SameSite, Partitioned, then the extensions.

It raises `CookieError` when:

- the name is not an HTTP token or the value leaves cookie-octet (encode arbitrary data,
  with Base64 for example);
- the name and value exceed 4096 octets, or an attribute value exceeds 1024;
- `max_age` is not between 1 and 10**1024 - 1 (the grammar has no `Max-Age=0`: use
  `expire` to delete a cookie);
- `expires` is before 1601 or cannot be converted to UTC; a naive datetime is UTC, and so
  is one whose `tzinfo` gives no offset;
- `domain` is not a host name: ASCII, at most 253 characters, no leading dot, no port,
  labels of 1 to 63 letters, digits or hyphens that do not start or end with a hyphen;
- `path` is not empty and does not start with `/`, has outer whitespace, a control
  character, a non-ASCII character or `;` (`path=None` leaves the attribute out);
- `same_site` is not exactly `"Lax"`, `"Strict"` or `"None"`;
- an extension name is empty, has `=`, outer whitespace or a forbidden character, or is
  a standard attribute name; an extension value has outer whitespace or a forbidden
  character; the same extension name is given twice (case is ignored, A to Z only), which
  `Cookie.header()` also meets for a parsed line that repeats an extension;
- a `__Secure-` name lacks Secure, a `__Host-` name lacks Secure, has a Domain or a Path
  other than `/` (prefixes are matched without case, as browsers do);
- SameSite=None or Partitioned comes without Secure.

`expire(name, ...)` builds the same line with an empty value and
`Expires=Thu, 01 Jan 1970 00:00:00 GMT`; pass the Domain and Path the cookie was set
with.

## What a browser keeps: `receive` and `StoredCookie`

`receive(line, url, *, now, cross_site=False, is_public_suffix=None)` runs the storage
model of section 5.7 for one line received from `url` at `now` (an aware datetime) and
returns a frozen `StoredCookie`, or raises `CookieError` naming the rule that makes a
user agent ignore the line:

- the line itself is ignored (see `parse`), or the URL is malformed, has no host, or a
  host that cannot be canonicalized (see below);
- the Domain attribute is not ASCII, is a public suffix (when `is_public_suffix` is
  given and the host is not that suffix), or the host does not domain-match it;
- the cookie is Secure and the URL is not `https` or `wss`;
- `cross_site=True` and SameSite is not None;
- SameSite=None or Partitioned without Secure, or a broken prefix rule;
- a nameless cookie whose value starts with `__Secure-` or `__Host-`.

Without a Domain the cookie is host-only on the request host. Without a usable Path it
gets the default path, the directory of the request path. Expiry follows Max-Age over
Expires, both capped at 400 days from `now`; `Max-Age` of zero or less gives the
earliest representable time; a cookie with neither is a session cookie
(`persistent=False`, `expiry=None`). Non-ASCII hosts are converted with Python's IDNA
2003 codec, which differs from IDNA 2008 for a few characters such as sharp s.

The request host is canonicalized the way a browser's URL parser does it. It is
percent-decoded first (`ex%41mple.com` is `example.com`). It must fit DNS: at most 253
characters without a trailing dot and labels of at most 63, counted before IDNA
conversion, so a hostile host is refused at once instead of costing the punycode encoder
time that grows with the square of its length. After conversion it must not hold a
forbidden domain code point of the WHATWG URL Standard: a C0 control, space, `#`, `%`,
`/`, `:`, `<`, `>`, `?`, `@`, `[`, `\`, `]`, `^`, `|` or DEL (inside the brackets of an
IPv6 literal the address must be valid instead). Any of these raises `CookieError`.
Other characters that URL parsers accept, such as `_` and `"`, are kept.

The host inside brackets must be an IPv6 address without a zone ID (`[fe80::1%25eth0]`
raises `CookieError`, as URL parsers refuse it), and it is written the way the WHATWG URL
Standard serializes it: lower-case hexadecimal pieces with the first longest run of zero
pieces compressed, an IPv4-mapped address included. `[0:0::1]` and `[0000::0001]` are
both the host `::1`, so a cookie of one matches the other, and `[::FFFF:1.2.3.4]` is
`::ffff:102:304`. The cookie domain holds the address without its brackets.

In an `http`, `https`, `ws`, `wss` or `ftp` URL a backslash reads as a slash, and any
number of slashes or backslashes may follow the scheme, as in that parser:
`https://x.com\@evil.com/p` has the host `x.com` and the path `/@evil.com/p`,
`https://x.com/a\b/c` has the path `/a/b/c`, `http://[::1]\x` has the path `/x`, and
`https:x.com/a` has the host `x.com`. In a URL of any other scheme the backslash is kept
as it is.

Before the URL is read, C0 controls and spaces are stripped from both of its ends and every
tab, line feed and carriage return inside it is removed, as that parser does:
`https://x.com/a/b ` has the path `/a/b`. A port must be empty or a number from 0 to 65535
written in ASCII digits; any other port makes the URL malformed and raises `CookieError`,
as URL parsers refuse it. This also refuses `https://u:p\@x.com/`, whose authority ends at
the backslash and so has the port `p`.

The userinfo of the authority (everything up to its last `@`, the authority ending at the
first `/`, `?` or `#`) is dropped before the host is read, whatever it holds, as in that
parser: `http://[::1]@a.com/p` and `https://u:pw@x.com/` have the hosts `a.com` and
`x.com`, and a colon in the userinfo is never read as a port.

The request path is normalized the way that parser does it before it gives the default
path or is matched: spaces, double quotes, `<`, `>`, `^`, backquotes, braces, controls
and non-ASCII characters are percent-encoded as UTF-8, existing `%XX` escapes are kept,
and `.` and `..` segments (also spelled `%2e`) are resolved, so `/a/../b/c` stores the
path `/b` and `/a b/c` stores `/a%20b`.

The request host keeps a trailing dot, as browsers keep it: `www.example.com.` is a
different host from `www.example.com`, a cookie of one is not sent to the other, and
from the dotted host only a dotted Domain such as `example.com.` domain-matches. A host
whose last label is a number is read as an IPv4 address the way the WHATWG URL parser
reads it: `127.1`, `0x7f.0.0.1` and `2130706433` are all `127.0.0.1`, and a host such as
`1.2.3.4.5` or `256.0.0.1` cannot be canonicalized and raises `CookieError`.

`is_public_suffix` is called with the Domain attribute as `parse` reads it, lower-cased
(A to Z only) and without its leading dot, and also without a trailing dot, the way
public suffix lookups treat a fully qualified name: `Domain=.CO.UK.` asks about
`"co.uk"`. It is only called for a non-empty ASCII Domain. Whether the host is that
suffix is still compared with the dot, so from `https://co.uk./` the attribute
`Domain=co.uk.` is reset to a host-only cookie.

The rules that need the rest of the cookie store (step 16, a non-secure cookie
shadowing a secure one, and steps 23 and 24, replacing an old cookie and eviction) are
left to the caller.

`StoredCookie.is_expired(now)` is true once `now` reaches the expiry; the earliest
representable time that a Max-Age of zero or less gives is reached at any `now`, even an
aware time in year 1 whose UTC instant comes before it. A session cookie
never expires there: only the caller knows when the session ends.
`StoredCookie.matches(url)` is the domain, path and Secure check of the retrieval model
(section 5.8.3); SameSite and the request context are not checked.

## Errors

| Error | When |
| --- | --- |
| `CookieError` (a `ValueError`) | A line a user agent ignores, a line that breaks the server grammar in strict mode, a cookie `build` refuses, a URL that `receive` or `matches` cannot use |
| `TypeError` | An argument of the wrong type (a name that is not a `str`, a flag that is not a `bool`, a `now` that is not a `datetime`, ...) |
| `ValueError` | A naive `now` given to `receive` or `StoredCookie.is_expired` |

Messages name the rule and, for a bad character, its code point and index. They never
quote a cookie value, a whole line or a request URL, and other quoted text is cut to 40
characters, so a message is safe to log.

## Command line

`setcookie [--strict] [--url URL] [--now ISO] [LINE ...]` reads the lines given, or
stdin. Stdin is read as UTF-8 whatever the locale: a byte order mark is skipped, and a
byte that is not UTF-8 is kept as an escape (byte 0xFF becomes `\udcff` in the JSON).
It is a header dump when its first non-empty line starts with `HTTP/` or any line is a
`Set-Cookie:` field; then only the Set-Cookie fields are read, every other line is
ignored, and a dump without any prints `[]` and exits 0. It prints a JSON array with one
entry per line: `line`, then `cookie` (the fields of `Cookie`), `stored` with `--url`
(the fields of `StoredCookie`) or `error`. Dates are ISO 8601. The exit status is 0 when
every line was read, 1 when any was refused, 2 for a usage error, such as no line given
and nothing on stdin (empty or closed), and 141 when the reader of the output closed it
early (`| head`) or stdout is closed (`>&-`): the command then stops without a traceback,
as a tool killed by SIGPIPE does. With stderr closed (`2>&-`) the error lines are dropped
and stdout holds only the JSON. `--now` defaults to the clock and a time without a zone is UTC. A field name
followed by spaces or tabs before its colon (`Set-Cookie : a=1`) is still read as a
Set-Cookie field, although RFC 9112 forbids that whitespace.

## Moving from 0.2.0

Code that passes the documented types sees the same results for ordinary input. The
changes below touch error types and messages, unusual request URLs, `expires` values
whose `tzinfo` gives no offset, `str` and `int` subclasses such as Enum members, repeated
extension names and command line input. What changed:

- Wrong argument types raise `TypeError` where 0.2.0 raised `CookieError`: catch
  `TypeError` as well, or fix the call. Flags such as `secure` must be real `bool`s, and
  `max_age=True` is refused.
- Error messages are worded differently: they name the code point and index instead of
  quoting the value. Code that matched on the old text needs the new one.
- `StoredCookie.is_expired` raises `ValueError` for a naive `now`.
- `receive` no longer raises `OverflowError` near the end of the calendar.
- A request host keeps its trailing dot (0.2.0 dropped it), and a host that ends in a
  number is read as an IPv4 address (0.2.0 kept `127.1` as a name).
- `build` takes an `expires` whose `tzinfo` gives no offset as UTC, like a naive one;
  0.2.0 took it as local time, so the line differs by the machine's UTC offset.
- `build` refuses an extension name given twice (case ignored); 0.2.0 wrote both.
- A request host is percent-decoded and refused when it is longer than DNS allows or has
  a forbidden code point such as a space or a control character; 0.2.0 stored such a
  host as the cookie domain.
- The request path is percent-encoded and its dot segments resolved before the default
  path is taken and before `matches` compares it, as browsers do.
- In an `http`, `https`, `ws`, `wss` or `ftp` request URL a backslash reads as a slash
  (0.2.0 kept it, so `https://x.com\@evil.com/` gave the host `evil.com`), and
  `https:x.com` has a host.
- C0 controls and spaces are stripped from both ends of a request URL (0.2.0 kept a
  trailing one in the host or path), and a port that is not empty or a number from 0 to
  65535 raises `CookieError` (0.2.0 ignored the port).
- The userinfo of a request URL is dropped up to the last `@` of its authority, so a `[`
  or `]` in it no longer makes the URL malformed (0.2.0 raised `CookieError`).
- An IPv6 request host is stored in its compressed form (`::1` for `[0:0::1]`), and one
  with a zone ID raises `CookieError`.
- `is_public_suffix` gets the Domain without a trailing dot.
- `build` writes the plain value of a `str` or `int` subclass, so an Enum member gives
  its value instead of its name.
- The command line reads stdin as UTF-8 instead of the locale encoding, and a header
  dump without a Set-Cookie field prints `[]` and exits 0 instead of exiting 2.

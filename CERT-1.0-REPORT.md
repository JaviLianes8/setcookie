# setcookie 1.0.0 certification report

The 1.0.0 certification bar applied to setcookie. PyPI has 0.2.0, whose wheel modules are
byte for byte the `src/setcookie` of `main` at 73f9d14 (compared on 2026-10-20), so every
change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (73f9d14, same code as PyPI 0.2.0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: sources fetched again, reference implementations run (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [x] Gates (item 15), author run at 619d73a; final run after the QA lenses
- [x] PR #3 and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Baseline on 0.2.0 (before any change)

On this PC, CPython 3.13.2, at 73f9d14: `ruff format --check .`, `ruff check .` and
`mypy --strict src tests` exit 0; `pytest` passes with one skip (the installed-wheel
test, which needs `SETCOOKIE_E2E=1`); no doctests existed.

Defects found in 0.2.0 by reading and then reproducing:

- Error messages quoted the input in full: `parse` put the whole line (cookie value
  included) in the control character error, strict mode and `build` quoted the cookie
  value, and `receive` quoted the request URL, which may carry tokens in its query.
  A 1 MB value gave a 1 MB message.
- Wrong argument types were reported inconsistently: `build(1, "x")` raised
  `CookieError` (a `ValueError`) while `parse(1)` raised `TypeError`; `secure="no"`
  wrote a Secure attribute; `receive(..., now=date)` raised `AttributeError`;
  `parse_date(b"...")` raised a `TypeError` from `ord`.
- `StoredCookie.is_expired` with a naive `now` raised the comparison `TypeError`.
- `receive` raised `OverflowError` when `now` was near `datetime.max`.
- No public docstring had a runnable example; the README linked LICENSE relatively,
  which breaks on PyPI; there was no GUIDE.

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: the nine names, their parameters and defaults kept from 0.2.0 and pinned; every behaviour change in CHANGELOG and GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: every public name and method (`SameSite` in the package docstring), run by `tests/test_doctests.py`; README examples (17 outputs) run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, a consumer type-checked against the installed wheel on six interpreters |
| 5 | Typed, documented, bounded errors | PASS: `CookieError` (a `ValueError`) names the rule and position, never quotes a cookie value, a line or a URL, cuts other text to 40 characters; `TypeError` for wrong types |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: draft 22, RFC 6265, the CHIPS draft and seven web-platform-tests pages fetched again (hash match), undici and tough-cookie run live |
| 8 | Real e2e from the wheel | PASS: built wheel in a fresh venv, driven from an empty folder, console script and `python -m`, PyPI 0.2.0 upgraded in place |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t here, 3.14.6 on the laptop |
| 11 | README and `twine check` | PASS |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-20 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #3 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: author 52, every non-equivalent mutant killed (one survivor fixed with a contract, one equivalent) |
| 19 | Five independent QA lenses | rounds 1 to 3: all findings fixed (see QA lenses), re-verification pending |

## API review (item 1)

Kept: the nine public names of 0.2.0 with their signatures, parameter names and
defaults, now pinned by `tests/test_contract_api.py` together with the fields of `Cookie`
and `StoredCookie`, the `SameSite` literal and the error hierarchy. Changed, all in the
CHANGELOG and the GUIDE: `TypeError` for arguments of the wrong type everywhere (flags
must be real `bool`s), `ValueError` for a naive `now` in `StoredCookie.is_expired`,
bounded messages that name code point and index, the expiry clamped at the end of the
calendar, and `setcookie` as the module of the three public classes (pickles use the
public name). Internal: the builder's argument checks moved to `_checks.py` so every file
stays under 200 lines with its examples; `is_cookie_value` and `is_av_text` gave way to
helpers that report the position.

## Ground truth (item 7)

Fetched again on 2026-10-20 by `scripts/fetch_upstream.py` into the ignored
`tests/upstream` folder; every file matched the size and sha256 recorded in
`tests/upstream/MANIFEST.json` (URL, revision, licence). The datatracker still lists
revision 22 of draft-ietf-httpbis-rfc6265bis and revision 01 of the partitioned cookies
draft as the latest. Nothing fetched is committed or shipped.

- The draft text (`tests/test_sources.py`): cookie-octet, av-octet and the date
  delimiters are read from the ABNF and compared code point by code point; the size
  limits, the 1601 floor and the 400-day cap are read from the prose; the ten rejected and
  six accepted prefix examples of section 5.4 run through `receive` and strict mode; the
  examples of section 3.1 of RFC 6265 and of the draft pass strict mode.
- web-platform-tests at 1b67faf (`tests/test_wpt.py`): 134 cases of seven pages through
  `receive` and a small jar, all as the browsers' expectations say.
- undici 8.12.3, the HTTP client behind Node.js `fetch`, run live through
  `scripts/js_oracle.cjs` (`tests/test_oracles.py`): 12,000 seeded lines give the same
  name, value, Expires, Max-Age, Domain, Path, flags, SameSite and extensions. Corners
  where undici departs from the draft are named in the test and kept out of the inputs:
  it reads Expires with JavaScript's `Date`, keeps an earlier SameSite after an unknown
  value, does not refuse an empty name with an empty value, and writes `/` for the default
  path.
- tough-cookie 6.0.2, the cookie jar of jsdom (`tests/test_oracles.py`): 6,000 seeded
  line and URL pairs agree on whether the cookie is stored and on its name, value,
  domain, host-only flag, path, Secure and HttpOnly, and on which of nine URLs it is sent
  to. Kept out: a Secure cookie from an `http` URL (tough-cookie stores it, the draft
  says ignore it, step 13) and a `__Host-` cookie without a Path attribute (the draft
  requires the attribute, step 21.3; tough-cookie checks only the path).
- PyPI 0.2.0: its wheel modules are the `main` source; the e2e test installs it and then
  upgrades it in place.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`, three seeds each: 12,000 hostile lines through `parse` in both
modes (only `CookieError`, messages under 300 characters), 60,000 lines where every
strict-valid one rebuilds through `Cookie.header()` to the same cookie, 9,000 random
`build` calls that parse back to their arguments, 60,000 date strings, 9,000 `receive`
calls on twelve URLs. `tests/test_hostile.py`: eleven line shapes through `parse`, strict
`parse` and `receive`, six date shapes, long values, extension lists, domains and URLs,
each timed at 50,000 and 200,000 characters (linear), and 10 MB refused in under two
seconds.

## Author mutation round (item 18)

52 mutants over every module, each applied alone to a copy of a fresh clone on the
laptop (CPython 3.14.6) with the fetched sources and both JavaScript references present,
the full suite run with `-x` and a 300 s per-test limit.

| # | Mutation | Caught by |
| --- | --- | --- |
| M01 | cookie-octet admits space | test_build::test_build_rejects_values_outside_cookie_octet |
| M02 | av-octet admits `;` | test_build::test_build_rejects_unsafe_paths |
| M03 | DEL no longer a control (`~` instead) | test_fuzz::test_whatever_build_writes_parses_back_to_its_arguments |
| M04 | pair limit 4097 | test_build::test_build_enforces_the_size_limits |
| M05 | attribute limit 1023 | test_parse::test_attribute_values_longer_than_1024_octets_are_skipped |
| M06 | 400-day cap one second longer | test_docs::test_every_readme_example_runs_and_prints_its_comments |
| M07 | a 64-character label is a host name | survived; killed by test_contract_edges::test_a_domain_label_may_have_63_characters_but_not_64 (added) |
| M08 | messages not cut | test_contract_api::test_messages_stay_short_whatever_the_input |
| M09 | characters counted as octets | test_parse::test_name_and_value_size_limit_is_4096_octets |
| M10 | two-digit year 99 not 1999 | test_dates::test_parse_date_accepts |
| M11 | year floor 1600 | test_dates::test_parse_date_rejects |
| M12 | hour 24 passes the range check | equivalent: `datetime` refuses hour 24 and the date is `None` either way (pinned by test_contract_edges) |
| M13 | `;` not a date delimiter | test_sources::test_date_delimiters_match_section_5_1_1 |
| M14 | wrong day name in Expires | test_build::test_build_full_header_orders_attributes |
| M15 | Expires not converted to UTC | test_build::test_build_formats_expires_in_gmt_from_a_non_utc_zone |
| M16 | a bad Expires resets the earlier one | test_oracles::test_parse_agrees_with_undici |
| M17 | Domain keeps its leading dot | test_docs (README example) |
| M18 | a relative Path is kept | test_fuzz::test_a_strict_line_rebuilds_to_the_same_cookie |
| M19 | an unknown SameSite keeps the earlier one | test_parse::test_an_unknown_same_site_value_resets_to_default |
| M20 | Max-Age accepts `+` | test_docs (README example) |
| M21 | empty name and value accepted | test_oracles::test_parse_agrees_with_undici |
| M22 | `=` searched in the whole line | test_oracles::test_parse_agrees_with_undici |
| M23 | strict accepts Max-Age=0 | test_docs (README example) |
| M24 | strict accepts a duplicate Path | test_docs (README example) |
| M25 | strict accepts trailing whitespace | test_strict::test_strict_names_the_broken_rule |
| M26 | `__Host-` without Path accepted | test_build::test_build_enforces_prefix_and_secure_rules |
| M27 | Partitioned without Secure accepted | test_build::test_build_enforces_prefix_and_secure_rules |
| M28 | prefixes matched with case | test_build::test_build_enforces_prefix_and_secure_rules |
| M29 | Secure cookie from `http` accepted | test_cli::test_url_reports_a_rejected_cookie |
| M30 | cross-site Lax cookie accepted | test_store::test_a_cross_site_request_sets_only_same_site_none |
| M31 | Max-Age=0 not expired | test_store::test_max_age_zero_or_below_expires_at_once |
| M32 | Expires not capped at 400 days | test_store::test_max_age_wins_over_expires_and_is_capped_at_400_days |
| M33 | `__Host-` with Domain stored | test_oracles::test_storage_and_retrieval_agree_with_tough_cookie |
| M34 | public suffix refused even when it is the host | test_store::test_the_public_suffix_hook |
| M35 | default path of `/a` is `/a` | test_fuzz::test_receive_never_raises_anything_but_cookie_error |
| M36 | path match ignores the `/` boundary | test_oracles::test_storage_and_retrieval_agree_with_tough_cookie |
| M37 | IP hosts domain-match | test_store::test_an_ip_host_matches_only_itself |
| M38 | `wss` not secure | test_store::test_a_secure_cookie_needs_a_secure_url |
| M39 | Secure cookie sent over `http` | test_doctests (StoredCookie.matches example) |
| M40 | builder pair limit 4095 | test_build::test_build_enforces_the_size_limits |
| M41 | builder writes Max-Age=0 | test_build::test_build_rejects_max_age_that_is_not_a_positive_int |
| M42 | extension named `PATH` accepted | test_build::test_build_rejects_unsafe_extensions |
| M43 | path with a trailing tab accepted | test_review_fixes::test_a_path_with_outer_whitespace_is_refused |
| M44 | builder writes a 1600 Expires | test_build::test_build_rejects_expires_that_user_agents_ignore |
| M45 | the expiry instant is not expired | test_store::test_max_age_zero_or_below_expires_at_once |
| M46 | CLI always exits 0 | test_cli::test_strict_reports_the_rule_and_exits_one |
| M47 | a header dump without Set-Cookie read as lines | test_review_fixes::test_a_header_dump_without_set_cookie_yields_no_lines |
| M48 | `CookieError` not a `ValueError` | test_build::test_build_error_is_a_value_error |
| M49 | nameless `__Host-` value accepted | test_store::test_a_nameless_cookie_cannot_pose_as_a_prefix |
| M50 | int flags accepted | test_review_fixes::test_build_arguments_of_the_wrong_type_raise_type_error |
| M51 | empty attribute name kept as an extension | test_fuzz::test_a_strict_line_rebuilds_to_the_same_cookie |
| M52 | strict accepts a control in an extension | test_fuzz::test_a_strict_line_rebuilds_to_the_same_cookie |

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Laptop, fresh clone at 442e2d3, CPython 3.14.6, `SETCOOKIE_E2E=1` and
  `SETCOOKIE_E2E_PYPI=1`, fetched sources and both references present: 505 passed, no
  skip. The e2e test builds the wheel and sdist, checks their contents, installs PyPI
  0.2.0 into a fresh venv and checks it, upgrades it in place with the built wheel, runs
  a consumer program from an empty folder with `-I`, and drives the `setcookie` script
  and `python -m setcookie` by subprocess (JSON output, exit status 1 with the reason).
- This PC, fresh clone at 619d73a: wheel and sdist built, `twine check --strict` passes
  both. The wheel holds the package, `py.typed`, the entry point and LICENSE; the sdist
  holds the sources, tests, scripts, docs, LICENSE and the manifest of fetched files, and
  no fetched file, `node_modules`, planning note or this report. On every interpreter
  here the wheel was installed into a fresh venv and the sdist's own suite run with `src`
  removed (fetched sources, both references and mypy present): CPython 3.10.19, 3.11.5,
  3.12.12, 3.13.2, 3.14.2 and 3.14.2 free-threaded, 504 passed and 1 skipped each (the
  e2e test, which runs from the source tree). 3.8 and 3.9 are below `requires-python`;
  no 3.13 free-threaded build is installed here.
- pyproject: version 1.0.0, Production/Stable, Python 3.10 to 3.14 classifiers, MIT,
  Homepage, Source, Documentation, Issues and Changelog URLs, keywords, no runtime
  dependency.

## Gates (item 15)

At 619d73a on this PC, each command on its own: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (504 passed,
1 skipped: the opt-in e2e test, which passed on the laptop) all exit 0.

## QA lenses (item 19)

### Round 1

Five fresh lenses ran against 23471a2. None reported PASS outright; every finding is
fixed below, each behaviour fix with a contract that failed on 23471a2 first
(`tests/test_qa_fixes.py`, `tests/test_contract_pins.py`, `tests/test_cli.py`), and every
behaviour change is in the CHANGELOG and the GUIDE.

| Lens | Finding | Fix |
| --- | --- | --- |
| a | A1: the README example `curl -sI https://example.com \| setcookie --strict` exits 2, as example.com sets no cookie and an empty dump was a usage error | A dump without Set-Cookie prints `[]` and exits 0; exit 2 only when there is no input at all; README example uses github.com, which sets cookies (checked 2026-10-20) |
| a | A2: dump detection in the code (any `Set-Cookie:` line) differs from the docs (status line only) | README and GUIDE describe both triggers and that other lines of a dump are ignored; pinned by `test_set_cookie_fields_without_a_status_line_are_a_dump` |
| a | A3: GUIDE says `build` reads back to the same values, but Domain reads back lower-cased and Expires drops microseconds | GUIDE states both exceptions |
| b | F1: the request host lost its trailing dot, unlike draft 22 and Chrome | The trailing dot is kept: `www.example.com.` is its own host, only a dotted Domain matches it, cookies are not sent across |
| b | F2: IPv4 shorthand hosts (`127.1`, `0x7f.0.0.1`, `2130706433`) were domain names, so `Domain=1` was accepted from `127.1` | A host that ends in a number goes through the WHATWG IPv4 parser: it becomes the dotted address, or raises `CookieError` when it is not one (`1.2.3.4.5`, `256.0.0.1`, `a.09`) |
| c | F1: `OverflowError` escaped `receive`, `matches` and the CLI for a huge punycode label on 3.13 and 3.14 | `OverflowError` and `ValueError` from the codec become the documented `CookieError`; tests for `receive`, `matches` and the CLI |
| c | F2: `build` checked a `str` or `int` subclass but wrote it through its `__format__` (Enum names, attribute injection) | Every argument is turned into its exact `str` or `int` before it is checked and written |
| c | F3: an `expires` whose `tzinfo` gives no offset was read as local time | `format_http_date` tests `utcoffset() is None`, so it is UTC like a naive datetime |
| d | F1: same as A1 | Same fix |
| d | F2: stdin was decoded with the locale encoding (cp1252 on Windows) | The CLI reads the bytes and decodes UTF-8 with the BOM skipped and other bytes kept as escapes |
| d | F3: `scripts/release.ps1` refused any name already on PyPI, so it could never release 1.0.0 | It checks that the version in `pyproject.toml` is not on PyPI yet; the guard was run for 1.0.0 (passes) and 0.2.0 (refused) |
| e | F1 to F9: ten surviving mutants (lone DQUOTE, `expire` Partitioned, strict SameSite=none spelling, prefix trailing dash, trailing-dot host, Max-Age clamp, 1601 boundary, CLI `--now` offset, build size guards) | Contracts added; each mutant re-applied alone and killed (table below) |
| e | F10: the linearity test was flaky under load | It compares 8 times the input against a 24 times bound (quadratic would be 64) and measures again up to three times before failing; a quadratic stand-in still fails it |

Mutants of lens e and of this round's fixes, each applied alone on CPython 3.13.2 here:

| Mutant | Caught by |
| --- | --- |
| C06 a value of one `"` counts as quoted | test_contract_pins::test_a_lone_double_quote_is_not_a_quoted_value |
| B10 `expire` drops Partitioned | test_contract_pins::test_expire_passes_every_flag_through |
| S05 strict SameSite=None check case-sensitive | test_contract_pins::test_strict_same_site_none_needs_secure_in_any_case |
| R04 `__host` and `__secure` without the dash | test_contract_pins::test_a_name_that_only_starts_like_a_prefix_has_no_prefix_rules |
| H07 the trailing dot dropped again | test_qa_fixes::test_a_trailing_dot_keeps_the_request_host_distinct |
| T07 Max-Age overflow returns `now` | test_contract_pins::test_max_age_past_the_end_of_the_calendar_clamps_to_the_latest_time |
| B02 1601 refused | test_contract_pins::test_build_accepts_expires_from_the_first_day_of_1601 |
| L05 CLI `--now` offset replaced by UTC | test_cli::test_now_keeps_its_offset |
| B13 and B14 build size guards one octet late | test_contract_pins::test_build_size_limits_raise_its_own_messages_at_the_boundary |
| codec `OverflowError` not caught | test_qa_fixes::test_a_punycode_label_too_large_to_decode_raises_cookie_error |
| `max_age` and `same_site` not made exact | test_qa_fixes::test_build_writes_the_value_an_enum_member_holds |
| floating `tzinfo` read as local | test_qa_fixes::test_build_takes_a_floating_tzinfo_as_utc_like_a_naive_datetime |
| stdin decoded as cp1252 | test_cli::test_stdin_is_decoded_as_utf_8_whatever_the_locale |
| empty dump a usage error | test_cli::test_a_header_dump_without_set_cookie_prints_an_empty_list |
| IPv4 parser skipped | test_qa_fixes::test_ipv4_shorthand_hosts_are_read_as_the_address |

Disputed findings: none.

Gates at the fix commit on this PC (CPython 3.13.2): `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (543 passed,
1 skipped: the opt-in e2e test) exit 0.

E2E at 4fd7ae1 (fresh clone from GitHub, this PC on turn pc/3, CPython 3.13.2, fetched
sources present, `SETCOOKIE_E2E=1` and `SETCOOKIE_E2E_PYPI=1`): 540 passed, 4 skipped
(the Node.js reference tests, no Node.js in that venv); the wheel, sdist, upgrade from
PyPI 0.2.0 and the CLI by subprocess all pass with the round 1 fixes.

### Round 2

Lenses d and e ran again against 09db9e8 (lenses a, b and c are re-checked separately).
Lens d confirmed its three round 1 findings fixed (wheel and sdist on CPython 3.10.19,
3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t, upgrade from PyPI 0.2.0, a 68 check sweep)
and found one new defect. Lens e confirmed its ten round 1 findings closed (F5 accepted as
a design change) and found eight surviving mutants in the code changed since 23471a2.
Every finding is fixed; the defect with a contract that failed on 09db9e8 first.

| Lens | Finding | Fix |
| --- | --- | --- |
| d | N1: with stdin closed (`setcookie <&-`) `sys.stdin` is `None` and the CLI died with an `AttributeError` traceback and exit 1 | `_stdin` returns no input for a closed stdin, so the CLI reports the usage error and exits 2; `test_cli::test_closed_stdin_is_a_usage_error_not_a_crash` runs it by subprocess (and with descriptor 0 really closed off Windows); CHANGELOG, GUIDE and README say so |
| e | G1 (N30): a middle IPv4 part above 255 not pinned | `1.256.0.1` and `1.2.256.3` added to the refused hosts |
| e | G2 (N29): the four part limit not pinned apart from the last part range | `1.2.3.4.0` added to the refused hosts |
| e | G3 (N33): a label that is not a number, in a host that ends in a number, not pinned | `a.1` and `x.y.127` added to the refused hosts |
| e | G4 (N34): a hex last label not pinned | `127.0.0.0x1` added to the shorthand table, `x.0x1` to the refused hosts |
| e | G5 (N25): a decimal label with hex letters not pinned as a host name | `x.1a` and `example.1e` added to the names that stay host names |
| e | G6 (N23): an octal label with a non-octal digit not pinned | `1.09` and `09` added to the refused hosts |
| e | G7 (N24): a bare `0x` part read as 0 not pinned | `test_a_bare_hex_prefix_is_the_number_zero` (`0x` and `0x.0x.0x.0x` are `0.0.0.0`) |
| e | G8 (N13): undecodable stdin bytes kept as escapes not pinned | `test_cli::test_bytes_that_are_not_utf_8_do_not_crash` asserts the value `a\udcffb`; GUIDE shows the escape |

Each mutant applied alone, `__pycache__` removed and bytecode off, against
`tests/test_qa_fixes.py` and `tests/test_cli.py` on CPython 3.14 (laptop, turn portatil/3):

| Mutant | Caught by |
| --- | --- |
| N30 `number > 255` to `> 256` | test_qa_fixes::test_a_host_that_ends_in_a_bad_number_is_refused[1.256.0.1] |
| N29 `len(numbers) > 4` to `> 5` | test_qa_fixes::test_a_host_that_ends_in_a_bad_number_is_refused[1.2.3.4.0] |
| N33 `None in numbers` removed | test_qa_fixes::test_a_host_that_ends_in_a_bad_number_is_refused[a.1] |
| N34 hex last label not read as a number | test_qa_fixes::test_ipv4_shorthand_hosts_are_read_as_the_address[127.0.0.0x1] |
| N25 decimal digits take the hex alphabet | test_qa_fixes::test_names_with_digits_that_are_not_numbers_stay_host_names |
| N23 octal only from three characters | test_qa_fixes::test_a_host_that_ends_in_a_bad_number_is_refused[1.09] |
| N24 bare `0x` is not a number | test_qa_fixes::test_a_bare_hex_prefix_is_the_number_zero[0x] |
| N13 stdin decoded with `replace` | test_cli::test_bytes_that_are_not_utf_8_do_not_crash |
| N1 closed stdin read again | test_cli::test_closed_stdin_is_a_usage_error_not_a_crash |

Disputed findings: none.

Fix commit: the commit that adds this section, on top of 09db9e8.

Gates at the fix commit: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on Elena's
PC (CPython 3.14, turn elena/8, fetched sources present): 555 passed, 1 skipped (the
opt-in e2e test).

### Round 3

Lens e ran again against 0797282. It confirmed the eight round 2 findings (G1 to G8) killed
on CPython 3.14.2 and the F5 dispute still valid, and ran 15 new mutants on `_cli._stdin`
and its caller, the only source change since 09db9e8: 12 were killed and 3 survived. No
behaviour changed: the three survivors were missing contracts, so this round adds tests
only and the CHANGELOG is unchanged.

| Lens | Finding | Fix |
| --- | --- | --- |
| e | E3-C15: whitespace at the start and end of stdin not pinned (`_stdin().strip()` survived) | `test_cli::test_stdin_lines_keep_their_outer_whitespace`: `a=1 ` with `--strict` exits 1 with the trailing whitespace error and echoes the line as given; `  a=1` keeps its leading spaces in `line` |
| e | E3-C08-C09: the fallback for a text stdin without `.buffer` never exercised | `test_cli::test_a_text_stdin_without_a_byte_buffer_is_read`: a `StringIO` stdin is read, exit 0 and cookie `a`; the fallback stays, since a host program may replace `sys.stdin` with a plain text stream |

Each mutant applied alone to a copy of the repository, `__pycache__` removed and bytecode
off, against `tests/test_cli.py` on CPython 3.13.2 (this PC, one test file):

| Mutant | Caught by |
| --- | --- |
| C15 `_stdin()` to `_stdin().strip()` in `main` | test_cli::test_stdin_lines_keep_their_outer_whitespace |
| C08 `getattr(sys.stdin, "buffer", None)` to `sys.stdin.buffer` | test_cli::test_a_text_stdin_without_a_byte_buffer_is_read (AttributeError) |
| C09 fallback `return sys.stdin.read()` to `return ""` | test_cli::test_a_text_stdin_without_a_byte_buffer_is_read (usage error) |

Disputed findings: none.

Fix commit: the commit that adds this section, on top of 0797282.

Gates at the fix commit: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on Elena's
PC (CPython 3.14, turn elena/11, clean clone of 2daf6e5, fetched sources absent): 533
passed, 24 skipped.

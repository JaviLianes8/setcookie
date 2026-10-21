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
| 19 | Five independent QA lenses | rounds 1 to 11: all findings fixed or disputed with evidence (see QA lenses), re-verification pending |

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

### Round 4

Lens e ran again against 7797334. It confirmed every earlier finding fixed (E3-C15, C08,
C09 now killed, the eight original mutants still killed) and the F5 dispute still valid,
and ran 10 new probes on `_cli._stdin` and `_cli.main`: 7 were killed and 3 survived. No
behaviour changed: the three survivors were missing contracts, so this round adds tests
only and the CHANGELOG is unchanged.

| Lens | Finding | Fix |
| --- | --- | --- |
| e | E4-S08: nothing pinned that stdin is read only when no line is given (`text = _stdin()` survived, so `setcookie a=1` would wait for EOF on an open stdin) | `test_cli_stdin::test_stdin_is_not_read_when_lines_are_given`: a stdin whose `read` fails, `main(["a=1"])` exits 0 with cookie `a`; `test_cli_stdin::test_the_command_does_not_wait_on_an_open_stdin_when_lines_are_given`: `python -m setcookie a=1` with a stdin pipe left open exits 0 within 60 s |
| e | E4-S03: outer whitespace not pinned on the text stdin fallback (`read().strip()` survived) | `test_cli::test_a_text_stdin_without_a_byte_buffer_is_read` also feeds `StringIO("a=1 \n")` with `--strict`: exit 1, line `a=1 `, trailing whitespace error on stdout and stderr |
| e | E4-S06: the text stdin fallback tested with one line only (`readline()` survived) | the same test now reads `StringIO("a=1\nb=2\n")` and asserts the cookie names `["a", "b"]` |

Each mutant applied alone to the working tree, against `tests/test_cli.py` and
`tests/test_cli_stdin.py` on CPython 3.13.2 (this PC, two test files), then reverted:

| Mutant | Caught by |
| --- | --- |
| S08 `text = "" if options.lines else _stdin()` to `text = _stdin()` | test_cli_stdin::test_stdin_is_not_read_when_lines_are_given (AssertionError from the stdin read); test_cli_stdin::test_the_command_does_not_wait_on_an_open_stdin_when_lines_are_given (timeout) |
| S03 fallback `return sys.stdin.read()` to `return sys.stdin.read().strip()` | test_cli::test_a_text_stdin_without_a_byte_buffer_is_read |
| S06 fallback `return sys.stdin.read()` to `return sys.stdin.readline()` | test_cli::test_a_text_stdin_without_a_byte_buffer_is_read |

Disputed findings: none.

Fix commit: the commit that adds this section, on top of 7797334.

Gates at the fix commit: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on Elena's
PC (CPython 3.14, turn elena/10, clean clone of 72ebcdf, fetched sources absent, so their
tests and the opt-in e2e test skip): 560 tests collected, none failed.

### Round 5

Lens e ran again against 85d1d2a. It confirmed the round 4 findings (E4-S08, S03, S06)
killed, the 11 earlier mutants still killed and the F5 dispute still valid, and ran 10 new
probes on `_cli._stdin` and `_cli.main`: 7 were killed and 3 survived. It also found that
one subprocess test ran whatever setcookie was installed instead of the tree under test.
No behaviour changed: this round adds and corrects tests only and the CHANGELOG is
unchanged.

| Lens | Finding | Fix |
| --- | --- | --- |
| e | E5-P10: the last byte of a byte stdin without a final newline not pinned (`buffer.read()[:-1]` survived) | `test_cli_stdin::test_the_last_byte_of_stdin_is_kept_without_a_final_newline`: `python -m setcookie` fed `b"a=1"` (no newline) exits 0 with cookie `a`, value `1` |
| e | E5-P02: the same gap on the text stdin fallback (`sys.stdin.read()[:-1]` survived) | `test_cli::test_a_text_stdin_without_a_byte_buffer_is_read` also reads `StringIO("a=1")` and asserts the value `1` |
| e | E5-P08: the newline after the JSON output not pinned (deleting `sys.stdout.write("\n")` survived) | `test_cli_stdin::test_the_json_output_ends_with_a_newline`: `python -m setcookie a=1` exits 0 and its stdout ends with a newline right after `]` |
| e | E5-T1: `test_the_command_does_not_wait_on_an_open_stdin_when_lines_are_given` started the child without `PYTHONPATH`, so it imported the installed setcookie | every child in `tests/test_cli_stdin.py` now gets `PYTHONPATH` set to the directory holding the `setcookie` under test, as `test_cli.py` already did; mutant S08 now fails this test too |

Each mutant applied alone to the working tree with bytecode off, against
`tests/test_cli.py` and `tests/test_cli_stdin.py` on CPython 3.13.2 (this PC, two test
files), then reverted:

| Mutant | Caught by |
| --- | --- |
| P10 `data: bytes = buffer.read()` to `buffer.read()[:-1]` | test_cli_stdin::test_the_last_byte_of_stdin_is_kept_without_a_final_newline |
| P02 fallback `return sys.stdin.read()` to `return sys.stdin.read()[:-1]` | test_cli::test_a_text_stdin_without_a_byte_buffer_is_read |
| P08 `sys.stdout.write("\n")` in `main` deleted | test_cli_stdin::test_the_json_output_ends_with_a_newline |
| S08 `text = "" if options.lines else _stdin()` to `text = _stdin()` | test_cli_stdin::test_stdin_is_not_read_when_lines_are_given; test_cli_stdin::test_the_command_does_not_wait_on_an_open_stdin_when_lines_are_given (now runs the tree under test) |

Disputed findings: none.

Fix commit: the commit that adds this section, on top of 85d1d2a.

Gates at the fix commit: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on the laptop
(CPython 3.14.6, turn portatil/4, clean clone of fb1580e, fetched sources absent, so
their tests and the opt-in e2e test skip): 537 passed, 24 skipped.

### Round 6

Five fresh lenses ran against 9e88df0 (the first round of a second full pass). None
reported PASS; every finding is fixed below. Each behaviour fix has a contract in
`tests/test_qa6_fixes.py` or `tests/test_qa6_pins.py` that failed on 9e88df0 first
(run against the 9e88df0 source: 82 of 170 cases failed, and the hostile host timing
case was stopped after two minutes; all 171 pass after the fix); the lens e findings that only
asked for a missing contract got a test that passes on 9e88df0 and fails on its mutant.
Every behaviour change is in the 1.0.0 section of the CHANGELOG and in the GUIDE.

| Lens | Finding | Fix |
| --- | --- | --- |
| a | F1: `is_public_suffix` got `co.uk.` for `Domain=co.uk.`, so a dotted public suffix was stored | the callable gets the Domain without its trailing dot (lower-case ASCII, no leading dot), documented in the `receive` docstring and the GUIDE; `test_qa6_fixes::test_the_public_suffix_callable_gets_the_domain_without_a_trailing_dot` |
| a, e | A-F2, E-F2-B03: a repeated extension name was refused only by the final strict self-check, with a `strict:` message, and was not pinned | `_checks.extension_texts` refuses it in the builder (`extension 'priority' is given twice`, case ignored), also for `Cookie.header()`; added to the GUIDE error list; `test_qa6_fixes::test_build_refuses_an_extension_name_given_twice` |
| a | F3: a naive `expires` reads back aware in UTC, not listed | GUIDE: third read-back exception |
| a | F4: GUIDE migration list missed the no-offset `tzinfo` change and its opening sentence was wrong | bullet added (with the other changes of this round), opening sentence reworded |
| a, e | A-F5, E-F9-X18: the bad-name message printed both causes; the length suffix of a cut text was not pinned | `cookie name is empty`, or `cookie name 'a b' has U+0020 at index 1, outside tchar`; doctest of `Cookie.header` updated; `test_qa6_fixes::test_a_bad_cookie_name_names_the_rule_it_breaks`, `test_qa6_pins::test_a_long_quoted_text_is_cut_and_its_length_given` |
| a | F6: the five public functions reported private modules | `__module__ = "setcookie"` on `build`, `expire`, `parse`, `parse_date`, `receive`; `test_qa6_fixes::test_the_public_functions_report_the_public_module` |
| a | F7: CLI usage line differed from the GUIDE | `metavar="ISO"` and `metavar="LINE"`; usage now `setcookie [-h] [--strict] [--url URL] [--now ISO] [LINE ...]` |
| a | F8: 0.2.0 and 0.1.0 had no date | `## [0.2.0] - 2026-10-19` (PyPI upload time), `## [0.1.0] - 2026-10-12` (commit 841d91f) |
| b, c | B-F1, C-F2: hosts with controls, space, `<`, `^`, `|`, `%` were stored; `%41` kept literally | the host is percent-decoded, then refused after IDNA conversion when it holds a forbidden domain code point of the WHATWG URL Standard (list fetched from url.spec.whatwg.org on 2026-10-21); a bracketed host must be a valid IPv6 address; `test_qa6_fixes::test_a_host_with_a_forbidden_code_point_is_refused` (13 hosts, also through `matches`), `test_the_host_is_percent_decoded_as_a_url_parser_does`. Partly disputed, see below |
| b | F2: the request path was used verbatim | `_url._path` percent-encodes with the WHATWG path percent-encode set plus non-ASCII as UTF-8 and resolves `.`/`..` segments (also `%2e` spellings) for the default path and for `matches`; `/a/../b/c` gives `/b`, `/a b/c` gives `/a%20b`, `/é/x` gives `/%C3%A9`, as lens b measured in Chrome; `test_qa6_fixes::test_the_request_path_is_normalised_as_a_url_parser_does` (8 cases), `test_matches_normalises_the_request_path` |
| b | F3: strict refused a leap second; calendar errors shared the grammar message | `_dates.fixdate_problem`: `23:59:60` passes (RFC 9110 5.6.7 ABNF comment, fetched), an impossible moment says `is an IMF-fixdate of a moment that does not exist`; GUIDE documents both and that section 5.1.1 then drops the date; `test_qa6_fixes::test_strict_accepts_a_leap_second_and_names_an_impossible_date` |
| c | F1: host canonicalization was quadratic in host length | the host must fit 253 characters and labels of 63 (IDNA separators counted) before the codec runs; `test_qa6_fixes::test_a_huge_hostile_host_fails_fast`: a 32,000-character CJK label, 32,000 `é.` labels, a 64-character label and a 255-character host each fail in under 50 ms, 253 and 63 still pass |
| c | F3: a `str` subclass with a lying `__iter__` hid CR LF | `parse`, `receive`, `parse_date` and the URL reader work on `str.__str__(text)`; `test_qa6_fixes::test_a_str_subclass_is_read_as_the_text_it_holds` |
| c | F4: Max-Age=0 not expired at a year-1 aware `now` with a positive offset | `is_expired` treats the earliest-time sentinel as always reached; `test_qa6_fixes::test_max_age_zero_is_expired_even_at_the_earliest_aware_time` |
| d | F1: BrokenPipeError traceback and status 120 when the output pipe closes | `_cli.main` catches the closed pipe (EPIPE, or EINVAL on Windows), points stdout and stderr at devnull and returns 141; GUIDE exit statuses; `test_qa6_pins::test_a_closed_output_pipe_stops_quietly` (subprocess, read end closed before 5,000 lines are written) |
| e | F1-T16: `__Host-` cookie with a public-suffix Domain reset to host-only not pinned | `test_qa6_pins::test_a_host_prefix_survives_a_public_suffix_domain_reset_to_host_only` |
| e | F3-S14: non-ASCII whitespace at the edges of an extension in strict mode not pinned | `test_qa6_pins::test_strict_refuses_non_ascii_whitespace_at_the_edges_of_an_extension` (U+00A0, U+0085, U+3000, both edges) |
| e | F4-C13: the exact tchar set not pinned | `test_qa6_pins::test_a_cookie_name_is_exactly_an_http_token`: all 128 ASCII characters through `build` and strict `parse` |
| e | F5-T15, F6-X01: a `tzinfo` whose `utcoffset()` is None not pinned for `receive` and `is_expired` | `test_qa6_pins::test_receive_refuses_a_now_whose_tzinfo_gives_no_offset`, `test_is_expired_refuses_a_now_whose_tzinfo_gives_no_offset` |
| e | F7-B06: `extensions=""` not pinned | `test_qa6_pins::test_extensions_given_as_a_string_raise_type_error` (`""`, a non-empty str, `b""`) |
| e | F8-L09: whitespace before the colon of a dump field not pinned | kept on purpose (a dump is read leniently), commented in `_cli.py`, documented in the GUIDE and pinned by `test_qa6_pins::test_a_header_dump_field_may_have_space_before_its_colon` (space and tab) |

Internal: request URL handling moved from `_match.py` to the new `_url.py`, so every file
stays under 200 lines.

Disputed findings:

- B-F1 (partly). The forbidden code points are fixed as above, but two parts of the
  suggested fix are not taken. (1) `"` in a host is accepted: it is not a forbidden host
  or domain code point in the WHATWG URL Standard (definitions fetched from
  https://url.spec.whatwg.org/ on 2026-10-21: the forbidden domain code points are the
  forbidden host code points, C0 controls, `%` and DEL; `"` is in neither list). (2)
  Labels are not required to be LDH: the same standard accepts `_`, and browsers keep
  such hosts. Evidence run on this PC with Node.js 24.18.0, whose `URL` follows the
  WHATWG parser: `new URL('https://a"b.com/').href` is `https://a"b.com/...`,
  `new URL('https://a_b.com/')` is accepted, while `a b.com`, `a<b.com`, `a^b.com`,
  `a|b.com` and `a%00b.com` throw, and `a%41b.com` gives `aab.com`. Refusing `"` or `_`
  would make `receive` reject URLs a browser sends cookies to.

Fix commit: the commit that adds this section, on top of 9e88df0.

Gates at the fix commit 8fa92b2: `ruff format --check .`, `ruff check .`, `mypy --strict src`
and `mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on
Elena's PC (CPython 3.14.2, turn elena/5, low priority, clean clone of 8fa92b2, fetched
sources absent, so their tests and the opt-in e2e test skip): 731 tests, 708 passed,
23 skipped, none failed.

### Round 7

The five lenses ran again against e5cb908 (the second round of the second full pass).
Lens b confirmed its round 6 findings F1, F2 and F3 fixed and the `"` dispute valid; lens
d confirmed its F1 fixed, the packaging and the PyPI upgrade, and 726 passed on six
interpreters. Every new finding is fixed below; none is disputed. Each behaviour fix has a
contract in `tests/test_qa7_fixes.py` that failed on e5cb908 first (27 of its 32 cases
failed; the 5 that passed pin cases already right: a backslash in the query, a backslash
in a URL of another scheme, `[::]`, `[2001:DB8::]` and `[1:2:3:4:5:6:7:8]`). The lens e
findings that only asked for a missing contract got a test in `tests/test_qa7_pins.py`
that passes on e5cb908 and fails on its mutant. The expected hosts and paths were measured with Node.js 24.18.0
`new URL(...)`, which follows the WHATWG URL parser. Every behaviour change is in the
1.0.0 section of the CHANGELOG and in the GUIDE.

| Lens | Finding | Fix |
| --- | --- | --- |
| a, b | A-N1, B-N1: a backslash in a special URL was kept, so `https://x.com\@evil.com/p/q` gave the host `evil.com` and `/a\b/c` the path `/a\b` | for `http`, `https`, `ws`, `wss` and `ftp`, `_url.request_of` reads every backslash as a slash and skips any slashes after the scheme before `urlsplit`, as the parser's special authority states do (`https:x.com` and `https:///x.com` now have the host `x.com`, as in Node); other schemes keep the backslash; docstring and GUIDE; `test_qa7_fixes::test_a_backslash_is_a_slash_in_a_special_url` (11 URLs), `test_a_backslash_is_kept_in_a_url_of_another_scheme`, `test_matches_reads_a_backslash_as_a_slash` |
| b, c, d | B-N2, C-N1, D-N3: a bracketed IPv6 host was stored as written and a zone ID (any characters, any length) was accepted | `_url._ipv6` refuses any `%` in the brackets and serializes the address as the WHATWG IPv6 serializer does (lower-case pieces, first longest zero run of two or more compressed, IPv4-mapped in hex pieces); `test_qa7_fixes::test_an_ipv6_host_is_serialized_as_a_url_parser_does` (10 spellings, each checked in Node), `test_spellings_of_one_ipv6_address_match_each_other`, `test_an_ipv6_zone_id_is_refused` (`%25eth0`, `%eth0`, NUL, space and `<>`, through `receive` and `matches`), `test_a_huge_ipv6_zone_id_is_refused` |
| d | D-N1: with stderr closed the error lines landed in stdout after the JSON | `_cli.main` writes the error lines only when `sys.stderr` is not None; GUIDE; `test_qa7_fixes::test_a_closed_stderr_leaves_the_json_on_stdout_intact` |
| d | D-N2: with stdout closed, `AttributeError` traceback | `_cli.main` skips the JSON when `sys.stdout` is None and returns 141 as for a closed pipe, still writing error lines to stderr; GUIDE; `test_qa7_fixes::test_a_closed_stdout_stops_without_a_traceback`, `test_a_closed_stdout_still_reports_failures_on_stderr` |
| e | N25: a bracketed host need not be IPv6 | `test_qa7_pins::test_a_bracketed_host_must_be_an_ipv6_address` (`[v1.abc]`, `[v7.x-y]`) |
| e | N27: the ideographic label separators not pinned | `test_qa7_pins::test_an_ideographic_full_stop_separates_labels_for_the_dns_bound` (U+3002, U+FF0E, U+FF61, labels of 40) |
| e | N38: lone surrogate to U+FFFD not pinned | `test_qa7_pins::test_a_lone_surrogate_in_the_path_becomes_the_replacement_character` |
| e | N24: `str.__str__` on the URL not pinned | `test_qa7_pins::test_a_str_subclass_cannot_redirect_the_request_url` (`receive` and `matches`) |
| e | N28: the 253 bound not pinned at its edge | `test_qa7_pins::test_the_host_length_bound_is_253_characters` (253 kept, 254 refused) |
| e | N29: the label bound before IDNA not pinned | `test_qa7_pins::test_the_label_bound_applies_before_idna_mapping` (63 `a` plus U+00AD) |
| e | N35: a final `.` or `..` segment becoming empty not observable | `test_qa7_pins::test_a_final_dot_segment_of_the_request_path_is_empty` (through `matches` and the default path) |
| e | N37: `~` left unencoded not pinned | `test_qa7_pins::test_a_tilde_is_not_encoded_in_the_path` |
| e | N40: not every `..` spelling pinned | `test_qa7_pins::test_every_spelling_of_a_double_dot_segment_is_resolved` (7 spellings) |
| e | N11: the flush inside the try not pinned | `test_qa7_pins::test_a_closed_output_pipe_stops_quietly_after_one_short_line` |
| e | N13: the stderr redirect of `_closed_pipe` not pinned | `test_qa7_pins::test_a_closed_error_pipe_stops_quietly` |
| e | N09: an OSError other than a closed pipe swallowed | `test_qa7_pins::test_an_output_error_other_than_a_closed_pipe_propagates` (ENOSPC) |

Each mutant applied alone to a scratch copy with bytecode off, against
`tests/test_qa7_pins.py`, `tests/test_qa7_fixes.py` and `tests/test_qa6_fixes.py` on
CPython 3.13.2 (this PC):

| Mutant | Caught by |
| --- | --- |
| N25 bracketed host stored as written | test_qa7_pins::test_a_bracketed_host_must_be_an_ipv6_address |
| N27 `_DOTS` reduced to `.` | test_qa7_pins::test_an_ideographic_full_stop_separates_labels_for_the_dns_bound |
| N38 lone surrogate not replaced | test_qa7_pins::test_a_lone_surrogate_in_the_path_becomes_the_replacement_character |
| N24 `str.__str__` dropped | test_qa7_pins::test_a_str_subclass_cannot_redirect_the_request_url |
| N28 `> 253` to `> 254` | test_qa7_pins::test_the_host_length_bound_is_253_characters |
| N29 `> 63` to `> 64` | test_qa7_pins::test_the_label_bound_applies_before_idna_mapping |
| N35 final dot segment kept | test_qa7_pins::test_a_final_dot_segment_of_the_request_path_is_empty |
| N37 `<= "~"` to `< "~"` | test_qa7_pins::test_a_tilde_is_not_encoded_in_the_path |
| N40 `%2e.` removed | test_qa7_pins::test_every_spelling_of_a_double_dot_segment_is_resolved |
| N11 flush in the try removed | test_qa7_pins::test_a_closed_output_pipe_stops_quietly_after_one_short_line |
| N13 `_closed_pipe` redirects stdout only | test_qa7_pins::test_a_closed_error_pipe_stops_quietly |
| N09 every OSError returns 141 | test_qa7_pins::test_an_output_error_other_than_a_closed_pipe_propagates |
| backslash not read as a slash | test_qa7_fixes::test_a_backslash_is_a_slash_in_a_special_url |
| slashes after the scheme not skipped | test_qa7_pins::test_a_bracketed_host_must_be_an_ipv6_address (no host), test_qa7_fixes::test_a_backslash_is_a_slash_in_a_special_url |
| zone ID check removed | test_qa7_fixes::test_an_ipv6_zone_id_is_refused |
| last instead of first longest zero run | test_qa7_fixes::test_an_ipv6_host_is_serialized_as_a_url_parser_does |
| stderr guard removed | test_qa7_fixes::test_a_closed_stderr_leaves_the_json_on_stdout_intact |
| status for a closed stdout removed | test_qa7_fixes::test_a_closed_stdout_stops_without_a_traceback |

One earlier test asserted the old IPv6 form: `test_qa_fixes::test_names_with_digits_that_are_not_numbers_stay_host_names`
expected `::ffff:1.2.3.4` for `[::ffff:1.2.3.4]`; it now expects `::ffff:102:304`, the
form Node gives.

Disputed findings: none.

Fix commit: the commit that adds this section, on top of e5cb908.

Gates at 5df78c2: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on Elena's
PC (CPython 3.14.2, turn elena/6, low priority, clean clone of 5df78c2, fetched sources
absent, so their tests and the opt-in e2e test skip): 784 tests, 761 passed, 23 skipped,
none failed.

### Round 8

The five lenses ran again against b42791b (the third round of the second full pass).
Lens b confirmed F1, F2, F3, N1 and N2 fixed and the `"` dispute still valid; lens e
confirmed all twelve round 7 findings fixed, killed all 16 re-applied mutants, and swept
33 new probes (21 killed, one equivalent: removing `sys.stderr.flush()`, as stderr is line
buffered and every message ends in a newline). Every new finding is fixed below; none is
disputed. Each behaviour fix has a contract in `tests/test_qa8_fixes.py` that failed on
b42791b first (21 of its 37 cases failed; the 16 that passed pin cases already right or
the lens e mutants, which pass on b42791b and fail on their mutant). Expected hosts and
paths were measured on this PC with Node.js 24.18.0 `new URL(...)`. Every behaviour change
is in the 1.0.0 section of the CHANGELOG and in the GUIDE.

| Lens | Finding | Fix |
| --- | --- | --- |
| a, b | A-R3-1, B-N4: the port was never read, so `https://x.com:abc/`, `:99999` and `https://u:p\@x.com/` (authority ending at the backslash, port `p`) gave a host where the URL parser throws | `_url._valid_port`: the port after the host (bracketed or not) must be empty or ASCII digits up to 65535, and anything after `]` must start with `:`; otherwise `CookieError("the request URL is malformed")`. An explicit check, so the rule is the WHATWG one and is pinned by its own mutants. `test_qa8_fixes::test_a_url_with_an_invalid_port_is_malformed` (9 URLs, through `receive` and `matches`, each throws in Node), `test_a_valid_or_empty_port_is_accepted` (empty, 0, 65535, a bracketed host with a port) |
| b, d | B-N3, D-R2: only leading C0 controls and space were stripped | `str.strip` instead of `lstrip` (constant renamed `_STRIPPED`), before tab, LF and CR are removed, as the WHATWG parser orders it; `test_qa8_fixes::test_c0_controls_and_spaces_are_stripped_at_both_ends` (10 URLs: trailing space, two spaces, U+0001, tab and space, in the host and the path, both ends with NUL), `test_matches_strips_a_trailing_space_of_the_url` |
| d | R1: `http://[::1]\x` raised `CookieError` because the raw URL went through `urlsplit` before the backslash rewrite | the special scheme is read with a regular expression (`[A-Za-z][A-Za-z0-9+.-]*:`, case folded) and the rewrite runs before the only `urlsplit`; `test_qa8_fixes::test_a_backslash_may_follow_a_bracketed_host` (4 URLs, upper-case scheme included) |
| e | E1, E2: `http`, `ftp` and `ws` not pinned as special schemes | `test_qa8_fixes::test_every_special_scheme_reads_a_backslash_as_a_slash` (all five schemes, `x.com\a/b` and `x.com\@evil.com/p/q`) |
| e | E3: the leading strip not pinned | covered by `test_c0_controls_and_spaces_are_stripped_at_both_ends` (leading space and U+0001 before a URL with a backslash) |
| e | E4: removal of tab, LF and CR not pinned | `test_qa8_fixes::test_tab_and_newlines_are_removed_from_the_scheme` (each inside `https` of a URL with a backslash) |
| e | E5: the stderr form of several failing lines not pinned | `test_qa8_fixes::test_every_failing_line_gets_its_own_stderr_line` (exact two lines) |

Each mutant applied alone to a scratch copy with bytecode off, against
`tests/test_qa8_fixes.py` and `tests/test_qa7_fixes.py` on CPython 3.13.2 (this PC):

| Mutant | Caught by |
| --- | --- |
| S09 `http` removed from the special schemes | test_qa8_fixes::test_a_backslash_may_follow_a_bracketed_host |
| S08 `ftp` removed | test_qa8_fixes::test_every_special_scheme_reads_a_backslash_as_a_slash |
| S11 `ws` removed | test_qa8_fixes::test_every_special_scheme_reads_a_backslash_as_a_slash |
| S01 space not stripped | test_qa8_fixes::test_c0_controls_and_spaces_are_stripped_at_both_ends |
| S02 strip removed | test_qa8_fixes::test_c0_controls_and_spaces_are_stripped_at_both_ends |
| strip back to `lstrip` | test_qa8_fixes::test_c0_controls_and_spaces_are_stripped_at_both_ends |
| S03, S04, S05 tab, LF or CR kept | test_qa8_fixes::test_tab_and_newlines_are_removed_from_the_scheme |
| S06 `translate` removed | test_qa8_fixes::test_tab_and_newlines_are_removed_from_the_scheme |
| port check removed | test_qa8_fixes::test_a_url_with_an_invalid_port_is_malformed |
| port bound 65536 | test_qa8_fixes::test_a_url_with_an_invalid_port_is_malformed |
| `isascii` dropped from the port check | test_qa8_fixes::test_a_url_with_an_invalid_port_is_malformed |
| scheme compared without case folding | test_qa8_fixes::test_a_backslash_may_follow_a_bracketed_host |
| C04 newline dropped from each stderr message | test_qa8_fixes::test_every_failing_line_gets_its_own_stderr_line |
| C07 only the first failure reported | test_qa8_fixes::test_every_failing_line_gets_its_own_stderr_line |

One mutant survives on 3.13 and is equivalent there: dropping the check that only `:`
may follow `]`. On 3.11.4 and later `urlsplit` itself refuses `[::1]x`; the check is kept
for 3.10, where it is the only guard (checked on CPython 3.10.19: `http://[::1]x/`,
`http://[::1]:abc/`, `:+1`, a non-ASCII digit, `:65536` and `https://u:p\@x.com/` all
raise `CookieError`, while `http://[::1]\x/y` and a trailing space read as in Node).

Disputed findings: none.

Fix commit: 52d298f, on top of b42791b.

Gates at 52d298f: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on Elena's
PC (CPython 3.14.2, turn elena/8, low priority, clean clone of 52d298f, fetched sources
absent, so their tests and the opt-in e2e test skip): 823 tests, 800 passed, 23 skipped,
none failed.

### Round 9

Lenses d and e ran again against cb6915d (the fourth round of the second full pass).
Lens d confirmed R1 (a backslash after a bracketed host) and R2 (trailing C0 controls and
spaces) fixed in clean 3.14.2 venvs from the wheel, from the sdist and from PyPI 0.2.0
upgraded in place. Lens e confirmed E1 to E5 fixed, killed all 11 re-applied mutants, and
swept 30 new probes on `_url.py` (21 killed; three cannot fail the suite: P18 is
unobservable on 3.10, 3.13 and 3.14, where `urlsplit` itself refuses `[::1]x`, and killed
on 3.11.5, while P24 and P30 are equivalent). Every new finding is fixed below; none is
disputed. Each behaviour fix has a contract in `tests/test_qa9_fixes.py`: the four cases of
`test_brackets_in_the_userinfo_do_not_hide_the_host` with a `[` or `]` in the userinfo
failed on cb6915d first, and the other cases pin behaviour that was already right and fail
on their mutant. Expected hosts and paths were
measured on this PC with Node.js 24.18.0 `new URL(...)`; 0.2.0 (73f9d14) was run to
confirm it raised `CookieError` for the same URLs. The change is in the 1.0.0 section of
the CHANGELOG and in the GUIDE.

| Lens | Finding | Fix |
| --- | --- | --- |
| d | N1: a `[` or `]` in the userinfo made `urlsplit` raise, so `http://[::1]@a.com/p`, `http://[::1]:x@a.com/p`, `https://u[x]@a.com/` and `http://a]@b.com/` were refused where the URL parser reads the host `a.com` or `b.com` | `_url.request_of` drops the userinfo before `urlsplit`: an anchored regular expression takes an optional scheme, `//`, and the authority up to its last `@` before the first `/`, `?` or `#`, and keeps only the scheme and `//`. The port check and the bracket test then read `netloc` directly. Docstring and GUIDE; `test_qa9_fixes::test_brackets_in_the_userinfo_do_not_hide_the_host` (5 URLs, through `request_of`, `receive` and `matches`), `test_only_the_authority_loses_its_userinfo` (`@` in the query, fragment and path, `//u@` inside the path, another scheme, a scheme-relative URL, a userinfo before a bracketed host, a backslash before `@` in a special URL); `test_hostile::test_a_long_url_is_linear` gains a userinfo of `[a:` and a path of `//a`, each repeated up to 400 000 times |
| e | F1: the bracket branch of `_valid_port` not pinned (P20 `rest[2:]`, P29 `rpartition("]")`) | `test_qa9_fixes::test_a_bad_port_after_a_bracketed_host_is_malformed` (`[::1]:99999`, `:a`, `:65536`, `:]`, `:8]`, with and without a userinfo); each throws in Node |
| e | F2: dropping the userinfo before the port check not pinned (P22, P23) | `test_qa9_fixes::test_a_colon_in_the_userinfo_is_not_a_port` (`u:pw@`, `u:1@`, `u:@`, `a@b:x@`, `a:b@c:d@`, a userinfo before a valid port), each giving `x.com` as in Node. The code these mutants touched is replaced by the N1 fix, so the same cases now pin the new regular expression |
| e | F3: `_SCHEME` not pinned (P10 colon dropped, P09 `search`) | `test_qa9_fixes::test_a_special_scheme_needs_its_colon` (`http//x.com\a/b`, `https//x.com/a/b`, `wss x.com/a/b`, `http;//x.com/a/b`; each throws in Node, here `the request URL has no host`), `test_a_scheme_is_only_read_at_the_start_of_the_url` (`//x.com/http:\a`) |

Lens e also noted, outside its lens and not counted, that a scheme-relative URL such as
`//x.com/a` is accepted, where a WHATWG parser needs a base URL. Nothing is changed for it
in this round; it is left to the correctness lens, as lens e asked.

Each mutant applied alone to a copy of 1f98ac0 with bytecode off, against
`tests/test_qa9_fixes.py`, `test_qa8_fixes.py`, `test_qa7_fixes.py`, `test_qa7_pins.py`
and `test_hostile.py` (60 s per test), on CPython 3.14.6 on the laptop (turn portatil/1):

| Mutant | Caught by |
| --- | --- |
| P20 bracketed port read from `rest[2:]` | test_qa9_fixes::test_a_bad_port_after_a_bracketed_host_is_malformed |
| P29 `rpartition("]")` | test_qa9_fixes::test_a_bad_port_after_a_bracketed_host_is_malformed |
| P10 colon dropped from the scheme expression | test_qa9_fixes::test_a_special_scheme_needs_its_colon |
| P09 scheme searched, not matched | test_qa9_fixes::test_a_scheme_is_only_read_at_the_start_of_the_url |
| userinfo removal dropped | test_qa9_fixes::test_brackets_in_the_userinfo_do_not_hide_the_host |
| userinfo ends at the first `@` | test_qa9_fixes::test_a_colon_in_the_userinfo_is_not_a_port |
| `?` does not end the authority | test_qa9_fixes::test_only_the_authority_loses_its_userinfo |
| `#` does not end the authority | test_qa9_fixes::test_only_the_authority_loses_its_userinfo |
| `/` does not end the authority | test_qa9_fixes::test_only_the_authority_loses_its_userinfo |
| scheme required before `//` | test_qa9_fixes::test_only_the_authority_loses_its_userinfo |
| anchor dropped | test_qa9_fixes::test_only_the_authority_loses_its_userinfo (and quadratic time on the long userinfo) |

One mutant survives and is equivalent: removing `count=1` from the substitution, since an
expression anchored at the start of the string can match only once.

Disputed findings: none.

Fix commits: e8158de and 1f98ac0, on top of cb6915d.

Gates at 1f98ac0: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on the
laptop (CPython 3.14.6, turn portatil/1, low priority, clean clone of 1f98ac0, fetched
sources absent, so their tests and the opt-in e2e test skip): 855 tests, 832 passed,
23 skipped, none failed. The same run at e8158de on Elena's PC (CPython 3.14.2, turn
elena/7) also exited 0.

### Round 10

Lens e ran again against 072c242 (the fifth round of the second full pass). It confirmed
F1 to F3 fixed, killed all 6 re-applied mutants on CPython 3.14.2, and swept 28 new probes
on `_url.py` (15 killed, S14, S19 and S29 equivalent, S23 killed on 3.11.5 only). The six
survivors are fixed below; none is disputed. Five of them pin behaviour that was already
right; F8 is a behaviour change on Python 3.10 only, listed in the 1.0.0 section of the
CHANGELOG and in the GUIDE. Every contract is in `tests/test_qa10_fixes.py`. Expected hosts
and paths were measured on this PC with Node.js 24.18.0 `new URL(...)`, which gives the
listed host for every accepted URL, an empty host for `foo:/@/x.com/p` and `a:/u@/x.com/p`,
and throws for the other refused URLs.

| Lens | Finding | Fix |
| --- | --- | --- |
| e | F4: the scheme part of the userinfo expression not pinned (S06 lower case only, S07 letters only) | `test_the_userinfo_is_dropped_after_any_scheme`: `HTTPS://u:1@x.com/a/b`, `HTTP://[::1]@a.com/p`, `web+cal://u:1@x.com/a`, `foo1://u:1@x.com/a`, `a.b-c://u:1@x.com/a`, through `request_of`, `receive` and `matches` |
| e | F5: an empty userinfo not pinned (S08 `+@`) | same test: `https://@[::1]/a/b` (host `::1`) and `https://@x.com/a/b` |
| e | F6: a backslash in the userinfo of a non-special URL not pinned (S09) | same test: `foo://a:@x.com/a` and `foo://a:1@[::1]/a` |
| e | F7: the `//` of the userinfo expression not pinned (S10 `/+`) | `test_a_url_without_an_authority_has_no_host`: `foo:/@/x.com/p`, `/@/x.com/p`, `a:/u@/x.com/p`, each `the request URL has no host` |
| e | F8: on Python 3.10 `urlsplit` takes `1http` or `+a` as a scheme, so `receive("a=1", "1http://u@x.com/a")` stored the domain `x.com` there (0.2.0 did the same) while 3.11 and later raise `has no host`; S16, S17 and S28 survived the 3.10 suite | `_url.request_of` treats a URL as hostless when `urlsplit` returns a scheme that the scheme expression (an ASCII letter first) did not match, before the port check. `test_a_url_without_an_authority_has_no_host` gains `1http://u@x.com/a`, `+a://u@x.com/a`, `+a://x.com/a`, `1http://u:1@x.com/a` and `9://x.com/a`; on 3.10.19 four of them failed on 072c242 first (the colon case gave `malformed`) and all pass now on 3.10.19, 3.11.5, 3.13.2 and 3.14.2 |
| e | F9: `_valid_port` with a `[` inside the authority not pinned on 3.11.5 (S25) | `test_a_bracket_inside_the_host_is_malformed`: `http://x[::1]/` is `the request URL is malformed` on every version (on 3.10, 3.11.14 and later `urlsplit` raises first) |

Each mutant applied alone to a copy of 379fd58 with bytecode off, against
`tests/test_qa10_fixes.py`, on CPython 3.10.19, 3.11.5 and 3.13.2 on this PC (single file,
under a second per run):

| Mutant | 3.10.19 | 3.11.5 | 3.13.2 |
| --- | --- | --- | --- |
| S06 scheme `[a-z][a-z0-9+.-]*` | killed | killed | killed |
| S07 scheme `[A-Za-z][A-Za-z]*` | killed | killed | killed |
| S08 `*@` changed to `+@` | killed | killed | killed |
| S09 backslash added to the authority class | killed | killed | killed |
| S10 `//` changed to `/+` | killed | killed | killed |
| S25 `"[" in hostinfo` | equivalent (`urlsplit` raises first) | killed | equivalent |
| F8 fix removed (`hostless = False`) | killed | equivalent | equivalent |

S28 (a digit allowed first in the userinfo scheme) is equivalent after the fix: every URL
it changes starts with something other than a letter, which is now hostless with or
without the mutant (checked on 3.10.19 and 3.11.5 with `1http://u@x.com/a`,
`1http://u:1@x.com/a`, `9a://u:1@[::1]/a` and `0://@x.com/a`). S16 and S17 change how the
host is read from a netloc that still holds an `@`, which after the userinfo removal only
the 3.10 hostless URLs had, and those no longer reach that code; their re-run is left to
lens e.

Disputed findings: none.

Fix commit: 379fd58, on top of 072c242.

Gates at 379fd58: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2); `pytest` exits 0 on Elena's
PC (CPython 3.14.2, turn elena/7, clean clone of 379fd58, fetched sources absent, so their
tests and the opt-in e2e test skip): 872 tests, 848 passed, 24 skipped, none failed. The
URL test files (`test_qa6` to `test_qa10`, the pins, `test_store`, `test_wpt`,
`test_contract_edges`, 369 tests) also pass on CPython 3.10.19 and 3.11.5 on this PC.

### Round 11

Lens e ran again against 53b2d88 (the sixth round of the second full pass). It confirmed
F4 to F9 fixed on CPython 3.10.19, 3.11.5 and 3.13.2 and killed the re-applied S06 to S10
and S25 (on 3.11.5). It also showed S16 and S17 equivalent (0 differences in 60 000 seeded
URLs on each version). It swept 28 new probes on the hostless rule and on `_SCHEME`: 19
were killed, five were equivalent, and the three survivors are fixed below. None is
disputed. F10 is a behaviour change on Python 3.10 only, listed in the 1.0.0 section of
the CHANGELOG and in the GUIDE. Every contract is in `tests/test_qa11_fixes.py`.
Node.js 24.18.0 `new URL(...)` on this PC throws for every refused URL and gives the host
`x.com` and the path `/a` for both accepted ones.

| Lens | Finding | Fix |
| --- | --- | --- |
| e | F10: on Python 3.10, `urlsplit` raised `Invalid IPv6 URL` for a URL such as `1http://[/a` or `+a://x[/a` before the hostless rule ran, so it gave `the request URL is malformed` where 3.11 and later give `has no host`; S28 survived the 3.10 suite | `_url.request_of` now decides before `urlsplit` that a URL starting with a digit, `+`, `-` or `.` (after the ends are stripped) has no host. The rule that compared the scheme from `urlsplit` with the scheme expression is removed: such a URL never gets a host on any version, because `urlsplit` needs a scheme or a leading `//` to read an authority. `test_a_prefix_that_is_not_a_scheme_has_no_host`: `1http://[/a`, `+a://x[/a`, `9a://[@?q`, `1http://]/a`, `-a://u@[x/a`, `.a://[::1/a`, `1http://[x]/a`, `1http://[::1]x/a`, through `request_of` and `receive`. On 3.10.19, all eight failed on 53b2d88 first (`malformed`) |
| e | F11: a one-letter scheme not pinned (H23) | `test_a_scheme_may_be_one_letter`: `a://x.com/a` and `A://u@x.com/a` give `x.com` and `/a` through `request_of`, `receive` and `matches` |
| e | F12: a prefix starting with `-` or `.` not pinned on 3.10 (H28) | the same refused-URL test also covers `-a://x.com/a`, `.a://u@x.com/a`, `-://x.com/a` and `.://x.com/a` |

Each mutant was applied alone to a copy of f9eecd7 with bytecode off. It ran against
`tests/test_qa11_fixes.py`, `test_qa10_fixes.py`, `test_qa9_fixes.py`, `test_qa8_fixes.py`,
`test_qa7_fixes.py`, `test_qa7_pins.py` and `test_hostile.py` on CPython 3.10.19, 3.11.5 and
3.13.2 on this PC (single files, under a second per run):

| Mutant | 3.10.19 | 3.11.5 | 3.13.2 |
| --- | --- | --- | --- |
| early hostless check removed | killed | equivalent | equivalent |
| H28: `-` and `.` dropped from the first-character class | killed | equivalent | equivalent |
| digit dropped from the class | killed | equivalent | equivalent |
| `+` dropped | killed | equivalent | equivalent |
| `.` dropped | killed | equivalent | equivalent |
| `-` dropped | killed | equivalent | equivalent |
| letters added to the class | killed | killed | killed |
| class searched, not matched | killed | killed | killed |

On 3.11 and later, `urlsplit` itself takes no scheme that starts with anything but a letter,
so the early check only changes 3.10. Three mutants are now equivalent on every version.
Each gave 0 differences in 60 000 seeded URLs on 3.10.19, 3.11.5 and 3.13.2; a
control mutant (the early check removed) gave 25 on 3.10.19:

- S28 (the userinfo scheme may start with a digit): every URL it changes now stops at the
  early check.
- H23 (a scheme needs two characters): `_SCHEME` now only finds the five special schemes,
  and none of them has one letter. The new accept cases still pin the behaviour.
- The first-character class extended to `[0-9+.-][A-Za-z0-9+.-]*:`: this is the reason the
  rule is written as one character.

Disputed findings: none.

Fix commit: f9eecd7, on top of 53b2d88.

Gates at f9eecd7: `ruff format --check .`, `ruff check .`, `mypy --strict src` and
`mypy --strict src tests` exit 0 on this PC (CPython 3.13.2). `pytest` exits 0 on Elena's
PC (turn elena/9, clean clone of f9eecd7, fetched sources absent, so their tests and the
opt-in e2e test skip): 862 passed and 24 skipped, none failed, on CPython 3.14.2 and again
on CPython 3.10.19. The URL test files (`test_qa6` to `test_qa11`, the pins,
`test_store`, `test_wpt`, `test_contract_edges`, 383 tests) also pass on CPython 3.11.5 and
3.13.2 on this PC.

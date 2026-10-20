# setcookie 1.0.0 certification report

The 1.0.0 certification bar applied to setcookie. PyPI has 0.2.0, whose wheel modules are
byte for byte the `src/setcookie` of `main` at 73f9d14 (compared on 2026-10-20), so every
change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (73f9d14, same code as PyPI 0.2.0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Ground truth: sources fetched again, reference implementations run (item 7)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] Gates (item 15), final run
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

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

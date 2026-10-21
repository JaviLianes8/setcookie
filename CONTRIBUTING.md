# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/setcookie/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- The reference tests need the fetched specification files and two JavaScript
  implementations; without them they skip. Fetch them once with
  `python scripts/fetch_upstream.py` and
  `npm install --prefix tests/upstream/oracle --save-exact undici@8.12.3 tough-cookie@6.0.2`.
  `SETCOOKIE_E2E=1` adds the installed-wheel test, and `SETCOOKIE_E2E_PYPI=1` with it
  upgrades the PyPI release in place first.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.

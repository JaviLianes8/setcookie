"""Every docstring example of the package runs and prints what it shows."""

from __future__ import annotations

import doctest
import inspect

import pytest

import setcookie

METHODS = [
    setcookie.Cookie.header,
    setcookie.StoredCookie.is_expired,
    setcookie.StoredCookie.matches,
]


def _objects() -> list[object]:
    found: list[object] = [setcookie]
    found += [getattr(setcookie, name) for name in setcookie.__all__ if name != "SameSite"]
    return [*found, *METHODS]


@pytest.mark.parametrize(
    "target", _objects(), ids=lambda obj: getattr(obj, "__qualname__", "setcookie")
)
def test_the_docstring_examples_pass(target: object) -> None:
    finder = doctest.DocTestFinder(recurse=False)
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    name = getattr(target, "__name__", "setcookie")
    # Examples use the public names as `from setcookie import *` would bind them.
    globs = {key: getattr(setcookie, key) for key in setcookie.__all__}
    tests = finder.find(target, name, module=False, globs=globs)
    for test in tests:
        runner.run(test)
    assert runner.failures == 0
    assert runner.tries > 0


def test_every_public_name_has_a_docstring_with_an_example() -> None:
    for name in setcookie.__all__:
        if name == "SameSite":
            # A typing alias carries no docstring; the package docstring shows it in use.
            assert "SameSite" in (setcookie.__doc__ or "")
            continue
        doc = inspect.getdoc(getattr(setcookie, name)) or ""
        assert ">>> " in doc, name
    for method in METHODS:
        assert ">>> " in (inspect.getdoc(method) or ""), method

"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with SETCOOKIE_E2E=1. With
SETCOOKIE_E2E_PYPI=1 as well, the release on PyPI is installed first and upgraded in place.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("SETCOOKIE_E2E") != "1", reason="set SETCOOKIE_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources
from datetime import datetime, timezone
import setcookie
from setcookie import Cookie, CookieError, StoredCookie, build, expire, parse, parse_date, receive

assert "site-packages" in setcookie.__file__, setcookie.__file__
assert importlib.metadata.version("setcookie") == setcookie.__version__
assert importlib.resources.files("setcookie").joinpath("py.typed").is_file()

header = build("__Host-sid", "abc", max_age=60, secure=True, same_site="None", partitioned=True)
assert header == "__Host-sid=abc; Max-Age=60; Path=/; Secure; SameSite=None; Partitioned"
assert parse(header, strict=True).header() == header
assert expire("sid") == "sid=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/"
cookie = parse("test7; Max-Age=+5; Domain=.EX.com; Priority=High")
assert (cookie.name, cookie.value, cookie.max_age, cookie.domain) == ("", "test7", None, "ex.com")
assert cookie.extensions == (("Priority", "High"),)
assert parse_date("Fri Jan 01 03:14:07 2038") == datetime(2038, 1, 1, 3, 14, 7, tzinfo=timezone.utc)
now = datetime(2026, 10, 13, tzinfo=timezone.utc)
line = "a=1; Domain=example.com; Max-Age=999999999"
stored = receive(line, "https://www.example.com/x/y", now=now)
assert isinstance(stored, StoredCookie) and stored.path == "/x" and not stored.host_only
assert stored.matches("https://shop.example.com/x/z") and not stored.matches("https://example.org/x")
assert (stored.expiry - now).days == 400
for call in (
    lambda: build("sid", "a\r\nSet-Cookie: x=y"),
    lambda: build("__Secure-x", "1"),
    lambda: parse("sid=a\x00b"),
    lambda: parse("sid=abc; Max-Age=0", strict=True),
    lambda: receive("a=1; Secure", "http://h.test/", now=now),
):
    try:
        call()
    except CookieError as error:
        assert isinstance(error, ValueError)
    else:
        raise AssertionError("expected CookieError")
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("setcookie-*.whl")
    (sdist,) = dist.glob("setcookie-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "setcookie/py.typed" in names and "setcookie/__main__.py" in names
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in names)
    assert not any(name.startswith(("tests/", "scripts/")) for name in names)
    entry_points = next(name for name in names if name.endswith("entry_points.txt"))
    assert "setcookie = setcookie._cli:main" in zipfile.ZipFile(wheel).read(entry_points).decode()
    listing = _run(sys.executable, "-m", "tarfile", "-l", sdist).stdout.decode()
    assert "IMPROVEMENTS-round" not in listing and "upstream/wpt" not in listing
    assert "CERT-1.0" not in listing and "node_modules" not in listing
    assert "GUIDE.md" in listing and "LICENSE" in listing and "scripts/js_oracle.cjs" in listing
    assert "tests/upstream/MANIFEST.json" in listing
    assert ".txt" not in listing.replace("requirements-dev.txt", "")
    assert "tests/test_wpt.py" in listing and "scripts/fetch_upstream.py" in listing

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    if os.environ.get("SETCOOKIE_E2E_PYPI") == "1":
        _upgrade_from_pypi(python, tmp_path)
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.decode().strip() == "e2e ok"

    head = b"HTTP/2 200\r\nset-cookie: a=1; Path=/; Secure\r\nSet-Cookie: b=2\r\n\r\n"
    script = bindir / ("setcookie.exe" if sys.platform == "win32" else "setcookie")
    commands: list[list[str | Path]] = [[python, "-m", "setcookie"]]
    if os.environ.get("SETCOOKIE_E2E_NO_SCRIPT") != "1":
        commands.append([script])
    for command in commands:
        shown = _run(*command, "--url", "https://h.test/", cwd=work, stdin=head)
        assert shown.returncode == 0, shown.stderr
        report = json.loads(shown.stdout)
        assert [entry["stored"]["name"] for entry in report] == ["a", "b"]
        failed = _run(*command, "--strict", "sid=a b", cwd=work)
        assert failed.returncode == 1 and b"cookie-octet" in failed.stderr


OLD_PROGRAM = r"""
import importlib.metadata
from setcookie import CookieError, build, parse
assert importlib.metadata.version("setcookie") == "0.2.0"
assert build("sid", "abc", secure=True) == "sid=abc; Path=/; Secure"
try:
    build(1, "x")
except CookieError:
    print("0.2.0 ok")
"""


def _upgrade_from_pypi(python: Path, tmp_path: Path) -> None:
    """Install 0.2.0 from PyPI and check it, so the wheel below upgrades it in place."""
    old = _run(python, "-m", "pip", "install", "-q", "--no-cache-dir", "setcookie==0.2.0")
    assert old.returncode == 0, old.stderr
    work = tmp_path / "old"
    work.mkdir()
    result = _run(python, "-I", "-c", OLD_PROGRAM, cwd=work)
    assert result.stdout.decode().strip() == "0.2.0 ok", result.stderr

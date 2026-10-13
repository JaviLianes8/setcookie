from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


def read_upstream(name: str) -> str:
    """Return a third-party reference file as text.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their
    tests skip while a file is absent and fail if it differs from the manifest.
    """
    path = UPSTREAM / name
    if not path.is_file():
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    entry = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))[name]
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"{name} differs from MANIFEST"
    return body.decode("utf-8")


def _unpaginated(text: str) -> str:
    """Drop the page footers and headers of an RFC or draft so sections read as one block."""
    lines = [
        line
        for line in text.splitlines()
        if not line.startswith(("Bingler, et al.", "Internet-Draft  ", "Barth  ", "RFC 6265  "))
        and "\f" not in line
    ]
    return "\n".join(lines)


@pytest.fixture(scope="session")
def rfc6265() -> str:
    """RFC 6265, see tests/upstream/MANIFEST.json for its source."""
    return _unpaginated(read_upstream("rfc6265.txt"))


@pytest.fixture(scope="session")
def draft() -> str:
    """draft-ietf-httpbis-rfc6265bis-22, see tests/upstream/MANIFEST.json for its source."""
    return _unpaginated(read_upstream("draft-ietf-httpbis-rfc6265bis-22.txt"))


@pytest.fixture(scope="session")
def chips() -> str:
    """The partitioned cookies draft, see tests/upstream/MANIFEST.json for its source."""
    return _unpaginated(read_upstream("draft-cutler-httpbis-partitioned-cookies-01.txt"))

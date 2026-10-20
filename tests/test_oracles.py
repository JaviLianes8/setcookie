"""Cross-check against two independent implementations run live: undici and tough-cookie.

undici (the HTTP client behind Node.js fetch) follows the parsing algorithm of the draft;
tough-cookie (the cookie jar of jsdom) follows the storage and retrieval models. Both are
installed into the ignored tests/upstream/oracle folder and driven by scripts/js_oracle.cjs:

    npm install --prefix tests/upstream/oracle --save-exact undici@8.12.3 tough-cookie@6.0.2

The tests skip while Node.js or that folder is absent. Where an implementation knowingly
departs from the draft, the inputs avoid that corner; each corner is named below.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from setcookie import Cookie, CookieError, parse, receive
from setcookie._dates import format_http_date

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "tests" / "upstream" / "oracle"
VERSIONS = {"undici": "8.12.3", "tough-cookie": "6.0.2"}
NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)

# undici reads Expires with JavaScript's Date, not the cookie date algorithm, so only
# IMF-fixdates and junk are generated; it keeps an earlier SameSite after an unknown
# value, so only the three known values are generated (in any case).
ATTRIBUTES = [
    "Max-Age=60", "max-age=-5", "Max-Age=+5", "Max-Age=1x", "Max-Age=", "MAX-AGE=0",
    "Max-Age=-", "Max-Age=--5", "Max-Age=123456789012", "Domain=Example.COM",
    "domain=.a.b", "Domain=", "Domain=.", "Path=/", "path=/x/y", "Path=rel", "Path=",
    "Secure", "secure=1", "HttpOnly", "SameSite=Lax", "samesite=STRICT", "SameSite=none",
    "Partitioned", "Priority=High", "x", "=v", "", " Domain = a.com ", "Expires=junk",
    "Path=/" + "p" * 1100, "a\t=\tb", "Expires=",
]  # fmt: skip
PAIRS = [
    "sid=abc", "a=", "=b", "nameless", " x = y ", "a=b=c", '"q"="w"', "", "  ", "=",
    "n=" + "v" * 4094,
]  # fmt: skip


def _run(cases: dict[str, Any]) -> dict[str, Any]:
    node = shutil.which("node")
    if node is None or not (ORACLE / "node_modules").is_dir():
        pytest.skip("Node.js or tests/upstream/oracle is absent; see the module docstring")
    script = ROOT / "scripts" / "js_oracle.cjs"
    done = subprocess.run(
        [node, script, ORACLE], input=json.dumps(cases).encode(), capture_output=True, check=True
    )
    result: dict[str, Any] = json.loads(done.stdout)
    assert result["versions"] == VERSIONS
    return result


def _fixdate(rng: random.Random) -> str:
    return format_http_date(NOW + timedelta(seconds=rng.randrange(-(10**9), 10**9)))


def _lines(seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    lines = []
    for _ in range(count):
        avs = [rng.choice(ATTRIBUTES) for _ in range(rng.randint(0, 6))]
        avs += [f"Expires={_fixdate(rng)}"] * (rng.random() < 0.3)
        rng.shuffle(avs)
        lines.append(";".join([rng.choice(PAIRS), *(rng.choice(["", " "]) + a for a in avs)]))
    return lines


def _ours(line: str) -> dict[str, Any] | None:
    try:
        cookie: Cookie = parse(line)
    except CookieError:
        return None
    extensions = [f"{key}={text or ''}" for key, text in cookie.extensions]
    return {
        "name": cookie.name,
        "value": cookie.value,
        "expires": cookie.expires.timestamp() if cookie.expires else None,
        "maxAge": cookie.max_age,
        "domain": cookie.domain,
        "path": "/" if cookie.path == "" else cookie.path,
        "secure": cookie.secure,
        "httpOnly": cookie.http_only,
        "sameSite": cookie.same_site,
        "partitioned": cookie.partitioned,
        "unparsed": extensions,
    }


def _theirs(found: dict[str, Any] | None) -> dict[str, Any] | None:
    # undici does not refuse an empty name with an empty value (step 5 of section 5.6),
    # keeps an empty Domain as "", puts Partitioned and attributes with an empty name
    # into "unparsed", and uses "/" where the draft says "the default path".
    if found is None or found["name"] == found["value"] == "":
        return None
    unparsed = [item for item in found.pop("unparsed") if not item.startswith("=")]
    found["partitioned"] = any(item.lower().startswith("partitioned=") for item in unparsed)
    found["unparsed"] = [i for i in unparsed if not i.lower().startswith("partitioned=")]
    found["domain"] = found["domain"] or None
    return found


@pytest.mark.parametrize("seed", [7, 2026])
def test_parse_agrees_with_undici(seed: int) -> None:
    lines = _lines(seed, 6000)
    result = _run({"parse": lines})
    for line, found in zip(lines, result["parse"], strict=True):
        assert _ours(line) == _theirs(found), line


HOSTS = [
    "example.com", ".example.com", "www.example.com", "EXAMPLE.COM", "other.org",
    "x.www.example.com", "",
]  # fmt: skip
URLS = [
    "https://www.example.com/x/y/z", "https://www.example.com/", "http://www.example.com/x/",
    "https://example.com/x", "https://x.www.example.com/", "https://www.example.com",
]  # fmt: skip
TARGETS = [*URLS, "https://www.example.com/x", "https://www.example.com/xy", "https://other.org/"]


def _store_cases(seed: int, count: int) -> list[list[Any]]:
    rng = random.Random(seed)
    cases: list[list[Any]] = []
    while len(cases) < count:
        avs = [f"Domain={rng.choice(HOSTS)}"] * (rng.random() < 0.5)
        avs += [f"Path={rng.choice(['/', '/x', '/x/y', 'rel', ''])}"] * (rng.random() < 0.5)
        avs += [flag for flag in ("Secure", "HttpOnly") if rng.random() < 0.4]
        name = rng.choice(["a=b", "__Secure-a=b", "__Host-a=b", "nameless"])
        url = rng.choice(URLS)
        if "Secure" in avs and url.startswith("http:"):
            continue  # tough-cookie stores a Secure cookie from an insecure URL (5.7 step 13)
        if name.startswith("__Host-") and not any(a.startswith("Path=") for a in avs):
            continue  # tough-cookie does not require the Path attribute (5.7 step 21.3)
        cases.append(["; ".join([name, *avs]), url, TARGETS])
    return cases


@pytest.mark.parametrize("seed", [11, 4242])
def test_storage_and_retrieval_agree_with_tough_cookie(seed: int) -> None:
    cases = _store_cases(seed, 3000)
    result = _run({"store": cases})
    stored_count = 0
    for (line, url, targets), found in zip(cases, result["store"], strict=True):
        try:
            ours = receive(line, url, now=NOW)
        except CookieError:
            assert found["stored"] is None, (line, url)
            continue
        assert found["stored"] is not None, (line, url, found["error"])
        stored_count += 1
        theirs = found["stored"]
        assert (ours.name, ours.value, ours.domain, ours.host_only, ours.path) == (
            theirs["name"], theirs["value"], theirs["domain"], theirs["hostOnly"], theirs["path"]
        ), (line, url)  # fmt: skip
        assert (ours.secure, ours.http_only) == (theirs["secure"], theirs["httpOnly"])
        assert [ours.matches(target) for target in targets] == found["sent"], (line, url)
    assert stored_count > 800

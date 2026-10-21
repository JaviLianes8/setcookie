"""Request URLs: the canonical host and path a browser derives from them (section 5.1.2)."""

from __future__ import annotations

import ipaddress
import re
from typing import NamedTuple
from urllib.parse import unquote_to_bytes, urlsplit

from ._chars import shown
from ._errors import CookieError, type_error

_SECURE_SCHEMES = frozenset({"https", "wss"})
# The special schemes of the WHATWG URL Standard that have a host (``file`` aside).
_SPECIAL_SCHEMES = frozenset({"ftp", "http", "https", "ws", "wss"})
# What is stripped from both ends (C0 controls and space) or removed first, as the WHATWG
# URL parser does.
_STRIPPED = "".join(chr(code) for code in range(0x21))
_SCHEME = re.compile("([A-Za-z][A-Za-z0-9+.-]*):")
_REMOVED = str.maketrans("", "", "\t\n\r")
# The forbidden domain code points of the WHATWG URL Standard.
_FORBIDDEN = frozenset(chr(code) for code in range(0x20)) | frozenset(" #%/:<>?@[\\]^|\x7f")
# The path percent-encode set; every code point above U+007E is encoded as well.
_PATH_ENCODED = frozenset(chr(code) for code in range(0x20)) | frozenset(' "#<>?^`{}')
_DOTS = re.compile("[.\u3002\uff0e\uff61]")  # the label separators of the IDNA codec
_SINGLE_DOT = frozenset({".", "%2e"})
_DOUBLE_DOT = frozenset({"..", ".%2e", "%2e.", "%2e%2e"})


class Request(NamedTuple):
    host: str
    path: str
    secure: bool


def request_of(url: str) -> Request:
    """Split a request URL into its canonical host, path and whether it is secure.

    The host is percent-decoded, held to the DNS lengths (253 characters, labels of 63)
    before any IDNA work, converted with the standard library's IDNA 2003 codec, which maps
    a few characters (such as sharp s) differently from the IDNA 2008 rules of section
    5.1.2, and refused when it holds a forbidden domain code point of the WHATWG URL
    Standard. A trailing dot is kept, so ``example.com.`` is a host of its own as in
    browsers, and a host whose last label is a number is read as an IPv4 address the way
    the WHATWG URL parser reads it (``127.1`` is ``127.0.0.1``). The path is percent-encoded
    and its dot segments resolved as that parser does. In an ``http``, ``https``, ``ws``,
    ``wss`` or ``ftp`` URL a backslash in the authority or path reads as a slash and any
    number of slashes may follow the scheme, as in that parser. A bracketed host must be an
    IPv6 address without a zone ID and is serialized as that parser does (``[0:0::1]`` is
    ``::1``). As in that parser, C0 controls and spaces are stripped from both ends, tab and
    newlines removed, and a port must be empty or a number from 0 to 65535.
    """
    if not isinstance(url, str):
        raise type_error("url", "a str", url)
    url = str.__str__(url).strip(_STRIPPED).translate(_REMOVED)
    scheme = _SCHEME.match(url)
    if scheme and scheme.group(1).lower() in _SPECIAL_SCHEMES:
        url = _special(url, len(scheme.group(1)))
    try:
        parts = urlsplit(url)
        host = parts.hostname
        if not _valid_port(parts.netloc.rpartition("@")[2]):
            raise ValueError("the port is not a number from 0 to 65535")
    except ValueError as error:
        raise CookieError("the request URL is malformed") from error
    if not host:
        raise CookieError("the request URL has no host")
    try:
        if parts.netloc.rpartition("@")[2].startswith("["):
            canonical = _ipv6(host)
        else:
            canonical = _domain(host)
    except (ValueError, OverflowError):
        raise CookieError(f"the request host cannot be canonicalized: {shown(host)}") from None
    return Request(canonical, _path(parts.path), parts.scheme.lower() in _SECURE_SCHEMES)


def _special(url: str, length: int) -> str:
    """The URL with ``//`` after the scheme and a slash for every backslash."""
    # The parser keeps a backslash of the query or fragment, but neither reaches the host
    # or the path, so every backslash can be read as a slash.
    rest = url[length + 1 :].replace("\\", "/").lstrip("/")
    return f"{url[:length]}://{rest}"


def _valid_port(hostinfo: str) -> bool:
    """Whether the port after the host is empty or a number the URL parser accepts."""
    if hostinfo.startswith("["):
        rest = hostinfo.partition("]")[2]
        if rest and not rest.startswith(":"):
            return False
        port = rest[1:]
    else:
        port = hostinfo.partition(":")[2]
    return not port or (port.isascii() and port.isdigit() and int(port) <= 65535)


def _ipv6(host: str) -> str:
    """The WHATWG IPv6 serializer: lower-case pieces, the first longest zero run compressed."""
    if "%" in host:  # a zone ID: the URL parser refuses it
        raise ValueError("an IPv6 host has a zone ID")
    packed = ipaddress.IPv6Address(host).packed
    pieces = [f"{packed[index] << 8 | packed[index + 1]:x}" for index in range(0, 16, 2)]
    start, size, run = 0, 1, 0
    for index, piece in enumerate([*pieces, "end"]):
        if piece == "0":
            run += 1
        else:
            if run > size:
                start, size = index - run, run
            run = 0
    if size == 1:
        return ":".join(pieces)
    return ":".join(pieces[:start]) + "::" + ":".join(pieces[start + size :])


def _domain(host: str) -> str:
    host = unquote_to_bytes(host).decode("utf-8")
    labels = _DOTS.split(host)
    if len(labels) > 1 and not labels[-1]:
        labels.pop()
    # The punycode encoder is quadratic in the label length: bound the input first.
    if sum(map(len, labels)) + len(labels) - 1 > 253 or max(map(len, labels)) > 63:
        raise ValueError("the host is longer than DNS allows")
    canonical = host.encode("idna").decode("ascii").lower()
    # A label that claims to be an A-label must decode (section 5.1.2 step 4); a huge
    # one makes the punycode decoder raise OverflowError on some Python versions.
    canonical.encode("ascii").decode("idna")
    if any(char in _FORBIDDEN for char in canonical):
        raise ValueError("the host has a forbidden domain code point")
    return _ipv4(canonical) or canonical


def _path(path: str) -> str:
    """Percent-encode a path and resolve its dot segments, as the WHATWG URL parser does."""
    if not path.startswith("/"):
        return path
    encoded = "".join(_encoded(char) for char in path)
    segments: list[str] = []
    *head, last = encoded[1:].split("/")
    for segment in head:
        folded = segment.lower()
        if folded in _DOUBLE_DOT:
            if segments:
                segments.pop()
        elif folded not in _SINGLE_DOT:
            segments.append(segment)
    folded = last.lower()
    if folded in _DOUBLE_DOT and segments:
        segments.pop()
    segments.append("" if folded in _SINGLE_DOT | _DOUBLE_DOT else last)
    return "/" + "/".join(segments)


def _encoded(char: str) -> str:
    if char not in _PATH_ENCODED and char <= "~":
        return char
    if "\ud800" <= char <= "\udfff":
        char = "\ufffd"  # a lone surrogate is not a scalar value; URL parsers replace it
    return "".join(f"%{octet:02X}" for octet in char.encode("utf-8"))


def _ipv4_number(part: str) -> int | None:
    base = 10
    if part[:2] == "0x":
        base, part = 16, part[2:]
    elif len(part) > 1 and part[0] == "0":
        base, part = 8, part[1:]
    if not part:
        return 0
    if part.strip("0123456789abcdef"[:base]):
        return None
    return int(part, base)


def _ipv4(host: str) -> str | None:
    """The WHATWG URL host parser: a host that ends in a number is an IPv4 address."""
    labels = host.split(".")
    if len(labels) > 1 and not labels[-1]:
        labels.pop()
    last = labels[-1]
    if ":" in host or not last or (last.strip("0123456789") and _ipv4_number(last) is None):
        return None
    numbers = [_ipv4_number(label) if label else None for label in labels]
    if len(numbers) > 4 or None in numbers:
        raise ValueError("not an IPv4 address")
    *head, tail = (number for number in numbers if number is not None)
    if any(number > 255 for number in head) or tail >= 256 ** (5 - len(numbers)):
        raise ValueError("an IPv4 part is out of range")
    for index, number in enumerate(head):
        tail += number << (8 * (3 - index))
    return str(ipaddress.IPv4Address(tail))

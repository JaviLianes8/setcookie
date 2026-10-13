"""Read the test arrays out of the web-platform-tests cookie pages.

The pages hold JavaScript arrays of ``{cookie, expected, name, defaultPath}`` objects.
This reader evaluates the small subset of JavaScript they use: string, template and
array literals, ``+``, ``.repeat(n)``, ``.slice(n)``, booleans, numbers and the
``cookieStringWithNameAndValueLengths`` helper of ``cookies/resources/cookie-test.js``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Case:
    cookie: tuple[str, ...]
    expected: str
    name: str
    default_path: bool


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0"}


class _Reader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def skip(self) -> None:
        while True:
            match = re.compile(r"(?:\s+|//[^\n]*)").match(self.text, self.pos)
            if not match or match.end() == self.pos:
                return
            self.pos = match.end()

    def take(self, token: str) -> bool:
        self.skip()
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def string(self, quote: str) -> str:
        out: list[str] = []
        while (char := self.text[self.pos]) != quote:
            self.pos += 1
            if char == "\\":
                char = self.text[self.pos]
                self.pos += 1
                if char == "u":
                    char = chr(int(self.text[self.pos : self.pos + 4], 16))
                    self.pos += 4
                out.append(_ESCAPES.get(char, char))
            elif quote == "`" and char == "$" and self.text[self.pos] == "{":
                self.pos += 1
                out.append(str(self.expression()))
                assert self.take("}")
            else:
                out.append(char)
        self.pos += 1
        return "".join(out)

    def primary(self) -> Any:
        self.skip()
        char = self.text[self.pos]
        if char in "'\"`":
            self.pos += 1
            return self.string(char)
        if self.take("["):
            items = []
            while not self.take("]"):
                items.append(self.expression())
                self.take(",")
            return items
        word = re.compile(r"[A-Za-z0-9_]+").match(self.text, self.pos)
        assert word, self.text[self.pos : self.pos + 40]
        self.pos = word.end()
        if word[0] in ("true", "false"):
            return word[0] == "true"
        if word[0].isdigit():
            return int(word[0])
        assert word[0] == "cookieStringWithNameAndValueLengths" and self.take("(")
        name_length = self.expression()
        assert self.take(",")
        value_length = self.expression()
        assert self.take(")")
        return "t" * name_length + "=" + "1" * value_length

    def postfix(self) -> Any:
        value = self.primary()
        while self.take("."):
            method = re.compile(r"[a-z]+").match(self.text, self.pos)
            assert method and method[0] in ("repeat", "slice")
            self.pos = method.end()
            assert self.take("(")
            argument = self.expression()
            assert self.take(")")
            value = value * argument if method[0] == "repeat" else value[argument:]
        return value

    def expression(self) -> Any:
        value = self.postfix()
        while self.take("+"):
            value = value + self.postfix()
        return value

    def objects(self) -> list[dict[str, Any]]:
        assert self.take("[")
        found = []
        while not self.take("]"):
            assert self.take("{")
            entry: dict[str, Any] = {}
            while not self.take("}"):
                self.skip()
                key = re.compile(r"[A-Za-z]+").match(self.text, self.pos)
                assert key
                self.pos = key.end()
                assert self.take(":")
                entry[key[0]] = self.expression()
                self.take(",")
            found.append(entry)
            self.take(",")
        return found


def cases(page: str) -> list[Case]:
    """Every case of the first ``const ...Tests = [...]`` array in a test page."""
    start = re.search(r"const \w+Tests = ", page)
    assert start, "no test array in the page"
    reader = _Reader(page)
    reader.pos = start.end()
    found = []
    for entry in reader.objects():
        cookie = entry["cookie"]
        found.append(
            Case(
                cookie=tuple(cookie) if isinstance(cookie, list) else (cookie,),
                expected=entry["expected"],
                name=entry["name"],
                default_path=entry.get("defaultPath", True),
            )
        )
    return found


def name_loop(page: str) -> list[str]:
    """The names of the ``for (const name of [...])`` loop that follows the array."""
    start = re.search(r"for \(const name of ", page)
    assert start, "no name loop in the page"
    reader = _Reader(page)
    reader.pos = start.end()
    names = reader.expression()
    assert isinstance(names, list)
    return [str(name) for name in names]

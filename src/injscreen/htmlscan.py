"""HTML-aware hidden-text extraction (B2).

Splits HTML into visible and hidden text. Hidden text is anything a human reader
of the rendered page would not see: comments, elements styled to be invisible,
elements marked hidden for assistive tech, and attribute text such as `alt`,
`title`, and `<meta content>`. The screen checks hidden text separately, because
instructions placed there are a strong sign of injection.

This is a heuristic parser, not a browser. Inline CSS only, no stylesheets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

_LOOKS_LIKE_HTML = re.compile(r"<[a-zA-Z!/][^>]*>")

_HIDDEN_STYLE = re.compile(
    r"display\s*:\s*none"
    r"|visibility\s*:\s*hidden"
    r"|font-size\s*:\s*0(?![.\d])"
    r"|opacity\s*:\s*0(?![.\d])"
    r"|left\s*:\s*-\d{3,}"
    r"|text-indent\s*:\s*-\d{3,}"
    r"|color\s*:\s*(#fff(fff)?|white)\b",
    re.IGNORECASE,
)

_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
     "param", "source", "track", "wbr"}
)


@dataclass(frozen=True)
class Split:
    visible: str
    hidden: str


def looks_like_html(text: str) -> bool:
    return bool(_LOOKS_LIKE_HTML.search(text))


class _Splitter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.visible: list[str] = []
        self.hidden: list[str] = []
        # Stack of (tag, hidden) for open elements, so hidden subtrees end correctly.
        self._stack: list[tuple[str, bool]] = []

    def _in_hidden(self) -> bool:
        return any(h for _, h in self._stack)

    def _sink(self, text: str) -> None:
        if not text.strip():
            return
        (self.hidden if self._in_hidden() else self.visible).append(text)

    def handle_starttag(self, tag, attrs):
        attr = {k: (v or "") for k, v in attrs}
        style = attr.get("style", "")
        is_hidden = (
            bool(_HIDDEN_STYLE.search(style))
            or "hidden" in attr
            or attr.get("aria-hidden", "").lower() == "true"
        )
        for key in ("alt", "title"):
            if attr.get(key):
                self.hidden.append(attr[key])
        if tag == "meta" and attr.get("content"):
            self.hidden.append(attr["content"])
        if tag not in _VOID:
            self._stack.append((tag, is_hidden))

    def handle_startendtag(self, tag, attrs):
        # Self-closing tags such as <img/> have no content to track.
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        self._sink(data)

    def handle_comment(self, data):
        if data.strip():
            self.hidden.append(data)


def split(text: str) -> Split:
    parser = _Splitter()
    parser.feed(text)
    parser.close()
    return Split(
        visible=" ".join(parser.visible).strip(),
        hidden=" ".join(parser.hidden).strip(),
    )

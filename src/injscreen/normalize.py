"""Normalisation variants (B1).

Attackers hide vocabulary from pattern matching with Unicode look-alikes,
invisible characters, spaced letters, and encodings. `variants` returns the raw
text plus a few normalised and decoded views. The screen runs its rules on all
of them, so a phrase hidden in any one view is still found.

Kept deliberately small: a handful of homoglyphs, not a full confusables table.
"""

from __future__ import annotations

import base64
import binascii
import html
import re
import unicodedata
from urllib.parse import unquote

# A few common Cyrillic/Greek/other look-alikes for Latin letters.
_HOMOGLYPHS = str.maketrans(
    {
        "А": "A", "І": "I", "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
        "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g", "ο": "o",
        "α": "a", "ε": "e", "ι": "i", "ν": "v", "τ": "t",
    }
)

_INVISIBLE = re.compile("[​-‏‪-‮⁠⁦-⁩﻿]")
_SPACED = re.compile(r"\b(?:[A-Za-z] ){3,}[A-Za-z]\b")
_B64_TOKEN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def _printable_ratio(s: str) -> float:
    if not s:
        return 0.0
    good = sum(1 for c in s if c.isprintable() or c in "\n\t")
    return good / len(s)


def _decode_base64_tokens(text: str) -> list[str]:
    decoded: list[str] = []
    for token in _B64_TOKEN.findall(text):
        try:
            raw = base64.b64decode(token, validate=True)
            candidate = raw.decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if _printable_ratio(candidate) >= 0.9:
            decoded.append(candidate)
    return decoded


def variants(text: str) -> list[tuple[str, str]]:
    """Return (label, text) views of the input. The first view is always raw."""
    out: list[tuple[str, str]] = [("raw", text)]

    folded = unicodedata.normalize("NFKC", text).translate(_HOMOGLYPHS)
    folded = _INVISIBLE.sub("", folded)
    folded = _SPACED.sub(lambda m: m.group(0).replace(" ", ""), folded)
    if folded != text:
        out.append(("normalized", folded))

    unquoted = unquote(text)
    if unquoted != text:
        out.append(("percent", unquoted))

    unescaped = html.unescape(text)
    if unescaped != text:
        out.append(("entity", unescaped))

    decoded = _decode_base64_tokens(text)
    if decoded:
        out.append(("base64", "\n".join(decoded)))

    return out

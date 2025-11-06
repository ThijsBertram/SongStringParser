from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Pattern, Sequence, Dict, Any, Iterable
from songstring_parser.conf import ParserConfig

# =========================================================
# Helpers (shared)
# =========================================================

_SEP_ONLY_RX = re.compile(r"^[\s\-\–\—_/|:;,.]+$")
_ZW_RX       = re.compile(r"[\u200B-\u200D\uFEFF]")
_WS_RX       = re.compile(r"\s+")
ARTIST_SEP_RX = re.compile(r"\s*(?:,|&|and|\+|x|×)\s*", re.IGNORECASE)

def is_effectively_empty(text: str) -> bool:
    if not text or not text.strip():
        return True
    return bool(_SEP_ONLY_RX.match(text))

def normalize_inner(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = _ZW_RX.sub("", t)
    t = _WS_RX.sub(" ", t).strip()
    return t

def word_alternatives(terms: Sequence[str], flexible_space: bool = True) -> str:
    # longest first so "vip mix" beats "vip"
    terms = sorted(terms, key=len, reverse=True)
    alts = []
    for t in terms:
        is_regexy = bool(re.search(r"[\\\[\]\(\)\^\$\.\*\+\?\{\}\|]|\\d|\\s", t))
        if is_regexy:
            alts.append(t)
        else:
            parts = t.split()
            glue = r"\s+" if flexible_space else r"\s*"
            alts.append(glue.join(re.escape(p) for p in parts))
    return "(?:" + "|".join(alts) + ")"

def _join_escaped_with_whitespace(parts: Iterable[str], flexible_space=True) -> str:
    glue = r"\s+" if flexible_space else r"\s*"
    return glue.join(re.escape(p) for p in parts if p)

def _tidy_name(s: str) -> str:
    return s.strip(" -:()[]{}\"'\t")


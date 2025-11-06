from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional, Pattern, Sequence
from songstring_parser.conf import ParserConfig


# GET CONFIG
pc = ParserConfig()
BRACKET_PAIRS = pc.bracket_pairs
FEAT_INDICATORS = pc.feat_indicators
VERSION_INDICATORS = pc.version_indicators
NOISE_INDICATORS = pc.noise_indicators
LIVE_INDICATORS = pc.live_indicators

@dataclass
class ParseResult:
    raw: str
    cleaned: str
    feat: str
    feat_artist: str
    remix_artist: str
    version: str
    extension: str
    bitrate: str
    harvested: List[Harvested]
    noise: List[str]
    
# Models
@dataclass
class Harvested:
    raw: str           
    text: str         
    type: str  # ["version", "remix", "feat", "live", "noise", "unknown"]        
    artist: Optional[str] = None  
    version: Optional[str] = None 
    span: _Span = None

@dataclass
class ClassifierPatterns:
    feat_leading : Pattern
    feat_trailing : Pattern
    version_rx: Pattern
    byline_type_by_name_rx  : Pattern
    byline_indicator_name_rx  : Pattern
    byline_possessive_rx : Pattern
    byline_name_type_rx : Pattern
    live_rx: Pattern
    noise_rx: Pattern
    noise_full_rx: Pattern
    original_mix_rx: Pattern

@dataclass
class _Span:
    start: int
    end: int          # end is exclusive (points to char AFTER the closing bracket)
    l: str            # opening bracket char
    r: str            # closing bracket char
    depth: int        # 1-based nesting depth at the time of match

# ================
# HELPERS
# ================
def _is_effectively_empty(text: str) -> bool:
    if not text or not text.strip():
        return True
    _SEP_ONLY_RX = re.compile(r"^[\s\-\–\—_/|:;,.]+$")

    return bool(_SEP_ONLY_RX.match(text))

def _find_spans_nested(s: str, pairs: List[Tuple[str, str]]) -> List[_Span]:
    openers = {l: r for (l, r) in pairs}
    closers = {r: l for (l, r) in pairs}
    stack: List[Tuple[str, int]] = []
    spans: List[_Span] = []

    for i, ch in enumerate(s):
        if ch in openers:
            stack.append((ch, i))
        elif ch in closers:
            if stack and stack[-1][0] == closers[ch]:
                lch, pos = stack.pop()
                depth = len(stack) + 1  # depth when this pair closes
                spans.append(_Span(start=pos, end=i+1, l=lch, r=ch, depth=depth))
            else:
                # mismatched closer; ignore
                continue
    return spans

# ================
# CONSTRUCT REGEX
# ================

def word_alternatives(terms, flexible_space=True) -> str:
    # longest first so "radio edit" beats "edit"
    terms = sorted(terms, key=len, reverse=True)
    alts = []
    for t in terms:
        # if you truly want to allow regex terms verbatim:
        is_regexy = bool(re.search(r"[\\\[\]\(\)\^\$\.\*\+\?\{\}\|]|\\d|\\s", t))
        if is_regexy:
            alts.append(t)
        else:
            parts = t.split()  # split on whitespace
            glue = r"\s+" if flexible_space else r"\s*"
            alts.append(glue.join(re.escape(p) for p in parts))
    return "(?:" + "|".join(alts) + ")"


def _join_escaped_with_whitespace(parts, flexible_space=True) -> str:
    glue = r"\s+" if flexible_space else r"\s*"
    return glue.join(re.escape(p) for p in parts if p)

def build_noise_alt(
    literal_terms: Sequence[str],
    regex_terms: Sequence[str],
    flexible_space: bool = True,
) -> str:
    """
    Search-mode alternation:
      - literals: \b<escaped words joined by \s+>\b
      - regex terms: inserted as-is (they manage their own boundaries)
    """
    alts = []
    for t in literal_terms:
        lit = _join_escaped_with_whitespace(t.split(), flexible_space)
        alts.append(rf"\b{lit}\b")
    alts.extend(regex_terms)  # prebuilt regex fragments
    return "(?:" + "|".join(alts) + ")"

def build_noise_fullmatch_alt(
    literal_terms: Sequence[str],
    regex_terms: Sequence[str],
    flexible_space: bool = True,
    allow_quotes: bool = False,
) -> str:
    """
    Fullmatch-mode alternation (use with ^(?:... )$):
      - literals: ^ (optional quotes) <escaped words joined by \s+> (optional quotes) $
      - regex terms: inserted as-is, optionally wrapped with quotes
    """
    alts = []
    q = r"""["'“”‘’]?\s*""" if allow_quotes else ""
    for t in literal_terms:
        lit = _join_escaped_with_whitespace(t.split(), flexible_space)
        alts.append(rf"{q}(?:{lit}){q}")
    alts.extend([rf"{q}(?:{rx}){q}" for rx in regex_terms])
    return "(?:" + "|".join(alts) + ")"

def compile_classifiers() -> ClassifierPatterns:
    # FEAT
    feat_alt = word_alternatives(FEAT_INDICATORS)
    # feat_leading 
    feat_names_leading_rx  = re.compile(rf"^(?:{feat_alt})\s*[:\-]?\s*(?P<names>.+?)\s*$", re.IGNORECASE)
    # feat trailing
    feat_names_trailing_rx = re.compile(rf"^(?P<names>.+?)\s*(?:{feat_alt})\s*[:\-]?\s*$", re.IGNORECASE)

    # ORIGINAL MIX
    # Use a strict match for "original mix" to let you null it later
    original_mix_rx = re.compile(r"\boriginal\s*mix\b", re.IGNORECASE)

    # --- Live ---
    # We allow 'live' + (at|in|@ ...) as a special case; other live terms come from config
    live_terms = [t for t in LIVE_INDICATORS if t.lower() != "live"]
    live_extra_alt = word_alternatives(live_terms) if live_terms else r"(?!x)x"  # never matches if empty
    live_rx = re.compile(
        rf"\b(?:live(?:\s+(?:at|in|@)\b.*)?|{live_extra_alt})\b", re.IGNORECASE
    )

    # NOISE
    BITRATE_RX = r"\d{2,3}\s*(?:kbps|kb/s|kbit/s|k)"
    VBR_RX = r"V[0-9]"
    CBR_VBR_WORDS_RX = r"(?:CBR|VBR)" # UNNECESSARY

    NOISE_REGEXES = [
        r"\bcat[#-]\S+\b",                # cat#XYZ-012 or cat-202
        r"\btrack\d{1,2}\b",              # Track07
        r"\bkey\s+[A-G][#b]?\d?\b",       # key 8A, key 12, key F#m...
        r"\b\d{2,3}\s*bpm\b",             # 124bpm, 90 bpm
        r"\b" + BITRATE_RX + r"\b",       # 320kbps, 128k, 192 kb/s...
        r"\b" + VBR_RX + r"\b",           # V0, V2, etc.
        r"\b" + CBR_VBR_WORDS_RX + r"\b", # CBR or VBR words
    ]

    # compile both
    noise_alt_search = build_noise_alt(NOISE_INDICATORS, NOISE_REGEXES)               # your existing builder
    noise_alt_full   = build_noise_fullmatch_alt(NOISE_INDICATORS, NOISE_REGEXES)     # NEW

    noise_rx        = re.compile(noise_alt_search, re.IGNORECASE)                   # .search
    noise_full_rx   = re.compile(rf"^(?:{noise_alt_full})$", re.IGNORECASE)         # .fullmatch equivalent

    version_alt = word_alternatives(VERSION_INDICATORS)
    version_only_inner_rx = re.compile(rf"^(?P<type>{version_alt})$", re.IGNORECASE)

    # version_anywhere_inner_rx = re.compile(rf"\b(?P<type>{version_alt})\b", re.IGNORECASE)  # optional fallback


    # 1) Type-by-name: "Bootleg by Barry", "Edit by Jane"
    byline_type_by_name_rx  = re.compile(
    rf"(?P<type>{version_alt})\s+by\s+(?P<name>.+?)\b",
    re.IGNORECASE
)

    # 2) Indicator + name (optional parenthesized type): "Remixed by MK", "Edited by Jane (VIP Mix)"
    byline_alt = word_alternatives(VERSION_INDICATORS)  # e.g. ["remixed by", "edited by", "remix by", "edit by", "bootleg by"]
    byline_indicator_name_rx  = re.compile(
        rf"(?:{byline_alt})\s+(?P<name>.+?)\b(?:\s*\((?P<type>.+?)\))?",
        re.IGNORECASE
    )

    # 3) Possessive: "Z's Edit" / "Z’s Edit"
    byline_possessive_rx  = re.compile(
        rf"(?P<name>.+?)['’]\s*(?P<type>{version_alt})\b",
        re.IGNORECASE
    )

    # 4) Name + Type **(last resort only)**: "Bicep Rework", "DJ City Edit"
    # We'll guard it at classification time (see below).
    byline_name_type_rx  = re.compile(
        rf"(?P<name>.+?)\s+(?P<type>{version_alt})\b",
        re.IGNORECASE
    )




    return ClassifierPatterns(
        feat_leading=feat_names_leading_rx,
        feat_trailing=feat_names_trailing_rx,
        version_rx=version_only_inner_rx,
        byline_type_by_name_rx=byline_type_by_name_rx,
        byline_indicator_name_rx=byline_indicator_name_rx,
        byline_possessive_rx=byline_possessive_rx,
        byline_name_type_rx =byline_name_type_rx ,
        live_rx=live_rx,
        noise_rx=noise_rx,
        noise_full_rx=noise_full_rx,
        original_mix_rx=original_mix_rx,
    )

# ================
# HELPER FUNCS
# ================
def _classify(text: str, patterns: ClassifierPatterns) -> Harvested:
    t = text.strip()
    print(f"TEXT TO MATCH: {t}")


    def _tidy_name(s: str) -> str:
        return s.strip(" -:()[]{}\"'\t")
    
    # Feat (strong, early)
    if (patterns.feat_leading.search(t)
            or patterns.feat_trailing.search(t)):

        print("DETECTED: FEAT")

        m = (patterns.feat_leading.search(t)
            or patterns.feat_trailing.search(t))
        feat_names_raw = m.group("names") if m and m.groupdict().get("names") else ""
        feat_names = _tidy_name(feat_names_raw)
        return Harvested(raw="", text=t, type="feat", artist=feat_names or None)
            
       
    # Live
    if patterns.live_rx.search(t):
        print("DETECTED: LIVE ")
        return Harvested(raw="", text=t, type="live")

    # ORIGINAL
    if patterns.original_mix_rx.search(t):
        return Harvested(raw="", text=t, type="version", version="Original Mix")
    
  # 4) STRICT version-only — entire inner text is a version token (e.g., "Radio Edit")
    m = patterns.version_rx.search(t)
    if m:
        print("DETECTED: VERSION")
        v = " ".join(w.capitalize() for w in m.group("type").split())
        return Harvested(raw="", text=t, type="version", version=v)

    # 5) remixer bylines (always capture version if present)
    for rx in (patterns.byline_type_by_name_rx, patterns.byline_indicator_name_rx, patterns.byline_possessive_rx):
        m = rx.search(t)
        if m:
            name = _tidy_name(m.group("name")) if m.groupdict().get("name") else None
            v = m.groupdict().get("type")
            if not v:
                # If indicator form had no explicit (type), try to infer from the matched prefix
                # E.g., for "Remixed by MK" set version="Remix"
                # Do a targeted search anchored at the start
                head = t.lower()
                for tok in sorted(VERSION_INDICATORS, key=len, reverse=True):
                    if head.startswith(tok.lower()):
                        v = tok
                        break
            if v:
                v = " ".join(w.capitalize() for w in v.split())
            return Harvested(raw="", text=t, type="remix", artist=name or None, version=v or None)

    # 6) guarded name+type (last resort, avoid "Live Version" → byline)
    m = patterns.byline_name_type_rx.search(t)
    if m:
        candidate_name = m.group("name").strip()
        # Guard: if the "name" itself is a known version/live word, do NOT treat as byline
        if not (patterns.version_rx.search(candidate_name) or patterns.live_rx.search(candidate_name)):
            v = " ".join(w.capitalize() for w in m.group("type").split())
            name = _tidy_name(candidate_name)
            return Harvested(raw="", text=t, type="remix", artist=name, version=v)

    # Noise (scene)
        # after live/version/byline checks
    if patterns.noise_full_rx.fullmatch(t):
        return Harvested(raw="", text=t, type="noise")
    if patterns.noise_rx.search(t):
        return Harvested(raw="", text=t, type="noise")

    # Unknown
    return Harvested(raw="", text=t, type="unknown")

# ================
# PARSER
# ================
def parse_brackets_nested(base: str) -> tuple[str, list]:
    """
    Nested-aware bracket harvesting using a progressive removal mask.
    Innermost spans are classified first; already-harvested inner brackets
    are *not* present when classifying an outer bracket.
    """
    patterns = compile_classifiers()
    spans = _find_spans_nested(base, BRACKET_PAIRS)

    # Process deepest -> shallowest; for identical depth, left-to-right
    order = sorted(range(len(spans)), key=lambda i: (-spans[i].depth, spans[i].start))

    # mask of what is still "visible" in the working string
    alive = [True] * len(base)

    harvested: List[Harvested] = []
    for idx in order:
        sp = spans[idx]

        # Build the current inner text (children may already be removed)
        inner_chars = [
            base[i] for i in range(sp.start + 1, sp.end - 1)
            if 0 <= i < len(alive) and alive[i]
        ]
        inner_text = re.sub(r"\s{2,}", " ", "".join(inner_chars)).strip()

        # If empty (or separator-only) after child removal: don't harvest, just remove
        if _is_effectively_empty(inner_text):
            for i in range(sp.start, sp.end):
                if 0 <= i < len(alive):
                    alive[i] = False
            continue  # skip appending a Harvested

        # Classify on pruned inner text
        h = _classify(inner_text, patterns)

        # Reconstruct raw *without* already removed children
        raw_now = sp.l + (inner_text if inner_text else "") + sp.r

        h.raw = raw_now
        h.text = inner_text
        h.span = sp
        harvested.append(h)

        # Now remove this span from alive view (so parents won't see it)
        for i in range(sp.start, sp.end):
            if 0 <= i < len(alive):
                alive[i] = False

    # Build cleaned base: everything not inside any bracket (mask still alive)
    cleaned = "".join(ch for i, ch in enumerate(base) if alive[i])
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    return cleaned, harvested
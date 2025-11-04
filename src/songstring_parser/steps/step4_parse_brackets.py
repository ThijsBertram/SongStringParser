from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional, Pattern, Sequence
from songstring_parser.conf import ParserConfig



# TO DO:
# - nested brackets
# - refactor remix_byline into version_artist (r'by' optional in the pattern)
# - change logical order of bracket parsing

# GET CONFIG
pc = ParserConfig()
BRACKET_PAIRS = pc.bracket_pairs
FEAT_INDICATORS = pc.feat_indicators
VERSION_INDICATORS = pc.version_indicators
NOISE_INDICATORS = pc.noise_indicators
LIVE_INDICATORS = pc.live_indicators


# Models
@dataclass
class Harvested:
    raw: str           
    text: str         
    kind: str         
    cls: str          
    name: Optional[str] = None  
    version: Optional[str] = None 

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
    original_mix_rx: Pattern

# ================
# CONSTRUCT REGEX
# ================
def word_alternatives(terms, flexible_space=True) -> str:
    # longest first so "radio edit" beats "edit"
    terms = sorted(terms, key=len, reverse=True)
    alts = []
    for t in terms:
        is_regexy = bool(re.search(r"[\\\[\]\(\)\^\$\.\*\+\?\{\}\|]|\\d|\\s", t))
        if not is_regexy:
            t = re.escape(t)
            t = re.sub(r"\s+", r"\\s+" if flexible_space else r"\\s*", t)
        alts.append(t)
    return "(?:" + "|".join(alts) + ")"



def build_noise_alt(
    literal_terms: Sequence[str],
    regex_terms: Sequence[str],
    flexible_space: bool = True,
) -> str:
    """
    Build a single alternation (?: ... ) for noise detection.
    - Literals are escaped and wrapped with \b...\b
    - Spaces in literals become \s+ (or \s*) for robustness
    - Regex terms are inserted as-is (no escaping, no global \b wrapping)
    """
    alts = []

    # literals: escape + flexible spaces + \b term \b
    for t in literal_terms:
        esc = re.escape(t)
        if flexible_space:
            esc = re.sub(r"\s+", r"\\s+", esc)
        # wrap literals with word boundaries
        alts.append(rf"\b{esc}\b")

    # regex terms: included as-is
    alts.extend(regex_terms)

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
    noise_alt = build_noise_alt(NOISE_INDICATORS, NOISE_REGEXES)
    noise_rx = re.compile(noise_alt, re.IGNORECASE)


    # VERSION
    # TODO: 
    # - only version, no artist
    # - version_artist + version_by_artist (by optional in regex pattern)
    # - artist_version
    # - artist_version_possessive



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
        original_mix_rx=original_mix_rx,
    )
# ================
# HELPER FUNCS
# ================
def _find_first_balanced(s: str) -> Optional[Tuple[int, int, str, str]]:
    """
    Find leftmost, shortest balanced bracket pair among (), [], {}.
    Returns (start, end, left_char, right_char) for the first found, else None.
    """
    best = None
    for l, r in BRACKET_PAIRS:
        i = s.find(l)
        if i == -1:
            continue
        # naive balanced search forward
        depth = 0
        for j in range(i, len(s)):
            if s[j] == l:
                depth += 1
            elif s[j] == r:
                depth -= 1
                if depth == 0:
                    cand = (i, j + 1, l, r)
                    if best is None or i < best[0] or (i == best[0] and (j + 1 - i) < (best[1] - best[0])):
                        best = cand
                    break
    return best


def _classify(text: str, patterns: ClassifierPatterns) -> Harvested:
    t = text.strip()

    def _tidy_name(s: str) -> str:
        return s.strip(" -:()[]{}\"'\t")
    
    # Feat (strong, early)
    if (patterns.feat_leading.search(t)
            or patterns.feat_trailing.search(t)):
        
        m = (patterns.feat_leading.search(t)
            or patterns.feat_trailing.search(t))
        feat_names_raw = m.group("names") if m and m.groupdict().get("names") else ""
        feat_names = _tidy_name(feat_names_raw)
        return Harvested(raw="", text=t, kind="", cls="feat", name=feat_names or None)
            
       
    # Live
    if patterns.live_rx.search(t):
        print("DETECTED: live")

        return Harvested(raw="", text=t, kind="", cls="live")

    # ORIGINAL
    if patterns.original_mix_rx.search(t):
        print("DETECTED: og")

        return Harvested(raw="", text=t, kind="", cls="remix_version", version="Original Mix")
    
  # 4) STRICT version-only — entire inner text is a version token (e.g., "Radio Edit")
    m = patterns.version_rx.fullmatch(t)
    if m:
        v = " ".join(w.capitalize() for w in m.group("type").split())
        return Harvested(raw="", text=t, kind="", cls="remix_version", version=v)

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
            return Harvested(raw="", text=t, kind="", cls="remixer_byline", name=name or None, version=v or None)

    # 6) guarded name+type (last resort, avoid "Live Version" → byline)
    m = patterns.byline_name_type_rx.search(t)
    if m:
        candidate_name = m.group("name").strip()
        # Guard: if the "name" itself is a known version/live word, do NOT treat as byline
        if not (patterns.version_rx.search(candidate_name) or patterns.live_rx.search(candidate_name)):
            v = " ".join(w.capitalize() for w in m.group("type").split())
            name = _tidy_name(candidate_name)
            return Harvested(raw="", text=t, kind="", cls="remixer_byline", name=name, version=v)

    # Noise (scene)
    if patterns.noise_rx.search(t):
        print("DETECTED: noise")

        return Harvested(raw="", text=t, kind="", cls="noise")

    # Unknown
    return Harvested(raw="", text=t, kind="", cls="unknown")

# ================
# PARSER
# ================
def parse_brackets(base: str) -> Tuple[str, List[Harvested]]:
    """
    Iteratively remove bracketed segments in order of appearance.
    Returns (cleaned_string, segments)
    """
    patterns = compile_classifiers()
    harvested: List[Harvested] = []
    s = base
    c = 0
    while True:

        found = _find_first_balanced(s)
        if not found:
            break
        i, j, l, r = found
        raw = s[i:j]
        inner = raw[1:-1].strip()

        h = _classify(inner, patterns)
        h.raw = raw
        h.kind = f"{l}{r}"
        harvested.append(h)
        # Remove the segment and normalize any leftover double spaces
        s = (s[:i] + " " + s[j:]).strip()
        s = re.sub(r'\s{2,}', ' ', s)
        c += 1

    return s, harvested

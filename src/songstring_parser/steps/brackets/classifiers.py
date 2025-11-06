from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Pattern, Sequence, Dict, Any, Iterable
from songstring_parser.conf import ParserConfig
from abc import ABC, abstractmethod
from songstring_parser.steps.brackets.models import Harvested
from songstring_parser.steps.brackets.helpers import word_alternatives, _join_escaped_with_whitespace, _tidy_name

class BaseClassifier(ABC):
    name: str

    def __init__(self, cfg: ParserConfig = ParserConfig):
        self.cfg = cfg
        self.patterns = self.compile()


    @abstractmethod
    def compile(self) -> List[re.Pattern]:
        self._compiled = True
        return
    
    @abstractmethod
    def classify(self, text: str) -> Optional[Harvested]:
        return
    

class LiveClassifier(BaseClassifier):
    name = "live"

    def compile(self):

        live_indicators = self.cfg.live_indicators

        # --- Live ---
        # We allow 'live' + (at|in|@ ...) as a special case; other live terms come from config
        live_terms = [t for t in live_indicators if t.lower() != "live"]
        live_extra_alt = word_alternatives(live_terms) if live_terms else r"(?!x)x"  # never matches if empty
        live_rx = re.compile(
            rf"\b(?:live(?:\s+(?:at|in|@)\b.*)?|{live_extra_alt})\b", re.IGNORECASE
        )

        return [live_rx]

    def classify(self, text):
        t = text.strip()
        for pattern in self.patterns:
            if pattern.search(t):
                return Harvested(raw="", text=t, type="live")
        return 


class FeatClassifier(BaseClassifier):
    name = 'feat'

    def compile(self):

        feat_indicators = self.cfg.feat_indicators

        # FEAT
        feat_alt = word_alternatives(feat_indicators)
        # feat_leading 
        feat_names_leading_rx  = re.compile(rf"^(?:{feat_alt})\s*[:\-]?\s*(?P<names>.+?)\s*$", re.IGNORECASE)
        # feat trailing
        feat_names_trailing_rx = re.compile(rf"^(?P<names>.+?)\s*(?:{feat_alt})\s*[:\-]?\s*$", re.IGNORECASE)

        return [feat_names_leading_rx, feat_names_trailing_rx]
    
    def classify(self, text):
        t = text.strip()
        if any([pattern.search(t) for pattern in self.patterns]):
            m = next((m for rx in self.patterns if (m := rx.search(t))), None)
            feat_names_raw = m.group("names") if m and m.groupdict().get("names") else ""
            feat_names = _tidy_name(feat_names_raw)
            return Harvested(raw="", text=t, type="feat", artist=feat_names or None)
    

class RemixClassifier(BaseClassifier):
    name = 'remix'

    def compile(self):

        version_indicators = self.cfg.version_indicators

        version_alt = word_alternatives(version_indicators)
        version_only_inner_rx = re.compile(rf"^(?P<type>{version_alt})$", re.IGNORECASE)

        # 1) Type-by-name: "Bootleg by Barry", "Edit by Jane"
        byline_type_by_name_rx  = re.compile(
        rf"(?P<type>{version_alt})\s+by\s+(?P<name>.+?)\b",
        re.IGNORECASE
    )

        # 2) Indicator + name (optional parenthesized type): "Remixed by MK", "Edited by Jane (VIP Mix)"
        byline_alt = word_alternatives(version_indicators)  # e.g. ["remixed by", "edited by", "remix by", "edit by", "bootleg by"]
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

        return [version_only_inner_rx, byline_type_by_name_rx, byline_indicator_name_rx, byline_possessive_rx, byline_name_type_rx]
    
    def classify(self, text):

        t = text.strip()
        version_indicators = self.cfg.version_indicators

        # 4) VERSION ONLY (Radio Edit) / (Extended Mix)
        m = self.patterns[0].search(t)
        if m:
            print("DETECTED: VERSION")
            v = " ".join(w.capitalize() for w in m.group("type").split())
            return Harvested(raw="", text=t, type="version", version=v)
        

        # 5) remixer bylines (always capture version if present)
        for rx in (self.patterns[1], self.patterns[2], self.patterns[3]):
            m = rx.search(t)
            if m:
                name = _tidy_name(m.group("name")) if m.groupdict().get("name") else None
                v = m.groupdict().get("type")
                if not v:
                    # If indicator form had no explicit (type), try to infer from the matched prefix
                    # E.g., for "Remixed by MK" set version="Remix"
                    # Do a targeted search anchored at the start
                    head = t.lower()
                    for tok in sorted(version_indicators, key=len, reverse=True):
                        if head.startswith(tok.lower()):
                            v = tok
                            break
                if v:
                    v = " ".join(w.capitalize() for w in v.split())
                return Harvested(raw="", text=t, type="remix", artist=name or None, version=v or None)

        # 6) guarded name+type (last resort, avoid "Live Version" → byline)
        m = self.patterns[-1].search(t)
        if m:
            candidate_name = m.group("name").strip()
            # Guard: if the "name" itself is a known version/live word, do NOT treat as byline
            if not (any([indicator in candidate_name for indicator in self.cfg.version_indicators]) or any([indicator in candidate_name for indicator in self.cfg.live_indicators])):
                v = " ".join(w.capitalize() for w in m.group("type").split())
                name = _tidy_name(candidate_name)
                return Harvested(raw="", text=t, type="remix", artist=name, version=v)

        return
    

class NoiseClassifier(BaseClassifier):
    name = 'noise'

    def _build_noise_alt(self, literal_terms: Sequence[str], regex_terms: Sequence[str], flexible_space: bool = True) -> str:
        alts = []

        for t in literal_terms:
            lit = _join_escaped_with_whitespace(t.split(), flexible_space)
            alts.append(rf"\b{lit}\b")
        alts.extend(regex_terms)
        return "(?:" + "|".join(alts) + ")"

    def _build_noise_fullmatch_alt(self, literal_terms: Sequence[str], regex_terms: Sequence[str],
                                flexible_space: bool = True, allow_quotes: bool = True) -> str:
        alts = []
        q = r"""["'“”‘’]?\s*""" if allow_quotes else ""
        for t in literal_terms:
            lit = _join_escaped_with_whitespace(t.split(), flexible_space)
            alts.append(rf"{q}(?:{lit}){q}")
        alts.extend([rf"{q}(?:{rx}){q}" for rx in regex_terms])
        return "(?:" + "|".join(alts) + ")"

    def compile(self):
        
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

        NOISE_INDICATORS = self.cfg.noise_indicators

        # compile both
        noise_alt_search = self._build_noise_alt(NOISE_INDICATORS, NOISE_REGEXES)               # your existing builder
        noise_alt_full   = self._build_noise_fullmatch_alt(NOISE_INDICATORS, NOISE_REGEXES)     # NEW

        noise_rx        = re.compile(noise_alt_search, re.IGNORECASE)                   # .search
        noise_full_rx   = re.compile(rf"^(?:{noise_alt_full})$", re.IGNORECASE)         # .fullmatch equivalent

        return [noise_rx, noise_full_rx]
    
    def classify(self, text):
        t = text.strip()
        if self.patterns[0].fullmatch(t):
            return Harvested(raw="", text=t, type="noise")
        if self.patterns[1].search(t):
            return Harvested(raw="", text=t, type="noise")

        return
    

class UnknownClassifier(BaseClassifier):
    name = "unknown"

    def compile(self):
        return []
    
    def classify(self, text):

        t = text.strip()

        return Harvested(raw="", text=t, type="unknown")
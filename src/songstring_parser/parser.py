from typing import Optional, Dict, Any, List, Tuple

from src.conf import ParserConfig
from src.models import ParseResult, HarvestedSegment

class SongStringParser:
    """
    Multi-pass parser for messy song strings.
    Orchestrates a series of deterministic passes; each pass 'chips away' at complexity.
    """

    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()

        # Placeholders for precompiled regex, if desired later.
        self._compiled: Dict[str, Any] = {}

    # ---------- Public API ----------

    def parse(self, raw: str) -> ParseResult:
        """
        Orchestrates the full parsing pipeline. Each stage updates the working state.
        """
        state = {
            "raw": raw,
            "working": raw,
            "basename": None,
            "extension": None,
            "harvest": [],            # List[HarvestedSegment]
            "artist_block": None,
            "title_block": None,
            "main_artist": None,
            "artists_primary": [],    # main + co-primaries (no feats/remixers yet)
            "feat_artist": [],
            "remixer": [],
            "remix_type": None,
            "live": False,
            "debug": {}
        }

        # Stage 1: Path & extension peel
        self._strip_path_and_extension(state)

        # Stage 2: Unicode & spacing normalization
        self._normalize_unicode_and_spacing(state)

        # Stage 3: Track/disc index peel
        self._peel_track_disc_index(state)

        # Stage 4: Bracket harvest (iterative classification)
        self._harvest_and_classify_brackets(state)

        # Stage 5: Primary artist–title split resolution
        self._resolve_artist_title_split(state)

        # Stage 6: Artist block parse (primaries + inline features)
        self._parse_artist_block(state)

        # Stage 7: Title block parse (inline feat/remix/live + title cleanup)
        self._parse_title_block(state)

        # Stage 8: Consolidation & normalization
        self._consolidate_fields(state)

        # Stage 9: Final sanity checks / ambiguity guard
        self._final_sanity_checks(state)

        # Assemble final result
        result = ParseResult(
            main_artist=state["main_artist"] or "",
            artists=self._dedupe_preserve_order(
                state["artists_primary"] + state["feat_artist"] + state["remixer"]
            ),
            title=state["title_block"] or "",
            remix_type=state["remix_type"],
            remixer=self._dedupe_preserve_order(state["remixer"]),
            feat_artist=self._dedupe_preserve_order(state["feat_artist"]),
            extension=state["extension"],
            live=bool(state["live"]),
            debug=state.get("debug", {})
        )
        return result

    # ---------- Stage methods (placeholders) ----------

    def _strip_path_and_extension(self, state: Dict[str, Any]) -> None:
        """
        Keep only the basename; detect and remove audio extension.
        Set state['basename'], state['extension'], update state['working'].
        """
        raise NotImplementedError("_strip_path_and_extension")

    def _normalize_unicode_and_spacing(self, state: Dict[str, Any]) -> None:
        """
        Normalize dashes, tildes, pipes; collapse spaces; standardize bracket spacing.
        Update state['working'].
        """
        raise NotImplementedError("_normalize_unicode_and_spacing")

    def _peel_track_disc_index(self, state: Dict[str, Any]) -> None:
        """
        Remove leading album/track indices (e.g., '01.', '02-', 'CD2-').
        Preserve for debug if desired; update state['working'].
        """
        raise NotImplementedError("_peel_track_disc_index")

    def _harvest_and_classify_brackets(self, state: Dict[str, Any]) -> None:
        """
        Iteratively extract (...) / [...] / {...}, classify each into SegmentType,
        and append HarvestedSegment to state['harvest']. Remove from state['working'].
        """
        raise NotImplementedError("_harvest_and_classify_brackets")

    def _resolve_artist_title_split(self, state: Dict[str, Any]) -> None:
        """
        Decide where to split the string into artist_block and title_block.
        Use scoring/heuristics; attempt title-first fallback if needed.
        Set state['artist_block'], state['title_block'].
        """
        raise NotImplementedError("_resolve_artist_title_split")

    def _parse_artist_block(self, state: Dict[str, Any]) -> None:
        """
        Parse artist_block into main + co-primaries; move any inline features to feat_artist.
        Set state['main_artist'], extend state['artists_primary'], extend state['feat_artist'].
        """
        raise NotImplementedError("_parse_artist_block")

    def _parse_title_block(self, state: Dict[str, Any]) -> None:
        """
        From title_block and harvested segments:
        - Extract inline feats → extend feat_artist
        - Extract remix/remixer/version
        - Detect live
        - Clean residual noise from title
        Update state['title_block'], state['remix_type'], state['remixer'], state['live'].
        """
        raise NotImplementedError("_parse_title_block")

    def _consolidate_fields(self, state: Dict[str, Any]) -> None:
        """
        Merge/normalize lists, handle Original Mix policy, apply case/trim rules,
        and prepare for final checks.
        """
        raise NotImplementedError("_consolidate_fields")

    def _final_sanity_checks(self, state: Dict[str, Any]) -> None:
        """
        Guard against unresolved ambiguity or empty essentials; raise ParseError if needed.
        """
        raise NotImplementedError("_final_sanity_checks")

    # ---------- Helpers (can be filled later) ----------

    @staticmethod
    def _dedupe_preserve_order(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in items:
            key = x.lower()
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out

    def _classify_harvested_segment(self, raw_segment: str, bracket: str) -> HarvestedSegment:
        """
        Given a raw bracketed segment and bracket type, return a HarvestedSegment.
        Placeholder; final implementation will apply dictionaries from ParserConfig.
        """
        raise NotImplementedError("_classify_harvested_segment")

    def _score_splits(self, candidates: List[int], working: str) -> int:
        """
        Given candidate indices (positions of separators), return the chosen split index.
        Placeholder: will implement scoring based on artist/title likeness features.
        """
        raise NotImplementedError("_score_splits")

    def _extract_feat_from_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Remove feat-tail from text and return (clean_text, feat_artists).
        """
        raise NotImplementedError("_extract_feat_from_text")

    def _extract_remix_info_from_text(self, text: str) -> Tuple[str, Optional[str], List[str]]:
        """
        Return (clean_text, remix_type, remixers[]) from inline/title text.
        """
        raise NotImplementedError("_extract_remix_info_from_text")

    def _detect_live_from_text(self, text: str) -> Tuple[str, bool]:
        """
        Return (clean_text, live_flag) based on live keywords.
        """
        raise NotImplementedError("_detect_live_from_text")

    def _strip_noise_tokens(self, text: str) -> str:
        """
        Remove configured noise tokens (bitrate, catalog, promo tags, etc.).
        """
        raise NotImplementedError("_strip_noise_tokens")
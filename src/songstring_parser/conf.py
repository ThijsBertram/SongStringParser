from typing import Tuple, Dict
from dataclasses import dataclass, field

@dataclass
class ParserConfig:
    """Configuration knobs and synonym dictionaries."""

    # STEP 1 
    # Known audio file extensions (lowercased with leading dot)
    audio_extensions: Tuple[str, ...] = (".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".aiff", ".alac", ".wma")

    # STEP 2
    dashes_to_hyphen = {
        0x2010,  # hyphen
        0x2011,  # non-breaking hyphen
        0x2012,  # figure dash
        0x2013,  # en dash
        0x2014,  # em dash
        0x2015,  # horizontal bar
    }

    bracket_pairs = [
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("<", ">")
]


    # Synonyms / dictionaries (all matching should be case-insensitive at runtime)
    feat_indicators: Tuple[str, ...] = ("feat.", "ft.", "featuring", "with", "feat", "ft")

    version_indicators: Tuple[str, ...] = (
        "remix", "rmx", "edit", "version", "rework", "refix", "bootleg",
        "vip", "vip mix", "vip remix", "vip rmx", "vip version", 
        "dub", "dub mix", "club mix", "radio edit",
        "acoustic", "unplugged", "extended mix", "fix"
    )
    live_indicators: Tuple[str, ...] = (
        "live", "live version", "live at", "live in", "live @", "session"
    )


    noise_indicators: Tuple[str, ...] = (
        "official video", "visualizer", "vizualizer", "lyric video", "hq", "hd", "vbr",
        "videoclip", "official visualizer", "remastered", "remaster", "official remaster",
        "web", "promo", "unmastered", "final", 
        "purchase at beatport", "beatport exclusive", "sc-rip",
        "labelname", "promo cd", "label", "vinyl rip", "rip", "cd rip", "radio rip"
        # NOTE: removed "320kbps", "128k" here; those are now covered by regexes
        # NOTE: removed raw "key " and "bpm" because they’re too broad; better as regex (below)
    )


    # Artist connector policy
    split_connectors_spaced: Tuple[str, ...] = (" & ", " and ", " + ", " x ", " × ", " vs. ", ",")
    # Connectors that should NOT split when glued (e.g., 'CamelPhat&Elderbrook')
    treat_glued_connectors_as_single_token: bool = True

    # Policy toggles
    treat_original_mix_as_null: bool = True  # "Original Mix" → remix_type=None

    # Scoring weights (placeholder; used by split resolution)
    score_weights: Dict[str, float] = field(default_factory=lambda: {
        "artist_likeness": 1.0,
        "title_likeness": 1.0,
        "penalty_misplaced_tokens": 1.0
    })
from typing import Tuple, Dict
from dataclasses import dataclass, field

@dataclass
class ParserConfig:
    """Configuration knobs and synonym dictionaries."""
    # Known audio file extensions (lowercased with leading dot)
    audio_extensions: Tuple[str, ...] = (".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".aiff", ".alac", ".wma")

    # Synonyms / dictionaries (all matching should be case-insensitive at runtime)
    feat_synonyms: Tuple[str, ...] = ("feat.", "ft.", "featuring", "with")
    remix_words: Tuple[str, ...] = (
        "remix", "edit", "version", "rework", "refix", "bootleg",
        "vip", "vip mix", "dub", "dub mix", "club mix", "radio edit",
        "acoustic", "unplugged", "extended mix", "private remix",
        "sped up", "nightcore"
    )
    live_words: Tuple[str, ...] = (
        "live", "live version", "live at", "live in", "live @", "session",
        "tiny desk", "bbc", "boilerrm", "boiler room"
    )

    # Tokens considered "noise" (to discard from title/artist semantic parsing)
    noise_tokens: Tuple[str, ...] = (
        "official video", "visualizer", "lyric video", "hq", "hd", "vbr",
        "320kbps", "128k", "flac", "web", "promo", "unmastered", "final",
        "key ", "bpm", "purchase at beatport", "beatport exclusive", "sc-rip",
        "cat#", "cat-", "labelname", "promo cd"
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
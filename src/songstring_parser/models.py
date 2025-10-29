from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple, Dict, Any

@dataclass
class ParseResult:
    """Final normalized output for a parsed song string."""
    main_artist: str
    artists: List[str]
    title: str
    remix_type: Optional[str] = None
    remixer: List[str] = field(default_factory=list)
    feat_artist: List[str] = field(default_factory=list)
    extension: Optional[str] = None
    live: bool = False

    # Optional debug payload during development (not part of final schema)
    debug: Dict[str, Any] = field(default_factory=dict)


class SegmentType(Enum):
    """Classification of harvested bracketed segments."""
    FEAT = auto()
    REMIX_VERSION = auto()
    REMIXER_BYLINE = auto()
    LIVE = auto()
    TECHNICAL_NOISE = auto()
    UNKNOWN = auto()


@dataclass
class HarvestedSegment:
    """Represents a bracketed/parenthetical segment harvested during parsing."""
    raw: str
    clean: str
    bracket: str  # one of '()', '[]', '{}'
    seg_type: SegmentType
    payload: Dict[str, Any] = field(default_factory=dict)  # e.g., {"remixer": "X", "remix_type": "Edit"}


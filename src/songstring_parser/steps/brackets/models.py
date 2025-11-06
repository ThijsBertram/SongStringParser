from __future__ import annotations
import re
import unicodedata
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Pattern, Sequence, Dict, Any, Iterable
from songstring_parser.conf import ParserConfig

@dataclass
class ParseResult:
    raw: str = None
    cleaned: str = None
    feat: str = None
    feat_artist: str = None
    remix_artist: str = None
    version: str = None
    extension: str = None
    bitrate: str = None
    harvested: List[Harvested] = None
    noise: List[str] = None



class SegmentType(Enum):
    """Classification of harvested bracketed segments."""
    VERSION = auto()
    FEAT = auto()
    REMIX = auto()
    NOISE = auto()
    LIVE = auto()
    UNKNOWN = auto()



# Models
@dataclass
class Harvested:
    raw: str           
    text: str         
    type: SegmentType 
    artist: Optional[str] = None  
    version: Optional[str] = None 
    span: _Span = None

@dataclass
class _Span:
    start: int
    end: int          # end is exclusive (points to char AFTER the closing bracket)
    l: str            # opening bracket char
    r: str            # closing bracket char
    depth: int        # 1-based nesting depth at the time of match

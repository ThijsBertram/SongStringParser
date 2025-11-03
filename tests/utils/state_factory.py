from __future__ import annotations
from typing import Any, Dict

def empty_state(raw: str) -> Dict[str, Any]:
    return {
        "raw": raw,
        "working": raw,
        "basename": None,
        "extension": None,
        "harvest": [],            # list of HarvestedSegment
        "artist_block": None,
        "title_block": None,
        "main_artist": None,
        "artists_primary": [],
        "feat_artist": [],
        "remixer": [],
        "remix_type": None,
        "live": False,
        "debug": {},
    }

def clone_state(state: Dict[str, Any]) -> Dict[str, Any]:
    # shallow copy is fine for our usage; deep-copy harvest if you mutate items
    return {**state, "harvest": list(state.get("harvest", []))}

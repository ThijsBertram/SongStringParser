# tests/test_parser.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from songstring_parser.models import ParseResult
from songstring_parser.errors import ParseError  # useful when you add negative tests

DATA_PATH = Path(__file__).parent / "data" / "test_songs.json"


def _load_cases() -> list[Dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


CASES = _load_cases()
CASE_IDS = [case["song_string"] for case in CASES]


def _result_to_dict(res: ParseResult) -> Dict[str, Any]:
    """Map ParseResult to the golden schema (ignoring any debug fields)."""
    return {
        "main_artist": res.main_artist,
        "artists": res.artists,
        "title": res.title,
        "remix_type": res.remix_type,
        "remixer": res.remixer,
        "feat_artist": res.feat_artist,
        "extension": res.extension,
        "live": res.live,
    }


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_parser_golden(parser, case: Dict[str, Any]) -> None:
    """Golden tests: song_string → exact expected fields."""
    song_string = case["song_string"]
    expected = {k: v for k, v in case.items() if k != "song_string"}

    result = parser.parse(song_string)
    got = _result_to_dict(result)

    assert got == expected, (
        f"\nSong string: {song_string!r}\n"
        f"Expected: {expected}\n"
        f"Got:      {got}\n"
    )

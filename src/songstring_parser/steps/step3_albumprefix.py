import re 

from songstring_parser.conf import ParserConfig

from typing import Optional, Dict, Any, Tuple

# Compile anchored (start-of-string) patterns for speed/readability.
# Each pattern eats the prefix AND the delimiter run that follows.
_RX_PATTERNS = [
    # 1) CD/DISC + optional track:  "CD2 07 -", "Disc 1: 03_", "CD3-02__", "Disc2-"
    re.compile(
        r"""^
        (?:(?:CD|Disc|Disk)\s*(?P<disc>\d+))      # disc number
        (?:\s*[:\-._ ]\s*(?P<track>\d{1,3}))?     # optional track number after disc
        \s*[:\-._ ]*\s*                           # eat trailing separators/spaces
        """,
        re.IGNORECASE | re.VERBOSE,
    ),

    # 2) Side-letter + track: "A1 -", "B2_", "C10.", "D7 "
    re.compile(
        r"""^
        (?P<side>[A-D])\s*(?P<track>\d{1,2})
        \s*[:\-._ ]+\s*
        """,
        re.IGNORECASE | re.VERBOSE,
    ),

    # 3) Disc x Track patterns: "1x02 -", "2X7_", "1x2."
    re.compile(
        r"""^
        (?P<disc>\d{1,2})\s*[xX]\s*(?P<track>\d{1,3})
        \s*[:\-._ ]+\s*
        """,
        re.IGNORECASE | re.VERBOSE,
    ),

    # 4) Track with explicit delimiter: "01 -", "03.", "07__", "12 : "
    re.compile(
        r"""^
        (?P<track>\d{1,3})
        \s*[:\-._ ]+\s*
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
]

def clean_album_prefix(s: str, max_passes: int = 3) -> Tuple[str, Dict[str, Any]]:
    """
    Remove leading track/disc/album indices from the start of the string.
    Repeats up to `max_passes` to peel stacked prefixes (e.g., "CD2 07 - ").

    Returns:
        cleaned_string, info_dict  (info has 'disc', 'track', 'side' if found)
    """
    info: Dict[str, Any] = {"disc": None, "track": None, "side": None, "passes": 0}
    if not s:
        return s, info

    working = s.lstrip()  # be tolerant of leading spaces
    for _ in range(max_passes):
        matched_any = False
        for rx in _RX_PATTERNS:
            m = rx.match(working)
            if not m:
                continue
            matched_any = True
            gd = {k: v for k, v in m.groupdict().items() if v is not None}
            # Record the first disc/track/side seen (don’t overwrite once set)
            if "disc" in gd and info.get("disc") is None:
                info["disc"] = int(gd["disc"])
            if "track" in gd and info.get("track") is None:
                # keep as int when numeric
                try:
                    info["track"] = int(gd["track"])
                except ValueError:
                    info["track"] = gd["track"]
            if "side" in gd and info.get("side") is None:
                info["side"] = gd["side"].upper()
            # Consume the matched prefix
            working = working[m.end():].lstrip()
            info["passes"] += 1
            break  # restart pattern loop from the top on the new working string
        if not matched_any:
            break

    return working, info

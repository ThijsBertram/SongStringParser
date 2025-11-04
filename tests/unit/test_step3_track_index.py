import pytest
from songstring_parser.parser import SongStringParser
from songstring_parser.conf import ParserConfig
from songstring_parser.steps.step3_albumprefix import clean_album_prefix
from tests.utils.state_factory import *


@pytest.mark.unit
@pytest.mark.step3
@pytest.mark.parametrize(
    "raw,target",
    [
        # Simple numeric
        ("02-Artist A - Title", "Artist A - Title"),
        ("01. mainartist - title (Original mix).mp3", "mainartist - title (Original mix).mp3"),
        ("07__Unknown Artist - Untitled", "Unknown Artist - Untitled"),
        ("12 : Artist - Title", "Artist - Title"),

        # Disc/track forms
        ("CD2 07 - Artist - Title", "Artist - Title"),
        ("Disc 1: 03_ Artist - Title", "Artist - Title"),
        ("CD3-02__ M-zine & Scepticz - Song-title-example", "M-zine & Scepticz - Song-title-example"),

        # Side-letter forms
        ("A1 - Main Artist - Title", "Main Artist - Title"),
        ("B2_ Main Artist - Title", "Main Artist - Title"),
        ("C10. Main Artist - Title", "Main Artist - Title"),

        # Disc x Track
        ("1x02 - Main Artist - Title", "Main Artist - Title"),
        ("2X7_ Main Artist - Title", "Main Artist - Title"),

        # Stacked prefixes (peel repeatedly)
        ("CD2 07 __ 01 - Main Artist - Title", "Main Artist - Title"),

        # False flags
        ("7xBuroo - Title",  "7xBuroo - Title"),
        ('CDs Are the Future - Title', "CDs Are the Future - Title"),

        # Should leave regular strings untouched
        ("M-zine & Scepticz - Song title example", "M-zine & Scepticz - Song title example"),
        ("CamelPhatxElderbrook - Cola (Live @ Printworks London)", "CamelPhatxElderbrook - Cola (Live @ Printworks London)"),
    ]
)

def test_strip_path_and_extension(raw, target):


    normalized, info = clean_album_prefix(raw)

    assert normalized == target

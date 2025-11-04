import pytest
from songstring_parser.parser import SongStringParser
from songstring_parser.conf import ParserConfig
from songstring_parser.steps.step2_normalize import normalize_separators_whitespace
from tests.utils.state_factory import *

@pytest.mark.step2
@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,target",
    [
        ("Artist — Title ~ (Extended Mix)", "Artist - Title ~ (Extended Mix)"),
        ("Main Artist – Title [feat. Who?] – (Dub)", "Main Artist - Title [feat. Who?] - (Dub)"),
        ("CamelPhatxElderbrook - Cola (Live @ Printworks London)", "CamelPhatxElderbrook - Cola (Live @ Printworks London)"),
        ("CamelPhat&Elderbrook - Cola", "CamelPhat&Elderbrook - Cola"),
        ("Title   (  Remix  )  [  VIP ] { Edit }", "Title (Remix) [VIP] {Edit}"),
        ("Artist_Name-Title__Live-Version.mp3", "Artist_Name-Title__Live-Version.mp3"),
        ("A- B", "A - B"),
        ("A -B", "A - B"),
        ("A  --   B", "A - B"),
        ("A|B|C - Track - (Bootleg)", "A | B | C - Track - (Bootleg)")
    ]
)

def test_strip_path_and_extension(raw, target):
    
    dashes_to_hyphen = ParserConfig().dashes_to_hyphen

    normalized = normalize_separators_whitespace(raw, dashes_to_hyphen=dashes_to_hyphen)

    assert normalized == target

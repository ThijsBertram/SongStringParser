import pytest
from songstring_parser.parser import SongStringParser
from songstring_parser.conf import ParserConfig
from songstring_parser.steps.step1_strip_path_and_extension import strip_path_and_extension
from tests.utils.state_factory import *


pytestmark = pytest.mark.unit

@pytest.fixture
def parser() -> SongStringParser:
    return SongStringParser(ParserConfig())

@pytest.mark.parametrize(
    "raw,basename,ext",
    [
        ("ALBUM RIP\\CD2\\07_Unknown_Artist_-_Untitled_.flac", "07_Unknown_Artist_-_Untitled_", "flac"),
        ("/mnt/music/Artist - Title (Radio Edit).MP3", "Artist - Title (Radio Edit)", "mp3"),
        ("NoExt Or Weird", "NoExt Or Weird", None),
        ("D:/Folder\\anotherfolder\\yetanotheroflder/lastfolder/Barry B - De barry way.mp3.wav", "Barry B - De barry way", "wav"),
        ("Barry B - wav woev wov.wav", "Barry B - wav woev wov", "wav")
    ],
)
def test_strip_path_and_extension(parser, raw, basename, ext):
    
    audio_extensions = ParserConfig().audio_extensions

    b, e= strip_path_and_extension(raw, audio_extensions=audio_extensions)

    assert b == basename
    assert e == ext

# tests/conftest.py
from __future__ import annotations

import pytest

from songstring_parser.conf import ParserConfig
from songstring_parser.parser import SongStringParser


@pytest.fixture(scope="session")
def config() -> ParserConfig:
    """Default parser config for all tests."""
    return ParserConfig()


@pytest.fixture(scope="session")
def parser(config: ParserConfig) -> SongStringParser:
    """Parser instance for all tests."""
    return SongStringParser(config=config)

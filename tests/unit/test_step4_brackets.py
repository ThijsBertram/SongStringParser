import pytest
from songstring_parser.steps.step4_parse_brackets import parse_brackets




@pytest.mark.step4
@pytest.mark.unit
@pytest.mark.parametrize("raw,expected", 
                            [
                                # Simple remix + feat + noise
                                # ("For A Feeling (feat. RHODES) [Extended Mix] [official video]",
                                # ("For A Feeling", ["feat", "remix_version", "noise"])),

                                # # # Live variants
                                ("Says (Live at Funkhaus) [Visualizer]",
                                ("Says", ["live", "noise"])),

                                # # Remixer byline vs version-only
                                ("Opal (Bicep Rework)", ("Opal", ["remixer_byline"])),
                                ("Glue (Original Mix)", ("Glue", ["remix_version"])),

                                # # # Bootleg by name and live
                                ("Track Name (Bootleg by Barry) (Live in Ibiza 2016)",
                                ("Track Name", ["remixer_byline", "live"])),

                                # # Mixed bracket families
                                ("Title [DJ City Edit] {VINYL RIP} (key 8A 124bpm)",
                                ("Title", ["remixer_byline", "noise", "noise"])),

                                # # Multiple useful tokens
                                ("Title (feat. MØ & DJ Snake) [Radio Edit]",
                                ("Title", ["feat", "remix_version"])),

                                # # Unknown stays unknown
                                ("Title [¯\\_(ツ)_/¯]", 
                                ("Title", ["unknown"])),  # treated as noise by our pattern

                                ("Artist Barry ((featuring bobo.lici()us))",
                                ("Artist Barry", ["feat"])),

                                ("some text{Sunset Dub (128kbps)}",
                                ("some text", ['noise', 'remix_byline'])),

                                ("some title (remixed by some artist) [featuring bobby billy] (Rework)",
                                ("some title", ['remix_byline', 'feat', 'remix_version']))


                            ]
                        )
def test_step4_bracket_harvest(raw, expected):
    cleaned, segs = parse_brackets(raw)
    print(raw)
    print(cleaned)
    for seg in segs:
        print(seg)
    print()
    exp_cleaned, exp_classes = expected
    assert cleaned == exp_cleaned
    assert [s.cls for s in segs] == exp_classes
import re 
import unicodedata

from songstring_parser.conf import ParserConfig

DASHES_TO_HYPHEN = ParserConfig().dashes_to_hyphen


def normalize_separators_whitespace(s: str, dashes_to_hyphen=DASHES_TO_HYPHEN) -> str:
    """
    Step 2 normalizer: make separators/spacing predictable without
    harming artist tokens like 'M-zine' or 'CamelPhat&Elderbrook'.
    Idempotent and conservative.
    """
    if s is None:
        return s

    # 1) Unicode normalize to tame exotic glyphs
    s = unicodedata.normalize("NFKC", s)

    # 2) Convert various unicode dashes to ASCII '-' (do NOT add spaces here)
    s = s.translate({code: ord('-') for code in dashes_to_hyphen})

    # 3) Normalize all horizontal whitespace (tabs, etc.) to single spaces (collapse later)
    s = re.sub(r'[\t\r\f\v]+', ' ', s)

    # 4) Normalize/pad secondary splitters: ~ and |  (surround with single spaces)
    s = re.sub(r'\s*~\s*', ' ~ ', s)
    s = re.sub(r'\s*\|\s*', ' | ', s)

    # 5) Normalize spacing around brackets to "Title (X) [Y] {Z}"
    #    First ensure exactly one space before opening, then tighten inside/outside
    #    Add a space before an opening bracket if there is a non-space before it.
    s = re.sub(r'(?<=\S)\s*\(\s*', ' (', s)
    s = re.sub(r'(?<=\S)\s*\[\s*', ' [', s)
    s = re.sub(r'(?<=\S)\s*\{\s*', ' {', s)
    #    Remove extra space before closing brackets, but keep a single space after if followed by a word char
    s = re.sub(r'\s+\)', ')', s)
    s = re.sub(r'\s+\]', ']', s)
    s = re.sub(r'\s+\}', '}', s)

    # 6) Collapse runs of spaces (we'll do it again at the end too)
    s = re.sub(r' {2,}', ' ', s)

    # 7) Canonicalize hyphen *as a separator* only when at least one side was spaced.
    #    Cases handled:
    #      "A- B"  -> "A - B"
    #      "A -B"  -> "A - B"
    #      "A  -  B" or "A -- B" -> "A - B"
    #    NOT touched:
    #      "M-zine", "CamelPhat&Elderbrook" (no spaces around the hyphen/&)
    #    First, compress multiple hyphens between spaces to a single hyphen.
    s = re.sub(r'\s-+\s', ' - ', s)
    #    Ensure a space on both sides if there is already space on at least one side.
    s = re.sub(r'(?<=\s)-(?=\S)', ' - ', s)  # " -B" -> " - B"
    s = re.sub(r'(?<=\S)-(?=\s)', ' - ', s)  # "A- " -> "A - "
    #    Fix any accidental double spaces from the above
    s = re.sub(r' {2,}', ' ', s)

    # 8) Final tidy: remove stray spaces before punctuation and collapse spaces
    s = re.sub(r'\s+([)\]\}])', r'\1', s)  # no space before closing bracket
    s = re.sub(r'([(\[\{])\s+', r'\1', s)  # no space right after opening bracket
    s = re.sub(r' {2,}', ' ', s).strip()

    return s
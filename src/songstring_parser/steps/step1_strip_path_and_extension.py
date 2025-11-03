import re
from typing import Dict, Any, Tuple, Optional

def strip_path_and_extension(s: str, audio_extensions) -> Tuple[str, bool]:
    """
    Return (basename, is_path) for a song string that may include directory parts.

    Path decision (conservative with '/'; liberal with '\\'):
      - Always treat backslash '\\' as a path separator.
      - Treat forward slash '/' as a path separator ONLY if any strong signal is present:
          * Windows drive prefix at start (e.g., 'C:\\')
          * UNC path prefix at start (e.g., '\\\\server\\share' or '//server/share')
          * URL scheme at start (e.g., 'file://', 'http://', etc.)
          * 'CD<d>' or 'Disc <d>' folder token near a slash
          * Two or more total separators (any combination of '/' and '\\')
          * Presence of any backslash (already covered above)
      - Otherwise, a lone '/' (e.g., 'AC/DC') is treated as a literal character.

    Also trims trailing separators before computing the basename.
    """
    if not s:
        return s, False

    # --- Strong signals (compiled here for single-function self-containment) ---
    re_win_drive  = re.compile(r"(?i)^[a-z]:[\\/]")
    re_unc_path   = re.compile(r"^(?:[\\/]{2})[^\\/]+[\\/][^\\/]+")  # \\server\share or //server/share
    re_url_scheme = re.compile(r"(?i)^[a-z][a-z0-9+.\-]*://")
    re_cd_disc    = re.compile(r"(?i)(?:^|[\\/])(cd|disc)\s*\d+\b")

    has_backslash = ("\\" in s)
    slash_count   = s.count("/") + s.count("\\")
    looks_win_drive = bool(re_win_drive.search(s))
    looks_unc       = bool(re_unc_path.search(s))
    looks_url       = bool(re_url_scheme.search(s))
    has_cd_disc     = bool(re_cd_disc.search(s))
    multi_seps      = (slash_count >= 2)

    # Decide whether forward slashes should be treated as path separators
    allow_forward = any([
        has_backslash,
        looks_win_drive,
        looks_unc,
        looks_url,
        has_cd_disc,
        multi_seps,
    ])

    # If we consider it path-like, strip trailing separators to avoid empty basenames
    s_stripped = s.rstrip("/\\") if (allow_forward or has_backslash) else s

    last_backslash = s_stripped.rfind("\\")
    last_forward   = s_stripped.rfind("/") if (allow_forward or has_backslash) else -1

    cut = max(last_backslash, last_forward)
    basename = s_stripped[cut + 1 :] if cut >= 0 else s_stripped


    # # ======================
    # # REMOVE AUDIO EXTENSION
    # # ======================

    exts_core = sorted({ext.lstrip(".").lower() for ext in audio_extensions})
    exts_alt = "|".join(re.escape(x) for x in exts_core)  # e.g. "mp3|flac|wav|m4a"
    ext_re = re.compile(rf"\s*\.({exts_alt})\s*$", re.IGNORECASE)

    primary_ext: Optional[str] = None
    working = basename

    # 3) Loop: peel ALL trailing audio extensions
    while True:
        m = ext_re.search(working)
        if not m:
            break
        # Capture the first one we remove as the "result extension"
        if primary_ext is None:
            primary_ext = m.group(1).lower()
        # Remove this trailing extension and any whitespace before it
        working = working[: m.start()].rstrip()

    return working, primary_ext
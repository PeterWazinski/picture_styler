"""Shared OOM (out-of-memory) detection helpers for GPU/DirectML errors.

Both :mod:`src.core.engine` and :mod:`src.stylist.apply_worker` need to
distinguish OOM errors from other ONNX exceptions.  Keeping a single keyword
set and regex here ensures both paths stay in sync when new ONNX error wordings
appear.
"""
from __future__ import annotations

import re

_OOM_KEYWORDS: tuple[str, ...] = ("out of memory", "insufficient", "error code: 6", ": 6 :")
# Match "oom" as a whole word (case-insensitive) to avoid false positives from
# words like "boom" or "room" that happen to contain the substring "oom".
_OOM_WORD_RE: re.Pattern[str] = re.compile(r"\boom\b", re.IGNORECASE)


def is_oom_error(message: str) -> bool:
    """Return True if *message* signals a GPU/DirectML out-of-memory condition."""
    lower = message.lower()
    return bool(_OOM_WORD_RE.search(message)) or any(k in lower for k in _OOM_KEYWORDS)

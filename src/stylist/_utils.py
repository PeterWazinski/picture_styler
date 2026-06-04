"""Small utility helpers shared across the stylist package."""
from __future__ import annotations

import functools
import sys
from pathlib import Path


@functools.lru_cache(maxsize=1)
def _get_project_root() -> Path:
    """Return the project root for resolving relative model paths.

    When frozen (PyInstaller), the root is the directory that contains the
    executable (i.e. ``dist/PictureStyler/``).  In development the root
    is three levels above this file (``src/stylist/_utils.py`` → repo root).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def _get_bundled_data_root() -> Path:
    """Return the root for data files bundled via PyInstaller ``datas``.

    In PyInstaller 6.x onedir builds all ``datas`` land in ``_internal/``
    (i.e. ``sys._MEIPASS``).  In development this is the same as the project
    root so both paths work transparently.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent.parent

"""Shared pytest fixtures for all tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# --run-slow option: opt-in to _takes_long tests
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests whose names end in '_takes_long' (slow / high-memory).",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-slow"):
        return  # nothing to skip
    skip = pytest.mark.skip(reason="slow test — pass --run-slow to run")
    for item in items:
        if "takes_long" in item.name:
            item.add_marker(skip)


# ---------------------------------------------------------------------------
# Synthetic image fixtures (no disk I/O required)
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_64() -> Image.Image:
    """64×64 random RGB image for fast unit tests."""
    arr = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    return Image.fromarray(arr)


@pytest.fixture()
def sample_256() -> Image.Image:
    """256×256 random RGB image."""
    arr = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
    return Image.fromarray(arr)


@pytest.fixture()
def sample_2048() -> Image.Image:
    """2048×1536 random RGB image (simulates ~3 MP photo for fast tile tests)."""
    arr = np.random.randint(0, 255, (1536, 2048, 3), dtype=np.uint8)
    return Image.fromarray(arr)


# ---------------------------------------------------------------------------
# Fixture directory
# ---------------------------------------------------------------------------

@pytest.fixture()
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"

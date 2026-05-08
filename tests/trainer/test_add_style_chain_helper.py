"""Tests for training/add_style_chain_helper.py."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from training.add_style_chain_helper import install_chain, validate_chain_styles


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_styles_catalog(names: list[str]) -> dict:
    return {
        "styles": [
            {"id": n.lower().replace(" ", "_"), "name": n, "model_path": f"styles/{n}/model.onnx"}
            for n in names
        ]
    }


def _make_chains_catalog(chain_ids: list[str]) -> dict:
    return {
        "chains": [
            {"id": cid, "name": cid.capitalize(), "chain_path": f"style_chains/{cid}/chain.yml",
             "preview_path": "", "step_count": 1, "tags": []}
            for cid in chain_ids
        ]
    }


def _make_fake_image(tmp_path: Path, size: tuple[int, int] = (64, 64)) -> Path:
    p = tmp_path / "content.png"
    arr = np.zeros((*size, 3), dtype=np.uint8)
    Image.fromarray(arr).save(p)
    return p


# ---------------------------------------------------------------------------
# validate_chain_styles
# ---------------------------------------------------------------------------

class TestValidateChainStyles:
    def test_all_styles_present_returns_empty(self) -> None:
        catalog = _make_styles_catalog(["Ukiyo-e", "Cubism"])
        steps = [{"style": "Ukiyo-e", "strength": 150}, {"style": "Cubism", "strength": 80}]
        assert validate_chain_styles(steps, catalog) == []

    def test_missing_style_returned(self) -> None:
        catalog = _make_styles_catalog(["Ukiyo-e"])
        steps = [{"style": "Ukiyo-e", "strength": 150}, {"style": "Ghost", "strength": 80}]
        missing = validate_chain_styles(steps, catalog)
        assert missing == ["Ghost"]

    def test_all_missing(self) -> None:
        catalog = _make_styles_catalog([])
        steps = [{"style": "A", "strength": 100}, {"style": "B", "strength": 100}]
        missing = validate_chain_styles(steps, catalog)
        assert set(missing) == {"A", "B"}

    def test_empty_steps_returns_empty(self) -> None:
        catalog = _make_styles_catalog(["Ukiyo-e"])
        assert validate_chain_styles([], catalog) == []

    def test_empty_catalog_all_missing(self) -> None:
        steps = [{"style": "Any", "strength": 100}]
        assert validate_chain_styles(steps, {"styles": []}) == ["Any"]


# ---------------------------------------------------------------------------
# setup() — file-system-level
# ---------------------------------------------------------------------------

class TestSetup:
    def test_setup_returns_context(self, tmp_path: Path) -> None:
        from training.add_style_chain_helper import setup

        # Create minimal required files
        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        catalog = {"styles": []}
        (styles_dir / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        sample_dir = tmp_path / "sample_images"
        sample_dir.mkdir()
        (sample_dir / "arch.png").write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal header

        ctx = setup(repo_root=tmp_path)
        assert ctx.repo_root == tmp_path
        assert ctx.existing_chain_ids == set()
        assert ctx.styles_catalog == catalog

    def test_setup_loads_existing_chain_ids(self, tmp_path: Path) -> None:
        from training.add_style_chain_helper import setup

        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "catalog.json").write_text(json.dumps({"styles": []}), encoding="utf-8")
        sample_dir = tmp_path / "sample_images"
        sample_dir.mkdir()
        (sample_dir / "arch.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        chains_dir = tmp_path / "style_chains"
        chains_dir.mkdir()
        chain_catalog = _make_chains_catalog(["pastel", "dense"])
        (chains_dir / "catalog.json").write_text(json.dumps(chain_catalog), encoding="utf-8")

        ctx = setup(repo_root=tmp_path)
        assert ctx.existing_chain_ids == {"pastel", "dense"}

    def test_setup_raises_when_styles_catalog_missing(self, tmp_path: Path) -> None:
        from training.add_style_chain_helper import setup
        with pytest.raises(AssertionError, match="Styles catalog not found"):
            setup(repo_root=tmp_path)


# ---------------------------------------------------------------------------
# install_chain  (filesystem only — engine and registry are mocked out)
# ---------------------------------------------------------------------------

class TestInstallChain:
    """Tests for install_chain that verify file layout and catalog updates."""

    def _mock_engine(self, out_image: Image.Image) -> MagicMock:
        engine = MagicMock()
        engine.is_loaded.return_value = False
        engine.apply.return_value = out_image
        return engine

    def _mock_registry(self) -> MagicMock:
        style = MagicMock()
        style.id = "cubism"
        style.tensor_layout = "NCHW"
        style.model_path_resolved.return_value = Path("styles/cubism/model.onnx")
        registry = MagicMock()
        registry.find_by_name.return_value = style
        return registry

    def _run_install(
        self,
        tmp_path: Path,
        steps: list[dict] | None = None,
        chain_name: str = "My Chain",
    ) -> str:
        chains_dir = tmp_path / "style_chains"
        chains_dir.mkdir()
        catalog_path = chains_dir / "catalog.json"
        chains_catalog: dict = {"chains": []}
        content_image = _make_fake_image(tmp_path)

        if steps is None:
            steps = [{"style": "Cubism", "strength": 80}]

        fake_result = Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8))

        with (
            patch("src.core.engine.StyleTransferEngine",
                  return_value=self._mock_engine(fake_result)),
            patch("src.core.registry.StyleRegistry",
                  return_value=self._mock_registry()),
        ):
            return install_chain(
                steps=steps,
                chain_name=chain_name,
                chain_desc="A test chain",
                chain_tags=["test"],
                chains_dir=chains_dir,
                chains_catalog_path=catalog_path,
                chains_catalog=chains_catalog,
                existing_chain_ids=set(),
                content_image=content_image,
                repo_root=tmp_path,
            )

    def test_returns_chain_id(self, tmp_path: Path) -> None:
        assert self._run_install(tmp_path, chain_name="My Chain") == "my-chain"

    def test_chain_id_spaces_become_hyphens(self, tmp_path: Path) -> None:
        assert self._run_install(tmp_path, chain_name="Cool Art Style") == "cool-art-style"

    def test_chain_yml_written(self, tmp_path: Path) -> None:
        chain_id = self._run_install(tmp_path, chain_name="Pastel")
        yml = tmp_path / "style_chains" / chain_id / "chain.yml"
        assert yml.exists()
        assert yml.stat().st_size > 0

    def test_preview_jpg_written(self, tmp_path: Path) -> None:
        chain_id = self._run_install(tmp_path, chain_name="Pastel")
        preview = tmp_path / "style_chains" / chain_id / "preview.jpg"
        assert preview.exists()
        assert preview.stat().st_size > 0

    def test_catalog_json_updated(self, tmp_path: Path) -> None:
        self._run_install(tmp_path, chain_name="Pastel")
        catalog_path = tmp_path / "style_chains" / "catalog.json"
        assert catalog_path.exists()
        with catalog_path.open() as f:
            catalog = json.load(f)
        assert len(catalog["chains"]) == 1
        entry = catalog["chains"][0]
        assert entry["id"] == "pastel"
        assert entry["name"] == "Pastel"
        assert entry["description"] == "A test chain"
        assert entry["tags"] == ["test"]
        assert entry["step_count"] == 1

    def test_catalog_chain_path_fields(self, tmp_path: Path) -> None:
        self._run_install(tmp_path, chain_name="Dense")
        catalog_path = tmp_path / "style_chains" / "catalog.json"
        with catalog_path.open() as f:
            entry = json.load(f)["chains"][0]
        assert entry["chain_path"] == "style_chains/dense/chain.yml"
        assert entry["preview_path"] == "style_chains/dense/preview.jpg"

    def test_step_count_reflects_number_of_steps(self, tmp_path: Path) -> None:
        steps = [
            {"style": "Cubism", "strength": 80},
            {"style": "Cubism", "strength": 100},
            {"style": "Cubism", "strength": 60},
        ]
        self._run_install(tmp_path, steps=steps, chain_name="Three Step")
        catalog_path = tmp_path / "style_chains" / "catalog.json"
        with catalog_path.open() as f:
            entry = json.load(f)["chains"][0]
        assert entry["step_count"] == 3

    def test_duplicate_id_raises(self, tmp_path: Path) -> None:
        chains_dir = tmp_path / "style_chains"
        chains_dir.mkdir()
        catalog_path = chains_dir / "catalog.json"
        chains_catalog: dict = {"chains": []}
        content_image = _make_fake_image(tmp_path)
        fake_result = Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8))

        with (
            patch("src.core.engine.StyleTransferEngine",
                  return_value=self._mock_engine(fake_result)),
            patch("src.core.registry.StyleRegistry",
                  return_value=self._mock_registry()),
        ):
            with pytest.raises(AssertionError, match="already exists"):
                install_chain(
                    steps=[{"style": "Cubism", "strength": 80}],
                    chain_name="Pastel",
                    chain_desc="",
                    chain_tags=[],
                    chains_dir=chains_dir,
                    chains_catalog_path=catalog_path,
                    chains_catalog=chains_catalog,
                    existing_chain_ids={"pastel"},
                    content_image=content_image,
                    repo_root=tmp_path,
                )

    def test_empty_name_raises(self, tmp_path: Path) -> None:
        chains_dir = tmp_path / "style_chains"
        chains_dir.mkdir()
        catalog_path = chains_dir / "catalog.json"
        content_image = _make_fake_image(tmp_path)
        with pytest.raises(AssertionError, match="empty"):
            install_chain(
                steps=[{"style": "Cubism", "strength": 80}],
                chain_name="   ",
                chain_desc="",
                chain_tags=[],
                chains_dir=chains_dir,
                chains_catalog_path=catalog_path,
                chains_catalog={"chains": []},
                existing_chain_ids=set(),
                content_image=content_image,
                repo_root=tmp_path,
            )

    def test_empty_steps_raises(self, tmp_path: Path) -> None:
        chains_dir = tmp_path / "style_chains"
        chains_dir.mkdir()
        catalog_path = chains_dir / "catalog.json"
        content_image = _make_fake_image(tmp_path)
        with pytest.raises(AssertionError):
            install_chain(
                steps=[],
                chain_name="Empty",
                chain_desc="",
                chain_tags=[],
                chains_dir=chains_dir,
                chains_catalog_path=catalog_path,
                chains_catalog={"chains": []},
                existing_chain_ids=set(),
                content_image=content_image,
                repo_root=tmp_path,
            )

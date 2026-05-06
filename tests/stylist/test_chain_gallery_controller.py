"""Tests for ChainGalleryController — _apply_builtin_chain and _append_builtin_chain."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest
import yaml
from PIL import Image
from PySide6.QtWidgets import QMessageBox

from src.core.chain_models import BuiltinChainModel, ChainStore
from src.core.chain_registry import BuiltinChainRegistry
from src.core.engine import StyleTransferEngine
from src.core.models import StyleModel
from src.core.photo_manager import PhotoManager
from src.core.registry import StyleRegistry
from src.core.settings import AppSettings
from src.stylist.main_window import MainWindow
from tests.helpers import make_mock_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dummy_image(size: int = 64) -> Image.Image:
    return Image.fromarray(np.zeros((size, size, 3), dtype=np.uint8))


def _write_chain_yml(path: Path, steps: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump({"version": 1, "steps": steps}, f)


def _make_chain(chain_id: str, chain_path: str) -> BuiltinChainModel:
    return BuiltinChainModel(
        id=chain_id, name=chain_id.capitalize(),
        chain_path=chain_path,
        step_count=2,
    )


def _make_window(
    qtbot,
    tmp_path: Path,
    style_names: list[str],
    chain_steps: list[dict],
) -> tuple[MainWindow, MagicMock, BuiltinChainModel]:
    """Build a MainWindow with registered styles and one built-in chain."""
    # Write style catalog
    styles: list[StyleModel] = []
    for name in style_names:
        sid = name.lower().replace(" ", "-")
        preview = tmp_path / f"{sid}_preview.jpg"
        _dummy_image().save(preview)
        styles.append(StyleModel(
            id=sid, name=name,
            model_path=str(tmp_path / f"{sid}.onnx"),
            preview_path=str(preview),
        ))
    registry = StyleRegistry(catalog_path=tmp_path / "catalog.json")
    for s in styles:
        registry.add(s)

    # Write chain catalog + YAML
    rel_path = f"style_chains/test-chain/chain.yml"
    abs_yml = tmp_path / "style_chains" / "test-chain" / "chain.yml"
    _write_chain_yml(abs_yml, chain_steps)
    chain_catalog = tmp_path / "chain_catalog.json"
    chain_model = _make_chain("test-chain", rel_path)
    ChainStore(chain_catalog).save([chain_model])
    chain_registry = BuiltinChainRegistry(catalog_path=chain_catalog)

    # Build engine with mocked session
    engine = StyleTransferEngine()
    with (
        patch("src.core.engine._ORT_AVAILABLE", True),
        patch("src.core.engine.ort") as mock_ort,
        patch.object(Path, "exists", return_value=True),
    ):
        mock_ort.InferenceSession.return_value = make_mock_session()
        for s in styles:
            engine.load_model(s.id, Path("dummy/model.onnx"))

    window = MainWindow(
        registry=registry,
        engine=engine,
        photo_manager=PhotoManager(),
        settings=AppSettings(),
        chain_registry=chain_registry,
    )
    qtbot.addWidget(window)
    return window, engine, chain_model


# ---------------------------------------------------------------------------
# _apply_builtin_chain
# ---------------------------------------------------------------------------

class TestApplyBuiltinChain:
    def test_requires_photo_open(self, qtbot, tmp_path: Path) -> None:
        """Without an open photo, shows an info dialog and does nothing."""
        window, engine, chain = _make_window(
            qtbot, tmp_path,
            style_names=["Ukiyo-e"],
            chain_steps=[{"style": "Ukiyo-e", "strength": 100}],
        )
        assert window._current_photo is None
        with patch("src.stylist.chain_gallery_controller.QMessageBox.information") as mock_info:
            window._apply_builtin_chain(chain)
        mock_info.assert_called_once()

    def test_apply_chain_single_step_uses_apply_style(
        self, qtbot, tmp_path: Path
    ) -> None:
        """Single-step chain: first (and only) step calls _apply_style."""
        window, engine, chain = _make_window(
            qtbot, tmp_path,
            style_names=["Ukiyo-e"],
            chain_steps=[{"style": "Ukiyo-e", "strength": 150}],
        )
        window._current_photo = _dummy_image()
        result = _dummy_image()
        apply_calls: list[tuple] = []
        reapply_calls: list[tuple] = []

        original_apply = window._apply_style
        original_reapply = window._reapply_style

        def fake_apply(style_id: str, strength: float) -> None:
            apply_calls.append((style_id, strength))
            window._styled_photo = result  # simulate result
            window._style_log = [{"style": window._current_style_name, "strength": int(strength * 100)}]

        def fake_reapply(style_id: str, strength: float) -> None:
            reapply_calls.append((style_id, strength))

        with (
            patch.object(window, "_apply_style", side_effect=fake_apply),
            patch.object(window, "_reapply_style", side_effect=fake_reapply),
            patch("src.stylist.chain_gallery_controller._get_project_root", return_value=tmp_path),
        ):
            window._apply_builtin_chain(chain)

        assert len(apply_calls) == 1
        assert apply_calls[0] == ("ukiyo-e", 1.5)
        assert len(reapply_calls) == 0

    def test_apply_chain_two_steps_uses_apply_then_reapply(
        self, qtbot, tmp_path: Path
    ) -> None:
        """Two-step chain: first step → _apply_style, second → _reapply_style."""
        window, engine, chain = _make_window(
            qtbot, tmp_path,
            style_names=["Ukiyo-e", "Cubism"],
            chain_steps=[
                {"style": "Ukiyo-e", "strength": 150},
                {"style": "Cubism", "strength": 80},
            ],
        )
        window._current_photo = _dummy_image()
        result = _dummy_image()
        apply_calls: list[tuple] = []
        reapply_calls: list[tuple] = []

        def fake_apply(style_id: str, strength: float) -> None:
            apply_calls.append((style_id, strength))
            window._styled_photo = result
            window._style_log = [{"style": window._current_style_name, "strength": int(strength * 100)}]

        def fake_reapply(style_id: str, strength: float) -> None:
            reapply_calls.append((style_id, strength))
            window._style_log.append({"style": window._current_style_name, "strength": int(strength * 100)})

        with (
            patch.object(window, "_apply_style", side_effect=fake_apply),
            patch.object(window, "_reapply_style", side_effect=fake_reapply),
            patch("src.stylist.chain_gallery_controller._get_project_root", return_value=tmp_path),
        ):
            window._apply_builtin_chain(chain)

        assert len(apply_calls) == 1
        assert apply_calls[0][0] == "ukiyo-e"
        assert len(reapply_calls) == 1
        assert reapply_calls[0][0] == "cubism"

    def test_apply_chain_resets_log_regardless_of_prior_state(
        self, qtbot, tmp_path: Path
    ) -> None:
        """Even if _styled_photo is already set, first step uses _apply_style."""
        window, engine, chain = _make_window(
            qtbot, tmp_path,
            style_names=["Ukiyo-e"],
            chain_steps=[{"style": "Ukiyo-e", "strength": 100}],
        )
        window._current_photo = _dummy_image()
        window._styled_photo = _dummy_image()   # already styled
        window._style_log = [{"style": "Previous", "strength": 80}]
        apply_calls: list = []

        def fake_apply(style_id: str, strength: float) -> None:
            apply_calls.append(style_id)
            window._styled_photo = _dummy_image()
            window._style_log = [{"style": window._current_style_name, "strength": int(strength * 100)}]

        with (
            patch.object(window, "_apply_style", side_effect=fake_apply),
            patch("src.stylist.chain_gallery_controller._get_project_root", return_value=tmp_path),
        ):
            window._apply_builtin_chain(chain)

        assert len(apply_calls) == 1  # fresh: _apply_style called even though _styled_photo was set

    def test_unknown_style_shows_error(self, qtbot, tmp_path: Path) -> None:
        window, engine, chain = _make_window(
            qtbot, tmp_path,
            style_names=["Ukiyo-e"],
            chain_steps=[{"style": "Ghost Style", "strength": 100}],
        )
        window._current_photo = _dummy_image()
        with (
            patch("src.stylist.chain_gallery_controller.QMessageBox.critical") as mock_crit,
            patch("src.stylist.chain_gallery_controller._get_project_root", return_value=tmp_path),
        ):
            window._apply_builtin_chain(chain)
        mock_crit.assert_called_once()


# ---------------------------------------------------------------------------
# _append_builtin_chain
# ---------------------------------------------------------------------------

class TestAppendBuiltinChain:
    def test_append_uses_reapply_when_styled_photo_exists(
        self, qtbot, tmp_path: Path
    ) -> None:
        """With an existing styled photo, _append_builtin_chain calls _reapply_style."""
        window, engine, chain = _make_window(
            qtbot, tmp_path,
            style_names=["Ukiyo-e"],
            chain_steps=[{"style": "Ukiyo-e", "strength": 100}],
        )
        window._current_photo = _dummy_image()
        window._styled_photo = _dummy_image()
        window._style_log = [{"style": "Previous", "strength": 80}]
        reapply_calls: list = []

        def fake_reapply(style_id: str, strength: float) -> None:
            reapply_calls.append(style_id)

        with (
            patch.object(window, "_reapply_style", side_effect=fake_reapply),
            patch("src.stylist.chain_gallery_controller._get_project_root", return_value=tmp_path),
        ):
            window._append_builtin_chain(chain)

        assert len(reapply_calls) == 1
        assert reapply_calls[0] == "ukiyo-e"

    def test_append_uses_apply_when_no_styled_photo(
        self, qtbot, tmp_path: Path
    ) -> None:
        """Without a styled photo, _append_builtin_chain acts like apply."""
        window, engine, chain = _make_window(
            qtbot, tmp_path,
            style_names=["Ukiyo-e"],
            chain_steps=[{"style": "Ukiyo-e", "strength": 100}],
        )
        window._current_photo = _dummy_image()
        window._styled_photo = None
        apply_calls: list = []

        def fake_apply(style_id: str, strength: float) -> None:
            apply_calls.append(style_id)
            window._styled_photo = _dummy_image()
            window._style_log = [{"style": window._current_style_name, "strength": int(strength * 100)}]

        with (
            patch.object(window, "_apply_style", side_effect=fake_apply),
            patch("src.stylist.chain_gallery_controller._get_project_root", return_value=tmp_path),
        ):
            window._append_builtin_chain(chain)

        assert len(apply_calls) == 1


# ---------------------------------------------------------------------------
# Phase B — _delete_user_chain
# ---------------------------------------------------------------------------

def _make_window_with_user_chain(
    qtbot,
    tmp_path: Path,
) -> tuple[MainWindow, BuiltinChainModel]:
    """Window with one user chain and a user_catalog.json."""
    registry = StyleRegistry(catalog_path=tmp_path / "catalog.json")

    user_chain = BuiltinChainModel(
        id="my-chain",
        name="My Chain",
        chain_path="style_chains/user/my-chain/chain.yml",
        is_builtin=False,
    )
    chain_dir = tmp_path / "style_chains" / "user" / "my-chain"
    chain_dir.mkdir(parents=True)
    yml_path = chain_dir / "chain.yml"
    _write_chain_yml(yml_path, [{"style": "Ukiyo-e", "strength": 100}])

    sys_catalog = tmp_path / "chain_catalog.json"
    user_catalog = tmp_path / "user_catalog.json"
    ChainStore(sys_catalog).save([])
    ChainStore(user_catalog).save([user_chain])

    chain_registry = BuiltinChainRegistry(
        catalog_path=sys_catalog,
        user_catalog_path=user_catalog,
    )

    window = MainWindow(
        registry=registry,
        engine=StyleTransferEngine(),
        photo_manager=PhotoManager(),
        settings=AppSettings(),
        chain_registry=chain_registry,
    )
    qtbot.addWidget(window)
    return window, user_chain


class TestDeleteUserChain:
    def test_delete_confirmed_removes_directory(self, qtbot, tmp_path: Path) -> None:
        window, chain = _make_window_with_user_chain(qtbot, tmp_path)
        chain_dir = tmp_path / "style_chains" / "user" / "my-chain"
        assert chain_dir.exists()

        with (
            patch("src.stylist.chain_gallery_controller.QMessageBox.question",
                  return_value=QMessageBox.Yes),
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
        ):
            window._delete_user_chain(chain)

        assert not chain_dir.exists()

    def test_delete_confirmed_removes_from_registry(self, qtbot, tmp_path: Path) -> None:
        window, chain = _make_window_with_user_chain(qtbot, tmp_path)

        with (
            patch("src.stylist.chain_gallery_controller.QMessageBox.question",
                  return_value=QMessageBox.Yes),
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
        ):
            window._delete_user_chain(chain)

        assert not any(c.id == "my-chain" for c in window._chain_registry.list_chains())

    def test_delete_confirmed_updates_catalog_on_disk(
        self, qtbot, tmp_path: Path
    ) -> None:
        """user_catalog.json must not contain the chain after deletion."""
        from src.core.chain_models import ChainStore
        window, chain = _make_window_with_user_chain(qtbot, tmp_path)
        user_catalog = tmp_path / "user_catalog.json"

        with (
            patch("src.stylist.chain_gallery_controller.QMessageBox.question",
                  return_value=QMessageBox.Yes),
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
        ):
            window._delete_user_chain(chain)

        remaining = ChainStore(user_catalog).load()
        assert not any(c.id == "my-chain" for c in remaining)

    def test_delete_confirmed_removes_from_gallery_model(
        self, qtbot, tmp_path: Path
    ) -> None:
        """Gallery model must not contain the deleted chain after refresh."""
        from PySide6.QtCore import Qt as _Qt
        window, chain = _make_window_with_user_chain(qtbot, tmp_path)

        with (
            patch("src.stylist.chain_gallery_controller.QMessageBox.question",
                  return_value=QMessageBox.Yes),
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
        ):
            window._delete_user_chain(chain)

        model = window.chain_gallery.model()
        ids_in_model = [
            model.item(row).data(_Qt.UserRole).id
            for row in range(model.rowCount())
            if model.item(row).data(_Qt.UserRole) is not None
        ]
        assert "my-chain" not in ids_in_model

    def test_delete_rmtree_failure_still_updates_catalog_and_gallery(
        self, qtbot, tmp_path: Path
    ) -> None:
        """Even if the directory cannot be deleted (e.g. PermissionError on
        Windows), the catalog and gallery must still be updated."""
        from src.core.chain_models import ChainStore
        from PySide6.QtCore import Qt as _Qt
        window, chain = _make_window_with_user_chain(qtbot, tmp_path)
        user_catalog = tmp_path / "user_catalog.json"

        with (
            patch("src.stylist.chain_gallery_controller.QMessageBox.question",
                  return_value=QMessageBox.Yes),
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
            patch("src.stylist.chain_gallery_controller.shutil.rmtree",
                  side_effect=OSError("Permission denied")),
            patch("src.stylist.chain_gallery_controller.QMessageBox.warning"),
        ):
            window._delete_user_chain(chain)

        # Catalog on disk must be updated
        remaining = ChainStore(user_catalog).load()
        assert not any(c.id == "my-chain" for c in remaining)

        # In-memory registry must be updated
        assert not any(c.id == "my-chain" for c in window._chain_registry.list_chains())

        # Gallery model must not show the chain
        model = window.chain_gallery.model()
        ids_in_model = [
            model.item(row).data(_Qt.UserRole).id
            for row in range(model.rowCount())
            if model.item(row).data(_Qt.UserRole) is not None
        ]
        assert "my-chain" not in ids_in_model

    def test_delete_cancelled_does_nothing(self, qtbot, tmp_path: Path) -> None:
        window, chain = _make_window_with_user_chain(qtbot, tmp_path)
        chain_dir = tmp_path / "style_chains" / "user" / "my-chain"

        with (
            patch("src.stylist.chain_gallery_controller.QMessageBox.question",
                  return_value=QMessageBox.No),
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
        ):
            window._delete_user_chain(chain)

        assert chain_dir.exists()
        assert any(c.id == "my-chain" for c in window._chain_registry.list_chains())


# ---------------------------------------------------------------------------
# Phase C — _add_chain_from_yaml helpers
# ---------------------------------------------------------------------------

class TestMakeChainId:
    def test_simple(self) -> None:
        from src.stylist.chain_gallery_controller import _make_chain_id
        assert _make_chain_id("My Chain") == "my_chain"

    def test_special_chars_replaced(self) -> None:
        from src.stylist.chain_gallery_controller import _make_chain_id
        assert _make_chain_id("A + B") == "a_b"

    def test_empty_fallback(self) -> None:
        from src.stylist.chain_gallery_controller import _make_chain_id
        assert _make_chain_id("   ") == "chain"


class TestCenterCropToSquare:
    def test_square_unchanged(self) -> None:
        from PIL import Image
        from src.stylist.chain_gallery_controller import _center_crop_to_square
        img = Image.new("RGB", (100, 100))
        result = _center_crop_to_square(img)
        assert result.size == (100, 100)

    def test_landscape_cropped(self) -> None:
        from PIL import Image
        from src.stylist.chain_gallery_controller import _center_crop_to_square
        img = Image.new("RGB", (200, 100))
        result = _center_crop_to_square(img)
        assert result.size == (100, 100)

    def test_portrait_cropped(self) -> None:
        from PIL import Image
        from src.stylist.chain_gallery_controller import _center_crop_to_square
        img = Image.new("RGB", (80, 160))
        result = _center_crop_to_square(img)
        assert result.size == (80, 80)


class TestImportYamlChain:
    def _make_window_for_import(
        self, qtbot, tmp_path: Path
    ) -> tuple[MainWindow, BuiltinChainRegistry]:
        """Window with Ukiyo-e style + user catalog."""
        name = "Ukiyo-e"
        sid = "ukiyo-e"
        preview = tmp_path / f"{sid}_preview.jpg"
        _dummy_image().save(preview)
        style = StyleModel(
            id=sid, name=name,
            model_path=str(tmp_path / f"{sid}.onnx"),
            preview_path=str(preview),
        )
        registry = StyleRegistry(catalog_path=tmp_path / "catalog.json")
        registry.add(style)

        sys_catalog = tmp_path / "chain_catalog.json"
        user_catalog = tmp_path / "user_catalog.json"
        ChainStore(sys_catalog).save([])
        chain_registry = BuiltinChainRegistry(
            catalog_path=sys_catalog,
            user_catalog_path=user_catalog,
        )

        engine = StyleTransferEngine()
        with (
            patch("src.core.engine._ORT_AVAILABLE", True),
            patch("src.core.engine.ort") as mock_ort,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_ort.InferenceSession.return_value = make_mock_session()
            engine.load_model(sid, Path("dummy/model.onnx"))

        window = MainWindow(
            registry=registry,
            engine=engine,
            photo_manager=PhotoManager(),
            settings=AppSettings(),
            chain_registry=chain_registry,
        )
        qtbot.addWidget(window)
        return window, chain_registry

    def test_import_yaml_adds_chain_to_registry(
        self, qtbot, tmp_path: Path
    ) -> None:
        window, chain_registry = self._make_window_for_import(qtbot, tmp_path)

        # Write a valid YAML in tmp_path
        yml_path = tmp_path / "my_style.yml"
        _write_chain_yml(yml_path, [{"style": "Ukiyo-e", "strength": 100}])

        from src.stylist.widgets.name_chain_dialog import NameChainDialog

        class _FakeNameDialog:
            Accepted = NameChainDialog.Accepted

            def __init__(self, **kwargs):
                pass

            def exec(self):
                return self.Accepted

            def chain_name(self):
                return "My Style"

            def chain_description(self):
                return "My Style"

        with (
            patch("src.stylist.chain_gallery_controller.QFileDialog.getOpenFileName",
                  return_value=(str(yml_path), "")),
            patch("src.stylist.chain_gallery_controller.QMessageBox.question",
                  return_value=QMessageBox.No),  # No preview
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
        ):
            window._add_chain_from_yaml(_FakeNameDialog)

        assert any(c.id == "my_style" for c in chain_registry.list_chains())

    def test_import_yaml_unknown_style_shows_error(
        self, qtbot, tmp_path: Path
    ) -> None:
        window, _ = self._make_window_for_import(qtbot, tmp_path)

        yml_path = tmp_path / "bad.yml"
        _write_chain_yml(yml_path, [{"style": "Ghost", "strength": 100}])

        with (
            patch("src.stylist.chain_gallery_controller.QFileDialog.getOpenFileName",
                  return_value=(str(yml_path), "")),
            patch("src.stylist.chain_gallery_controller.QMessageBox.critical") as mock_crit,
            patch("src.stylist.chain_gallery_controller._get_project_root",
                  return_value=tmp_path),
        ):
            window._add_chain_from_yaml(object)  # NameChainDialog won't be reached

        mock_crit.assert_called_once()

    def test_import_yaml_no_file_selected_does_nothing(
        self, qtbot, tmp_path: Path
    ) -> None:
        window, chain_registry = self._make_window_for_import(qtbot, tmp_path)

        with patch("src.stylist.chain_gallery_controller.QFileDialog.getOpenFileName",
                   return_value=("", "")):
            window._add_chain_from_yaml(object)

        assert chain_registry.list_chains() == []


# ---------------------------------------------------------------------------
# Phase D — _add_chain_from_log
# ---------------------------------------------------------------------------

class TestAddChainFromLog:
    def _make_window_with_log(
        self, qtbot, tmp_path: Path
    ) -> tuple[MainWindow, BuiltinChainRegistry]:
        """Window with one registered style and a non-empty style log."""
        name = "Ukiyo-e"
        sid = "ukiyo-e"
        preview = tmp_path / f"{sid}_preview.jpg"
        _dummy_image().save(preview)
        style = StyleModel(
            id=sid, name=name,
            model_path=str(tmp_path / f"{sid}.onnx"),
            preview_path=str(preview),
        )
        registry = StyleRegistry(catalog_path=tmp_path / "catalog.json")
        registry.add(style)

        sys_catalog = tmp_path / "chain_catalog.json"
        user_catalog = tmp_path / "user_catalog.json"
        ChainStore(sys_catalog).save([])
        chain_registry = BuiltinChainRegistry(
            catalog_path=sys_catalog,
            user_catalog_path=user_catalog,
        )

        engine = StyleTransferEngine()
        with (
            patch("src.core.engine._ORT_AVAILABLE", True),
            patch("src.core.engine.ort") as mock_ort,
            patch.object(Path, "exists", return_value=True),
        ):
            mock_ort.InferenceSession.return_value = make_mock_session()
            engine.load_model(sid, Path("dummy/model.onnx"))

        window = MainWindow(
            registry=registry,
            engine=engine,
            photo_manager=PhotoManager(),
            settings=AppSettings(),
            chain_registry=chain_registry,
        )
        qtbot.addWidget(window)

        # Populate style_log
        window._style_log = [{"style": "Ukiyo-e", "strength": 100}]

        return window, chain_registry

    def _fake_name_dialog(self, name: str):
        from src.stylist.widgets.name_chain_dialog import NameChainDialog

        class _FakeNameDialog:
            Accepted = NameChainDialog.Accepted

            def __init__(self, **kwargs):
                pass

            def exec(self):
                return self.Accepted

            def chain_name(self):
                return name

            def chain_description(self):
                return name

        return _FakeNameDialog

    def test_add_chain_from_log_saves_chain(
        self, qtbot, tmp_path: Path
    ) -> None:
        window, chain_registry = self._make_window_with_log(qtbot, tmp_path)

        with patch("src.stylist.chain_gallery_controller._get_project_root",
                   return_value=tmp_path):
            window._add_chain_from_log(self._fake_name_dialog("Ukiyo-e Log"))

        assert any(c.id == "ukiyo_e_log" for c in chain_registry.list_chains())
        chain_dir = tmp_path / "style_chains" / "user" / "ukiyo_e_log"
        assert (chain_dir / "chain.yml").exists()
        assert (chain_dir / "preview.jpg").exists()

    def test_add_chain_from_log_cancelled_does_nothing(
        self, qtbot, tmp_path: Path
    ) -> None:
        window, chain_registry = self._make_window_with_log(qtbot, tmp_path)

        from src.stylist.widgets.name_chain_dialog import NameChainDialog

        class _CancelDialog:
            Accepted = NameChainDialog.Accepted

            def __init__(self, **kwargs):
                pass

            def exec(self):
                return NameChainDialog.Rejected

        with patch("src.stylist.chain_gallery_controller._get_project_root",
                   return_value=tmp_path):
            window._add_chain_from_log(_CancelDialog)

        assert chain_registry.list_chains() == []

    def test_add_chain_from_log_uses_styled_photo(
        self, qtbot, tmp_path: Path
    ) -> None:
        """When _styled_photo is set, preview.jpg should not be placeholder grey."""
        window, chain_registry = self._make_window_with_log(qtbot, tmp_path)
        window._styled_photo = _dummy_image(64)

        with patch("src.stylist.chain_gallery_controller._get_project_root",
                   return_value=tmp_path):
            window._add_chain_from_log(self._fake_name_dialog("MySnap"))

        chain_dir = tmp_path / "style_chains" / "user" / "mysnap"
        assert (chain_dir / "preview.jpg").exists()
        from PIL import Image as PILImage
        img = PILImage.open(chain_dir / "preview.jpg")
        assert img.width == img.height  # square after center-crop

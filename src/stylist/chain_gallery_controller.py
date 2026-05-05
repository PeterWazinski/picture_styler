"""ChainGalleryController mixin — built-in chain operations for MainWindow.

Provides ``_apply_builtin_chain``, ``_append_builtin_chain``,
``_delete_user_chain``, and ``_on_add_chain_requested``.
Mixed into :class:`src.stylist.main_window.MainWindow`.
"""
from __future__ import annotations

import io
import logging
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image as PILImage
from PySide6.QtWidgets import QFileDialog, QMessageBox

from src.core.chain_models import BuiltinChainModel
from src.core.style_chain_schema import load_style_chain, dump_style_chain, StyleChain, ChainStep
from src.stylist._utils import _get_project_root

if TYPE_CHECKING:
    from src.stylist.main_window import MainWindow

logger: logging.Logger = logging.getLogger(__name__)


def _make_chain_id(name: str) -> str:
    """Convert a display name to a unique-friendly slug, e.g. 'My Chain' → 'my_chain'."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_") or "chain"


def _center_crop_to_square(img: "PILImage.Image") -> "PILImage.Image":
    """Crop *img* to a centered square by trimming the longer axis."""
    w, h = img.size
    if w == h:
        return img
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def _save_preview(img: "PILImage.Image", dest: Path, size: int = 256) -> None:
    """Center-crop, resize to *size* × *size*, and save as JPEG."""
    square = _center_crop_to_square(img)
    thumb = square.resize((size, size), PILImage.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    thumb.save(str(dest), "JPEG", quality=85)


def _save_placeholder_preview(dest: Path, size: int = 256) -> None:
    """Save a solid grey placeholder JPEG at *dest*."""
    placeholder = PILImage.new("RGB", (size, size), color=(100, 100, 100))
    dest.parent.mkdir(parents=True, exist_ok=True)
    placeholder.save(str(dest), "JPEG", quality=85)


def _suggest_name_from_log(style_log: list[dict]) -> str:
    """Build 'A + B + C + …' from the style log (max 3 unique names)."""
    seen: list[str] = []
    for entry in style_log:
        name = str(entry.get("style", ""))
        if name and name not in seen:
            seen.append(name)
    truncated = seen[:3]
    result = " + ".join(truncated)
    if len(seen) > 3:
        result += " + \u2026"
    return result


class ChainGalleryController:
    """Mixin that adds built-in chain apply/append to MainWindow."""

    def _apply_builtin_chain(  # type: ignore[misc]
        self: "MainWindow",
        chain: BuiltinChainModel,
    ) -> None:
        """Apply *chain* fresh from the original photo (reset then run all steps)."""
        if self._current_photo is None:
            QMessageBox.information(self, "Apply Chain", "Open a photo first.")  # type: ignore[call-arg]
            return
        self._run_builtin_chain(chain, fresh=True)

    def _append_builtin_chain(  # type: ignore[misc]
        self: "MainWindow",
        chain: BuiltinChainModel,
    ) -> None:
        """Apply *chain* on top of the current photo state (append mode)."""
        if self._current_photo is None:
            QMessageBox.information(self, "Append Chain", "Open a photo first.")  # type: ignore[call-arg]
            return
        self._run_builtin_chain(chain, fresh=False)

    def _run_builtin_chain(  # type: ignore[misc]
        self: "MainWindow",
        chain: BuiltinChainModel,
        *,
        fresh: bool,
    ) -> None:
        """Common implementation shared by apply and append.

        Args:
            chain: The :class:`BuiltinChainModel` to run.
            fresh: When *True*, the first step always uses ``_apply_style``
                   (i.e. applies from the original photo, resetting the log).
                   When *False*, the first step uses ``_apply_style`` only if
                   ``_styled_photo`` is *None*, otherwise ``_reapply_style``.
        """
        root = _get_project_root()
        yml_path = chain.chain_path_resolved(root)
        try:
            sc = load_style_chain(yml_path)
        except ValueError as exc:
            QMessageBox.critical(self, "Apply Chain", str(exc))  # type: ignore[call-arg]
            return

        # Validate that all referenced styles are in the catalog.
        unknown: list[str] = [
            step.style
            for step in sc.steps
            if self._resolve_style_id_by_name(step.style) is None
        ]
        if unknown:
            names = "\n".join(f"  \u2022 {n}" for n in unknown)
            QMessageBox.critical(  # type: ignore[call-arg]
                self,
                "Apply Chain",
                "The following styles were not found in the catalog:\n"
                + names
                + "\n\nChain aborted.",
            )
            return

        dialog_title = "Apply Chain"
        for i, step in enumerate(sc.steps):
            style_id = self._resolve_style_id_by_name(step.style)
            assert style_id is not None
            self._current_style_name = step.style

            # Ensure ONNX model is loaded.
            if not self.engine.is_loaded(style_id):
                project_root = _get_project_root()
                style_obj = self.registry.get(style_id)
                try:
                    self.engine.load_model(
                        style_id,
                        style_obj.model_path_resolved(project_root),
                        tensor_layout=style_obj.tensor_layout,
                    )
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.critical(  # type: ignore[call-arg]
                        self,
                        dialog_title,
                        f"Could not load model for \u2018{step.style}\u2019: {exc}",
                    )
                    return

            # For fresh mode the first step always applies from the original.
            use_apply = (fresh and i == 0) or (not fresh and self._styled_photo is None)
            if use_apply:
                self._apply_style(style_id, step.strength / 100.0)
            else:
                self._reapply_style(style_id, step.strength / 100.0)

        self._status.showMessage(f"Chain applied: {chain.name}")

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def _delete_user_chain(  # type: ignore[misc]
        self: "MainWindow",
        chain: BuiltinChainModel,
    ) -> None:
        """Confirm then permanently delete *chain* and refresh the gallery."""
        reply = QMessageBox.question(  # type: ignore[call-arg]
            self,
            "Delete Chain",
            f"Delete \u2018{chain.name}\u2019?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,  # type: ignore[attr-defined]
            QMessageBox.No,  # type: ignore[attr-defined]
        )
        if reply != QMessageBox.Yes:  # type: ignore[attr-defined]
            return

        root = _get_project_root()
        chain_dir = (root / chain.chain_path).parent
        if chain_dir.exists():
            shutil.rmtree(chain_dir)

        try:
            self._chain_registry.remove_chain(chain.id)
        except (KeyError, ValueError) as exc:
            logger.warning("Could not remove chain '%s' from registry: %s", chain.id, exc)

        self.chain_gallery.refresh()
        self._status.showMessage(f"Chain deleted: {chain.name}")

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def _on_add_chain_requested(  # type: ignore[misc]
        self: "MainWindow",
    ) -> None:
        """Open AddChainDialog; route to import-YAML or save-from-log."""
        from src.stylist.widgets.add_chain_dialog import AddChainDialog
        from src.stylist.widgets.name_chain_dialog import NameChainDialog

        log_summary = ""
        log_empty = not bool(self._style_log)
        if not log_empty:
            log_summary = "  →  ".join(
                f"{e['style']} {e['strength']} %"
                for e in self._style_log
            )

        dlg = AddChainDialog(
            style_log_summary=log_summary,
            log_empty=log_empty,
            parent=self,
        )
        if dlg.exec() != AddChainDialog.Accepted:
            return

        if dlg.selected_source() == AddChainDialog.SOURCE_IMPORT_YAML:
            self._add_chain_from_yaml(NameChainDialog)
        else:
            self._add_chain_from_log(NameChainDialog)

    def _add_chain_from_yaml(  # type: ignore[misc]
        self: "MainWindow",
        NameChainDialog,  # type: ignore[misc]
    ) -> None:
        """Import-YAML path: file pick → validate → name dialog → preview → save."""
        start_dir = str(self._settings.last_save_dir or "")
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Import Style Chain", start_dir,  # type: ignore[call-arg]
            "YAML style chain (*.yml *.yaml)",
        )
        if not path_str:
            return

        yml_path = Path(path_str)
        try:
            sc = load_style_chain(yml_path)
        except ValueError as exc:
            QMessageBox.critical(self, "Import Chain", str(exc))  # type: ignore[call-arg]
            return

        unknown = [
            step.style for step in sc.steps
            if self._resolve_style_id_by_name(step.style) is None
        ]
        if unknown:
            names = "\n".join(f"  \u2022 {n}" for n in unknown)
            QMessageBox.critical(  # type: ignore[call-arg]
                self, "Import Chain",
                "The following styles were not found in the catalog:\n"
                + names + "\n\nChain aborted.",
            )
            return

        # Name dialog — prefill from YAML filename
        stem = yml_path.stem.replace("-", " ").replace("_", " ").title()
        name_dlg = NameChainDialog(suggested_name=stem, parent=self)
        if name_dlg.exec() != NameChainDialog.Accepted:
            return

        chain_name = name_dlg.chain_name()
        chain_desc = name_dlg.chain_description()
        chain_id = _make_chain_id(chain_name)

        root = _get_project_root()
        chain_dir = root / "style_chains" / "user" / chain_id
        chain_dir.mkdir(parents=True, exist_ok=True)
        dest_yml = chain_dir / "chain.yml"
        shutil.copy2(str(yml_path), str(dest_yml))

        preview_path = chain_dir / "preview.jpg"
        rel_preview = f"style_chains/user/{chain_id}/preview.jpg"

        # Preview popup — only for import YAML
        want_preview = QMessageBox.question(  # type: ignore[call-arg]
            self, "Generate Preview?",
            "Generate a preview thumbnail?\nThis may take several seconds.",
            QMessageBox.Yes | QMessageBox.No,  # type: ignore[attr-defined]
            QMessageBox.Yes,  # type: ignore[attr-defined]
        ) == QMessageBox.Yes  # type: ignore[attr-defined]

        if want_preview:
            sample = root / "sample_images" / "arch.png"
            if sample.exists():
                try:
                    img = PILImage.open(str(sample)).convert("RGB")
                    # Run the chain to generate a styled preview
                    for step in sc.steps:
                        style_id = self._resolve_style_id_by_name(step.style)
                        assert style_id is not None
                        if not self.engine.is_loaded(style_id):
                            style_obj = self.registry.get(style_id)
                            self.engine.load_model(
                                style_id,
                                style_obj.model_path_resolved(root),
                                tensor_layout=style_obj.tensor_layout,
                            )
                        img = self.engine.run(img, style_id, step.strength / 100.0)
                    _save_preview(img, preview_path)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Preview generation failed: %s", exc)
                    _save_placeholder_preview(preview_path)
            else:
                logger.warning("arch.png not found at %s — using placeholder", sample)
                _save_placeholder_preview(preview_path)
        else:
            _save_placeholder_preview(preview_path)

        chain_model = BuiltinChainModel(
            id=chain_id,
            name=chain_name,
            description=chain_desc,
            chain_path=f"style_chains/user/{chain_id}/chain.yml",
            preview_path=rel_preview,
            step_count=len(sc.steps),
            is_builtin=False,
        )
        try:
            self._chain_registry.add_user_chain(chain_model)
        except ValueError as exc:
            QMessageBox.warning(self, "Add Chain", str(exc))  # type: ignore[call-arg]
            return

        self.chain_gallery.refresh()
        self._status.showMessage(f"Chain added: {chain_name}")

    def _add_chain_from_log(  # type: ignore[misc]
        self: "MainWindow",
        NameChainDialog,  # type: ignore[misc]
    ) -> None:
        """Save the current style log as a new user chain."""
        suggested = _suggest_name_from_log(self._style_log)
        name_dlg = NameChainDialog(suggested_name=suggested, parent=self)  # type: ignore[call-arg]
        if name_dlg.exec() != NameChainDialog.Accepted:
            return

        chain_name: str = name_dlg.chain_name()
        chain_desc: str = name_dlg.chain_description()
        chain_id: str = _make_chain_id(chain_name)

        root = _get_project_root()
        chain_dir = root / "style_chains" / "user" / chain_id
        chain_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML from current style log
        (chain_dir / "chain.yml").write_text(
            self._format_style_chain(), encoding="utf-8"  # type: ignore[attr-defined]
        )

        # Preview from _styled_photo (no popup for save-from-log)
        preview_path = chain_dir / "preview.jpg"
        if self._styled_photo is not None:  # type: ignore[attr-defined]
            _save_preview(self._styled_photo, preview_path)  # type: ignore[attr-defined]
        else:
            _save_placeholder_preview(preview_path)

        chain_model = BuiltinChainModel(
            id=chain_id,
            name=chain_name,
            description=chain_desc,
            chain_path=f"style_chains/user/{chain_id}/chain.yml",
            preview_path=f"style_chains/user/{chain_id}/preview.jpg",
            step_count=len(self._style_log),  # type: ignore[attr-defined]
            is_builtin=False,
        )
        try:
            self._chain_registry.add_user_chain(chain_model)  # type: ignore[attr-defined]
        except ValueError as exc:
            QMessageBox.warning(self, "Add Chain", str(exc))  # type: ignore[call-arg]
            return

        self.chain_gallery.refresh()  # type: ignore[attr-defined]
        self._status.showMessage(f"Chain saved: {chain_name}")  # type: ignore[attr-defined]

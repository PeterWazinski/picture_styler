"""Tests for ChainGalleryView."""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from src.core.chain_models import BuiltinChainModel, ChainStore
from src.core.chain_registry import BuiltinChainRegistry
from src.stylist.chain_gallery import ChainGalleryView
from src.stylist.widgets.thumbnail_delegate import ADD_ITEM_ROLE, BUILTIN_ROLE, INVALID_ROLE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chain(chain_id: str = "pastel", name: str = "Pastel") -> BuiltinChainModel:
    return BuiltinChainModel(
        id=chain_id,
        name=name,
        chain_path=f"style_chains/{chain_id}/chain.yml",
        preview_path="",
        description="A test chain",
        step_count=2,
    )


def _make_registry(tmp_path: Path, chains: list[BuiltinChainModel]) -> BuiltinChainRegistry:
    catalog = tmp_path / "catalog.json"
    ChainStore(catalog).save(chains)
    return BuiltinChainRegistry(catalog_path=catalog)


# ---------------------------------------------------------------------------
# Population
# ---------------------------------------------------------------------------

class TestPopulation:
    def test_empty_registry_shows_no_items(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        # Only the sentinel "+" item should be present
        assert view.model().rowCount() == 1

    def test_items_populated_from_registry(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel"), _make_chain("dense", "Dense")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        # 2 chains + 1 sentinel
        assert view.model().rowCount() == 3

    def test_items_sorted_by_name(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("z", "Zebra"), _make_chain("a", "Alpha")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        # Exclude sentinel (last item)
        names = [view.model().item(i).text() for i in range(view.model().rowCount() - 1)]
        assert names == ["Alpha", "Zebra"]


# ---------------------------------------------------------------------------
# Invalid chain badge
# ---------------------------------------------------------------------------

class TestInvalidBadge:
    def test_invalid_chain_has_invalid_role_set(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel"), _make_chain("dense", "Dense")])
        view = ChainGalleryView(registry=reg, invalid_chain_ids={"pastel"})
        qtbot.addWidget(view)
        # Find the "Pastel" item
        model = view.model()
        items = {model.item(i).text(): model.item(i) for i in range(model.rowCount())}
        assert items["Pastel"].data(INVALID_ROLE) is True
        assert not items["Dense"].data(INVALID_ROLE)

    def test_valid_chain_has_no_invalid_role(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg, invalid_chain_ids=set())
        qtbot.addWidget(view)
        item = view.model().item(0)
        assert not item.data(INVALID_ROLE)

    def test_set_invalid_ids_refreshes_view(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg, invalid_chain_ids=set())
        qtbot.addWidget(view)
        assert not view.model().item(0).data(INVALID_ROLE)

        view.set_invalid_ids({"pastel"})
        assert view.model().item(0).data(INVALID_ROLE) is True


# ---------------------------------------------------------------------------
# Signals — click / double-click
# ---------------------------------------------------------------------------

class TestSignals:
    def test_click_emits_chain_selected(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        received: list = []
        view.chain_selected.connect(received.append)
        view._list_view.clicked.emit(view.model().index(0, 0))
        assert len(received) == 1
        assert received[0].id == "pastel"

    def test_double_click_emits_chain_apply_requested(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        received: list = []
        view.chain_apply_requested.connect(received.append)
        view._list_view.doubleClicked.emit(view.model().index(0, 0))
        assert len(received) == 1
        assert received[0].id == "pastel"


# ---------------------------------------------------------------------------
# Context menu
# ---------------------------------------------------------------------------

class TestContextMenu:
    def test_context_menu_apply_emits_chain_apply_requested(
        self, qtbot, tmp_path: Path
    ) -> None:
        import unittest.mock as mock

        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        received: list = []
        view.chain_apply_requested.connect(received.append)

        first_index = view.model().index(0, 0)
        pos = view._list_view.visualRect(first_index).center()
        with mock.patch("src.stylist.chain_gallery.QMenu") as MockMenu:
            instance = MockMenu.return_value
            apply_action = object()
            append_action = object()
            delete_action = object()
            instance.addAction.side_effect = [apply_action, append_action, delete_action]
            instance.exec.return_value = apply_action
            view._on_context_menu_requested(pos)

        assert len(received) == 1
        assert received[0].id == "pastel"

    def test_context_menu_append_emits_chain_append_requested(
        self, qtbot, tmp_path: Path
    ) -> None:
        import unittest.mock as mock

        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        received: list = []
        view.chain_append_requested.connect(received.append)

        first_index = view.model().index(0, 0)
        pos = view._list_view.visualRect(first_index).center()
        with mock.patch("src.stylist.chain_gallery.QMenu") as MockMenu:
            instance = MockMenu.return_value
            apply_action = object()
            append_action = object()
            delete_action = object()
            instance.addAction.side_effect = [apply_action, append_action, delete_action]
            instance.exec.return_value = append_action
            view._on_context_menu_requested(pos)

        assert len(received) == 1
        assert received[0].id == "pastel"


# ---------------------------------------------------------------------------
# Phase B — BUILTIN_ROLE, ADD_ITEM_ROLE, delete context menu
# ---------------------------------------------------------------------------

class TestBuiltinRole:
    def test_builtin_chain_has_builtin_role(self, qtbot, tmp_path: Path) -> None:
        chain = BuiltinChainModel(
            id="pastel", name="Pastel",
            chain_path="style_chains/pastel/chain.yml",
            is_builtin=True,
        )
        reg = _make_registry(tmp_path, [chain])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        item = view.model().item(0)
        assert item.data(BUILTIN_ROLE) is True

    def test_user_chain_has_no_builtin_role(self, qtbot, tmp_path: Path) -> None:
        chain = BuiltinChainModel(
            id="my-chain", name="My Chain",
            chain_path="style_chains/user/my-chain/chain.yml",
            is_builtin=False,
        )
        reg = _make_registry(tmp_path, [chain])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        item = view.model().item(0)
        assert not item.data(BUILTIN_ROLE)

    def test_builtin_chain_has_no_delete_in_context_menu(
        self, qtbot, tmp_path: Path
    ) -> None:
        import unittest.mock as mock

        chain = BuiltinChainModel(
            id="pastel", name="Pastel",
            chain_path="style_chains/pastel/chain.yml",
            is_builtin=True,
        )
        reg = _make_registry(tmp_path, [chain])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)

        first_index = view.model().index(0, 0)
        pos = view._list_view.visualRect(first_index).center()
        with mock.patch("src.stylist.chain_gallery.QMenu") as MockMenu:
            instance = MockMenu.return_value
            apply_action = object()
            append_action = object()
            instance.addAction.side_effect = [apply_action, append_action]
            instance.exec.return_value = None
            view._on_context_menu_requested(pos)
        # Only 2 addAction calls — no Delete
        assert instance.addAction.call_count == 2

    def test_user_chain_has_delete_in_context_menu(
        self, qtbot, tmp_path: Path
    ) -> None:
        import unittest.mock as mock

        reg = _make_registry(tmp_path, [_make_chain("pastel")])  # is_builtin=False
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)

        first_index = view.model().index(0, 0)
        pos = view._list_view.visualRect(first_index).center()
        with mock.patch("src.stylist.chain_gallery.QMenu") as MockMenu:
            instance = MockMenu.return_value
            apply_action = object()
            append_action = object()
            delete_action = object()
            instance.addAction.side_effect = [apply_action, append_action, delete_action]
            instance.exec.return_value = None
            view._on_context_menu_requested(pos)
        assert instance.addAction.call_count == 3

    def test_delete_action_emits_chain_delete_requested(
        self, qtbot, tmp_path: Path
    ) -> None:
        import unittest.mock as mock

        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        received: list = []
        view.chain_delete_requested.connect(received.append)

        first_index = view.model().index(0, 0)
        pos = view._list_view.visualRect(first_index).center()
        with mock.patch("src.stylist.chain_gallery.QMenu") as MockMenu:
            instance = MockMenu.return_value
            apply_action = object()
            append_action = object()
            delete_action = object()
            instance.addAction.side_effect = [apply_action, append_action, delete_action]
            instance.exec.return_value = delete_action
            view._on_context_menu_requested(pos)

        assert len(received) == 1
        assert received[0].id == "pastel"


class TestAddSentinel:
    def test_sentinel_item_always_appended(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        last_row = view.model().rowCount() - 1
        assert view.model().item(last_row).data(ADD_ITEM_ROLE) is True

    def test_empty_gallery_still_has_sentinel(self, qtbot, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        assert view.model().rowCount() == 1
        assert view.model().item(0).data(ADD_ITEM_ROLE) is True

    def test_click_on_sentinel_emits_add_chain_requested(
        self, qtbot, tmp_path: Path
    ) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        received: list = []
        view.add_chain_requested.connect(lambda: received.append(True))
        sentinel_index = view.model().index(view.model().rowCount() - 1, 0)
        view._list_view.clicked.emit(sentinel_index)
        assert len(received) == 1

    def test_sentinel_not_emitted_as_chain_selected(
        self, qtbot, tmp_path: Path
    ) -> None:
        reg = _make_registry(tmp_path, [_make_chain("pastel")])
        view = ChainGalleryView(registry=reg)
        qtbot.addWidget(view)
        selected: list = []
        view.chain_selected.connect(selected.append)
        sentinel_index = view.model().index(view.model().rowCount() - 1, 0)
        view._list_view.clicked.emit(sentinel_index)
        assert len(selected) == 0

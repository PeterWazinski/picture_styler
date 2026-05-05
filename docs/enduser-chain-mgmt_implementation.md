# End-User Style Chain Management — Implementation Plan

**Status**: Approved — ready for implementation  
**Date**: 2026-05-05

---

## 1. Scope

Add full end-user Create / Delete workflow for style chains directly inside the
app UI, without any notebook or developer tooling.

| Capability | Included |
|------------|----------|
| Delete a user-added chain (with confirmation) | ✅ |
| Lock icon on system chains (undeletable) | ✅ |
| "+" thumbnail → import a YAML file as a new chain | ✅ |
| "+" thumbnail → save current style log as a new chain | ✅ |
| Rename a chain (display name only) | ❌ out of scope (this iteration) |
| Edit chain steps in-app | ❌ out of scope |
| In-app restore of deleted chains | ❌ out of scope |

---

## 2. Analysis of the Current Architecture

| Component | Relevant state |
|-----------|---------------|
| `BuiltinChainModel` | Fields: `id, name, chain_path, preview_path, description, step_count, tags`. No `is_builtin` field yet (unlike `StyleModel` which already has one). |
| `ChainStore` | Reads and writes `style_chains/catalog.json`. No `add()` / `remove()` methods. |
| `BuiltinChainRegistry` | In-memory read-only registry. No mutation methods. |
| `ChainGalleryView` | `QListView` IconMode. Context menu: *Apply* / *Append* only. No "+" item, no Delete. |
| `ThumbnailDelegate` | Supports `INVALID_ROLE` (grey overlay + ⚠). Lock overlay not yet present. |
| `MainWindow._style_log` | `list[{"style": str, "strength": int}]`. Held in the `StyleChainController` mixin. |
| `_chain_copy_action` | `File → Style Chain to Clipboard` — serialises log to YAML in clipboard. |

All three system chains (`pastel`, `dense`, `hundertwasser`) live in
`style_chains/<id>/` with a shared catalog at `style_chains/catalog.json`.
The catalog and folders are writable at runtime (they sit next to the EXE in
the onedir build).

---

## 3. Design Decisions

### 3.1 Storage: Split Catalogs (Option B)

System catalog `style_chains/catalog.json` is read at startup and **never
written at runtime**.  User chains live in their own subdirectory and catalog:

| | Path |
|---|---|
| System catalog (read-only at runtime) | `style_chains/catalog.json` |
| User catalog (read/write at runtime) | `style_chains/user_catalog.json` |
| User chain folders | `style_chains/user/<id>/` |

This ensures app updates can refresh system chains without touching anything
the user created.

---

### 3.2 Lock Overlay on System Chains

A `BUILTIN_ROLE` custom data role is added to `ThumbnailDelegate` (parallel to
the existing `INVALID_ROLE`).  System chain items have it set to `True`.  The
delegate paints a small padlock icon in the **bottom-right corner** of the
thumbnail (16 × 16 px, 60 % opacity).

The right-click context menu shows **"Delete Chain…"** only for user chains.
For system chains only *Apply* / *Append* appear — the delete option is omitted
entirely (not greyed out).

---

### 3.3 Delete: Hard Delete

Clicking "Delete Chain…" shows:

> Delete '*{name}*'?  
> This cannot be undone.

On confirmation: `shutil.rmtree(style_chains/user/<id>/)` + remove entry from
`user_catalog.json` + gallery refresh.  No trash folder.

---

### 3.4 The "+" Thumbnail and Add Flow

A sentinel item is **always appended last** in the chain gallery.
`ThumbnailDelegate` detects a new `ADD_ITEM_ROLE` and renders a grey tile with
a bold **`+`** drawn via `QPainter` — no external asset needed.

**On click (single or double)** the sentinel emits `add_chain_requested()`.
`ChainGalleryController` handles this and opens `AddChainDialog`.

```
┌─ Add Style Chain ────────────────────────────────────────────────┐
│                                                                   │
│  ○ Import YAML file…                                             │
│                                                                   │
│  ● Save current style log as chain                               │
│      Ukiyo-e 150 % → Cubism 80 %   (summary, read-only)         │
│      (radio-disabled and greyed when style log is empty)         │
│                                               [Cancel]  [Next >] │
└───────────────────────────────────────────────────────────────────┘
```

The controller passes the current style log summary text and its emptiness
state to the dialog constructor so `ChainGalleryView` does not need access to
`_style_log`.

**Both paths** continue to `NameChainDialog` (see §3.5).

---

### 3.5 Name / Description Dialog (both paths)

After the source is selected, `NameChainDialog` is always shown:

```
┌─ Name Your Chain ────────────────────────────────────────────────┐
│  Name*:        [Ukiyo-e + Cubism              ]  ← auto-filled   │
│  Description:  [Ukiyo-e + Cubism              ]  ← auto-filled   │
│                                                                   │
│  * required — [Save Chain] disabled while empty                  │
│                                       [Cancel]  [Save Chain]     │
└───────────────────────────────────────────────────────────────────┘
```

**Auto-suggested name and description** (both fields pre-filled identically):
- *Save from log*: unique style names from the log joined by `" + "`, truncated
  after three (e.g. `"Ukiyo-e + Cubism + Candy + …"`).
- *Import YAML*: YAML file stem converted to title-case
  (e.g. `my_chain.yml` → `"My Chain"`).

Both fields are fully editable.  Description is not required but defaults to
the same value as the name so the user only has to clear it if they do not want
it.  [Save Chain] is disabled while Name is empty.

---

### 3.6 Preview Generation

| Source | Strategy |
|--------|----------|
| Save from style log | Use the already-rendered `_styled_photo` — center-crop to square (crop the longer axis), then resize to 256 × 256 px, save as `preview.jpg`. Near-zero cost. |
| Import YAML | Show popup: **"Generate preview? This may take several seconds."** [**Yes** (default/hero)] [No]. On Yes: run the chain on `sample_images/arch.png` at 256 px (same as the developer notebook), then center-crop to square and resize to 256 × 256 px, save as `preview.jpg`. On No: save a grey placeholder. |

The preview popup is shown **after** schema validation and style pre-flight
checks pass — no point asking if the chain is broken.

> **Distribution requirement**: `sample_images/arch.png` must be present in
> the onedir build next to the EXE. Add a `--add-data` entry to `compile.ps1`:
> ```
> --add-data "sample_images/arch.png;sample_images"
> ```

---

### 3.7 File → Style Chain to Clipboard

**Keep as-is.** The clipboard export remains useful for sharing chain YAML via
chat or email, which the new gallery-save flow does not cover.

---

### 3.8 Update / Rename

No action in this iteration. If a user needs to change chain steps they delete
and re-create.

---

## 4. Data Model Changes

### 4.1 `BuiltinChainModel` — add `is_builtin`

```python
@dataclass
class BuiltinChainModel:
    id: str
    name: str
    chain_path: str
    preview_path: str = ""
    description: str = ""
    step_count: int = 0
    tags: list[str] = field(default_factory=list)
    is_builtin: bool = False          # ← new; True for system chains
```

System chains in `style_chains/catalog.json` get `"is_builtin": true`.
User chains default to `False`.  `from_dict` already ignores unknown keys,
so no migration risk for existing catalog files that lack the field.

### 4.2 `ChainStore` — add `add()` and `remove()`

```python
def add(self, chain: BuiltinChainModel) -> None:
    """Append a chain entry to the catalog JSON (create file if absent)."""

def remove(self, chain_id: str) -> None:
    """Remove the entry with chain_id from the catalog JSON. No-op if absent."""
```

### 4.3 `BuiltinChainRegistry` — user catalog support

Add an optional `user_catalog_path: Path | None = None` parameter.  
`list_chains()` merges both catalogs (system first, then user), sorted by name.  
New mutation methods route to the user store only:

```python
def add_user_chain(self, chain: BuiltinChainModel) -> None: ...
def remove_chain(self, chain_id: str) -> None: ...  # user chains only
```

Attempting to call `remove_chain` with a system chain ID raises `ValueError`.

### 4.4 `app.py`

Pass `user_catalog_path` to the registry at startup:

```python
_USER_CHAIN_CATALOG_PATH = _project_root() / "style_chains" / "user_catalog.json"

chain_registry = BuiltinChainRegistry(
    catalog_path=_CHAIN_CATALOG_PATH,
    user_catalog_path=_USER_CHAIN_CATALOG_PATH,
)
```

---

## 5. UI Changes

### 5.1 `ThumbnailDelegate` — two new roles

```python
BUILTIN_ROLE: int = Qt.UserRole + 2   # bool — True → render lock overlay
ADD_ITEM_ROLE: int = Qt.UserRole + 3  # bool — True → render "+" tile
```

- **Lock overlay** (`BUILTIN_ROLE=True`): 16 × 16 px padlock drawn in
  bottom-right corner, 60 % opacity.
- **"+" tile** (`ADD_ITEM_ROLE=True`): skip the normal image; fill tile with
  `Qt.lightGray`; draw a bold `+` centred via `QPainter`; no text label.

### 5.2 `ChainGalleryView` — additions

New signals:
```python
add_chain_requested: Signal = Signal()
chain_delete_requested: Signal = Signal(object)   # payload: BuiltinChainModel
```

Changes to `refresh()`:
1. Set `BUILTIN_ROLE=True` on items whose `chain.is_builtin` is `True`.
2. After all real chain items, append the sentinel "+" item with
   `ADD_ITEM_ROLE=True` and `Qt.UserRole = None`.

Changes to `_on_context_menu_requested()`:
- For system chains: *Apply* / *Append* (unchanged).
- For user chains: *Apply* / *Append* / separator / **Delete Chain…**

Changes to `_on_item_clicked()` / `_on_item_double_clicked()`:
- If the clicked item has `ADD_ITEM_ROLE=True`, emit `add_chain_requested()`
  instead of `chain_selected`.

### 5.3 `ChainGalleryController` — new slots

```python
def _on_add_chain_requested(self: "MainWindow") -> None:
    """Open AddChainDialog; route to import or save-from-log."""

def _delete_user_chain(self: "MainWindow", chain: BuiltinChainModel) -> None:
    """Confirm, delete files, update registry, refresh gallery."""
```

**`_delete_user_chain` flow:**
1. `QMessageBox.question` — "Delete '*{name}*'?\nThis cannot be undone."
2. On `Yes`:
   - `shutil.rmtree(style_chains/user/<chain_id>/)`.
   - `self._chain_registry.remove_chain(chain.id)`.
   - `self.chain_gallery.refresh()`.

**`_on_add_chain_requested` flow:**
1. Open `AddChainDialog(style_log_summary=..., log_empty=...)`.
2. On dialog accepted with "Import YAML":
   a. `QFileDialog.getOpenFileName` for `.yml`/`.yaml`.
   b. Validate schema with `load_style_chain()`.
   c. Validate all referenced styles exist (same pre-flight as `_append_style_chain`).
   d. Open `NameChainDialog` prefilled: name = YAML stem in title-case, description = same.
   e. On confirmed: derive `chain_id` (`name.lower().replace(" ", "_")`),
      `mkdir style_chains/user/<id>/`, copy `.yml` as `chain.yml`.
   f. **Preview popup**: `QMessageBox.question` — "Generate preview? This may take several seconds."
      [**Yes** (default)] [No].  
      - Yes: run the chain on `sample_images/arch.png` at 256 px (same logic as the developer notebook); center-crop to square, resize to 256 × 256 px, save as `preview.jpg`.  
      - No: save a grey 256 × 256 placeholder as `preview.jpg`.
   g. `self._chain_registry.add_user_chain(chain_model)`.
   h. `self.chain_gallery.refresh()`.
3. On dialog accepted with "Save style log":
   a. Open `NameChainDialog` prefilled: name = unique styles joined by `" + "` (max 3), description = same.
   b. On confirmed: derive `chain_id`, `mkdir style_chains/user/<id>/`,
      write `self._format_style_chain()` as `chain.yml`.
   c. Center-crop `self._styled_photo` to square (crop the longer axis), resize to 256 × 256 px, save as `preview.jpg` (no popup — cost is near-zero).
   d. `self._chain_registry.add_user_chain(chain_model)`.
   e. `self.chain_gallery.refresh()`.

### 5.4 New widget files

| File | Contents |
|------|----------|
| `src/stylist/widgets/add_chain_dialog.py` | `AddChainDialog(QDialog)` — source selection |
| `src/stylist/widgets/name_chain_dialog.py` | `NameChainDialog(QDialog)` — name + description input |

Both are small (< 80 lines each).

---

## 6. `MainWindow` wiring

`_wire_signals()` additions:
```python
self.chain_gallery.add_chain_requested.connect(self._on_add_chain_requested)
self.chain_gallery.chain_delete_requested.connect(self._delete_user_chain)
```

`_build_menus()`: no change — `File → Style Chain to Clipboard` is kept as-is.

---

## 7. Phased Implementation

| Phase | Content | Commits |
|-------|---------|---------|
| **A** | Data model: `is_builtin` field, `ChainStore.add/remove`, `BuiltinChainRegistry` user catalog support, `app.py` wiring, seed `catalog.json` with `is_builtin: true` | 1 |
| **B** | Delete: `BUILTIN_ROLE` + lock overlay, context menu, `_delete_user_chain` slot, tests | 1 |
| **C** | Add (import YAML): sentinel "+" item, `AddChainDialog`, `NameChainDialog`, import + preview-popup flow, `compile.ps1` `--add-data` for `arch.png`, tests | 1 |
| **D** | Add (from style log): "save log" path in `_on_add_chain_requested`, preview from `_styled_photo`, tests | 1 |

Each phase is independently testable and commits in a clean state.

---

## 8. File Change Summary

| File | Change |
|------|--------|
| `src/core/chain_models.py` | Add `is_builtin: bool = False` to `BuiltinChainModel`; add `ChainStore.add()` and `remove()` |
| `src/core/chain_registry.py` | `user_catalog_path` param; `add_user_chain()`, `remove_chain()`; merged `list_chains()` |
| `src/stylist/chain_gallery.py` | Sentinel "+" item; `add_chain_requested` + `chain_delete_requested` signals; `BUILTIN_ROLE` handling in `refresh()`; updated context menu |
| `src/stylist/chain_gallery_controller.py` | `_delete_user_chain()`, `_on_add_chain_requested()` |
| `src/stylist/widgets/thumbnail_delegate.py` | `BUILTIN_ROLE` (lock icon) and `ADD_ITEM_ROLE` ("+" tile) |
| `src/stylist/widgets/add_chain_dialog.py` | **New**: `AddChainDialog` |
| `src/stylist/widgets/name_chain_dialog.py` | **New**: `NameChainDialog` |
| `src/stylist/main_window.py` | Wire new signals (no menu change) |
| `src/stylist/app.py` | Pass `user_catalog_path` to `BuiltinChainRegistry` |
| `compile.ps1` | Add `--add-data "sample_images/arch.png;sample_images"` so the file ships with the onedir build |
| `style_chains/catalog.json` | Add `"is_builtin": true` to all three existing chain entries |
| `tests/core/test_chain_models.py` | Tests for `ChainStore.add()` / `remove()` |
| `tests/core/test_chain_registry.py` | Tests for merged catalog, `add_user_chain()`, `remove_chain()` |
| `tests/stylist/test_chain_gallery.py` | Tests for "+" sentinel item, `BUILTIN_ROLE`, lock overlay, delete context menu |
| `tests/stylist/test_chain_gallery_controller.py` | Tests for delete, import YAML, save-from-log flows |

Estimated new test count: **~25 tests** across the four test files above.

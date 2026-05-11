## Project-Wide Refactoring Review

---

### 1. Behavior to Preserve

| Surface | Contract |
|---|---|
| `StyleTransferEngine.apply()` | Produces identical pixels for the same input, style, strength, tile_size, overlap |
| `BatchStyler` CLI | All flags (`--style-overview`, `--style-chain-overview`, `--apply-style-chain`, `--apply-random-style-chain`) and their exit codes |
| `PetersPictureStyler` GUI | Open / Apply / Re-Apply / Undo / Save; undo stack depth of 3; autosave `.yml` alongside saved image |
| Style chain YAML | Round-trip: GUI "copy to clipboard" YAML must be loadable by `--apply-style-chain` |
| OOM recovery | On OOM, all ONNX sessions unloaded; user can retry |
| Replay log | `autosave_style_log` setting writes `.yml` on save; `--apply-style-chain` can replay it |
| Tiling | Overlap/crop/merge invariants — output image same size as input |

---

### 2. Risks & Hotspots

**High risk: `ApplyController`/`StyleChainController` mixin pattern**
`MainWindow` inherits from `ApplyController`, `StyleChainController`, `ChainGalleryController`, and `QMainWindow` simultaneously. All four mixins access `self._styled_photo`, `self._settings`, `self.engine` etc. without any interface contract. Adding a field in one mixin silently shadows a field in another with no compiler warning. This is the highest-risk coupling in the codebase.

**High risk: `_reraise_if_oom` in `engine.py` and `is_oom_error` in `apply_worker.py`**
Two independent OOM-detection implementations exist — one in `engine.py` (keyword list in `_reraise_if_oom`) and one in `apply_worker.py` (regex + keyword list in `is_oom_error`). They use slightly different keyword sets. A new ONNX error wording must be added to both places to be caught everywhere.

**High risk: `_get_project_root()` in multiple callers**
`style_chain_controller.py` calls `_get_project_root()` inside a loop over chain steps (one call per step), and `main_window.py` calls it in `_on_style_selected()`. This is a filesystem operation called frequently in the hot path. A frozen-vs-dev guard is also duplicated across `src/stylist/_utils.py` and `src/batch_styler/catalog.py`.

**Medium risk: `_apply_chain_to_image` in `commands.py`**
Calls `engine.load_model` + `engine.unload_model` inside a step loop. If `load_model` raises mid-chain, no partial cleanup happens and the chain is silently half-applied. The `sys.exit()` calls inside this helper make it untestable without subprocess mocking.

**Medium risk: `StyleChainController._append_style_chain` model-loading logic**
Duplicates the model-loading code from `_on_style_selected` in `MainWindow`. Two places to update when `load_model` signature changes.

**Low risk: `JPEG_QUALITY = 92` vs `PhotoManager.save()` default of 95**
Silent quality discrepancy between GUI saves and CLI saves.

---

### 3. Minimal Safety Net

Tests already covering the critical paths:
- `tests/core/test_engine.py` — tiling, OOM detection, layout variants ✅
- `tests/stylist/test_apply_worker.py` — OOM routing, error routing ✅
- `tests/stylist/test_end_to_end.py` — apply/reapply/undo/save flow ✅
- `tests/batch_styler/test_batch_styler.py` — all CLI modes ✅

Gaps to close **before** refactoring:

1. **`StyleChainController._append_style_chain`** — no test covers the multi-step apply loop or the "unknown style" early-exit path in the GUI controller.
2. **`_get_project_root()` frozen vs. dev path** — no test exercises the `sys.frozen` branch; it can only be verified by running the compiled `.exe`.
3. **OOM keyword parity** — no test asserts that `is_oom_error()` and `_reraise_if_oom()` respond identically to the same message strings.

---

### 4. Step-by-Step Refactoring Plan

---

**Step 1 — Unify OOM keyword detection** *(Robustness, Maintainability)*
- **Change:** Extract a single `_OOM_KEYWORDS` tuple and `_OOM_WORD_RE` regex into `src/core/engine.py` or a new `src/core/_oom.py`. Import and reuse from both `engine._reraise_if_oom` and `apply_worker.is_oom_error`.
- **Why:** Two diverging keyword lists is the likeliest source of a future regression where one path catches an OOM the other silently misses.
- **Verification:** Existing `test_apply_worker.py` OOM tests pass; add a parametrized test asserting the same strings trigger both detectors.
- **Rollback:** Single-commit revert.

---

**Step 2 — Cache `_get_project_root()` result** *(Performance, DRY)*
- **Change:** Add `@functools.lru_cache(maxsize=1)` to `_get_project_root()` in `src/stylist/_utils.py`. Verify `src/batch_styler/catalog.py`'s `REPO_ROOT` uses the same implementation (or import from `_utils`).
- **Why:** Called in tight loops (per chain step, per style selection). Path resolution is pure and constant within a process lifetime.
- **Verification:** All existing tests pass. Confirm `catalog.REPO_ROOT` test patch still works.
- **Rollback:** Remove decorator.

---

**Step 3 — Extract `_load_style_model()` helper shared by `MainWindow` and `StyleChainController`** *(DRY, Maintainability)*
- **Change:** Extract the `if not engine.is_loaded → load_model` pattern (appears verbatim in `_on_style_selected` and in the loop in `_append_style_chain`) into a private `_ensure_model_loaded(style_id, style_obj)` method on `ApplyController`.
- **Why:** Identical 8-line try/except block in two places. A signature change to `load_model` requires two edits.
- **Verification:** Existing end-to-end and apply tests pass unchanged.
- **Rollback:** Inline the helper back.

---

**Step 4 — Replace `sys.exit()` in `_apply_chain_to_image` with raised exceptions** *(Testability)*
- **Change:** In `src/batch_styler/commands.py`, replace `sys.exit(f"Error: style '{step.style}'...")` inside `_apply_chain_to_image` with `raise ValueError(...)`. Catch at the `cmd_*` call sites and call `sys.exit()` there.
- **Why:** `sys.exit()` inside a pure helper makes unit testing impossible without subprocess overhead. All existing tests mock at the `cmd_*` level anyway.
- **Note:** **NOT a pure refactor** for callers that catch `SystemExit` — but none do; this is safe.
- **Verification:** `tests/batch_styler/test_batch_styler.py` passes; add one unit test for `_apply_chain_to_image` that asserts `ValueError` on unknown style.
- **Rollback:** Re-inline `sys.exit`.

---

**Step 5 — Remove ghost directories `src/ml/` and `src/ui/`** *(Understandability)*
- **Change:** `git rm -r src/ml/ src/ui/` (contain only `__pycache__`).
- **Why:** Ghost directories imply abandoned work and mislead contributors about where code should go.
- **Verification:** `grep -r "from src.ml\|from src.ui"` returns no hits; tests pass.
- **Rollback:** `git revert`.

---

**Step 6 — Align `JPEG_QUALITY` between CLI and `PhotoManager`** *(Correctness)*
- **Change:** Either change `PhotoManager.save()` default to `92`, or use `PhotoManager.save()` in `cmd_apply_style_chain` so both paths use the same value.
- **Note:** **NOT a pure refactor** if `PhotoManager.save()` default changes — it affects GUI saves too. Recommend: use `JPEG_QUALITY = 92` explicitly in `PhotoManager.save()` call in `commands.py`, and document both constants.
- **Verification:** Manual pixel-level check (or md5 of test output) before/after.
- **Rollback:** Revert constant.

---

**Step 7 — Replace multiple-inheritance mixin chain with explicit delegation** *(Architecture, long-term)*
- **Change:** Convert `ApplyController`, `StyleChainController`, `ChainGalleryController` from mixins to regular classes that receive a `MainWindow` reference in `__init__`. `MainWindow` holds them as `self._apply_ctrl`, etc., and calls their methods.
- **Why:** The current `class MainWindow(ApplyController, StyleChainController, ChainGalleryController, QMainWindow)` creates invisible shared-state coupling. Delegation makes the contract explicit and each controller testable in isolation without a `QMainWindow`.
- **Verification:** All GUI tests pass. Controllers become independently unit-testable.
- **Rollback:** Revert to mixin pattern (one commit per controller).

---

### 5. Target Design

```
src/core/
  _oom.py              ← single OOM keyword set, shared by engine + apply_worker
  engine.py            ← inference only; imports from _oom
  registry.py          ← find_by_name() as first-class method

src/stylist/
  main_window.py       ← construction, signal wiring, state only (~350 lines)
  _apply_ctrl.py       ← delegation class (not mixin); receives MainWindow ref
  _chain_ctrl.py       ← delegation class; receives MainWindow ref
  _gallery_ctrl.py     ← delegation class; receives MainWindow ref

src/batch_styler/
  commands.py          ← raises ValueError internally; sys.exit() at boundary only
```

**Dependency direction:** `stylist` → `core` → nothing. `batch_styler` → `core` → nothing. No cross-dependency between `stylist` and `batch_styler`. Training code in `training/` → `core` only.

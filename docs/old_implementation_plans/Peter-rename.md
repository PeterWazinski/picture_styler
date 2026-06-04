# Rename: PetersPictureStyler → PictureStyler

## Decisions (resolved)

| # | Decision | Answer |
|---|----------|--------|
| D1 | Display name (window title, credits, README headline) | **`Picture Styler`** (two words) |
| D2 | EXE / binary name | **`PictureStyler.exe`** / **`PictureStyler`** |
| D3 | Dist folder name | **`dist\PictureStyler\`** (Windows) / **`dist\PictureStyler-mac\`** (macOS) |
| D4 | YAML chain file header comment | **`# PictureStyler – style chain`** |
| D5 | Credits dialog | **Remove "Peter" entirely** |

---

## Complete file inventory

### Functional source — must change for the app to work correctly

| File | What changes | Impact if skipped |
|------|-------------|------------------|
| [picture_styler.spec](../picture_styler.spec) | `EXE(name="PetersPictureStyler")` → `"PictureStyler"` (line 126); `COLLECT(name="PetersPictureStyler")` (line 197); stub-cleanup loop (line 203) | Compiled EXE is still named `PetersPictureStyler.exe`; dist folder wrong |
| [picture_styler-mac.spec](../picture_styler-mac.spec) | `EXE(name="PetersPictureStyler_app")` → `"PictureStyler_app"` (line 136); `COLLECT(name="PetersPictureStyler-mac")` (line 207); stub loop (line 213) | macOS binary / dist folder wrong |
| [compile.ps1](../compile.ps1) | `$OutputDir`, `$OutputExe`, stub list, echo strings (10 occurrences) | Build script creates wrong folder / can't find output |
| [compile-mac.sh](../compile-mac.sh) | `OutputDir`, `OutputExe`, stub loop, rename step, rpath/sign loop, echo strings (15 occurrences) | macOS build creates wrong folder / can't find output |
| [src/stylist/main_window.py](../src/stylist/main_window.py) line 110 | `setWindowTitle("Peter's Picture Stylist")` → `"Picture Styler"` | Window title still shows old name |
| [src/stylist/app.py](../src/stylist/app.py) line 125 | `app.setApplicationName("Peter's Picture Stylist")` → `"Picture Styler"` | OS app-name (taskbar, About on macOS) wrong |
| [src/stylist/help_dialogs.py](../src/stylist/help_dialogs.py) | `"<b>Peter's Picture Stylist</b>"` → `"<b>Picture Styler</b>"` (remove all "Peter" occurrences) | Credits dialog shows old name / "Peter" |
| [src/stylist/_utils.py](../src/stylist/_utils.py) line 14 | Comment `dist/PetersPictureStyler/` | Comment only, no runtime effect — still worth updating |
| [src/stylist/app.py](../src/stylist/app.py) line 48 | Docstring `PetersPictureStyler\\app.log` | Comment only |
| [src/batch_styler/catalog.py](../src/batch_styler/catalog.py) line 19 | Comment `dist\PetersPictureStyler\` | Comment only |
| [src/core/style_chain_schema.py](../src/core/style_chain_schema.py) lines 9, 97 | `created_by = "PetersPictureStyler"` default value and header string | All future `.yml` files get old app name in header |
| [scripts/create_sample_overview.bat](../scripts/create_sample_overview.bat) line 6 | `dist\PetersPictureStyler\BatchStyler.exe` path | Script cannot find BatchStyler after rename |
| [scripts/create_sample_overview.sh](../scripts/create_sample_overview.sh) line 6 | `dist/PetersPictureStyler/BatchStyler` path | Script cannot find BatchStyler after rename |
| [scripts/sample_pic_slide_gen.bat](../scripts/sample_pic_slide_gen.bat) line 9 | `dist\PetersPictureStyler\BatchStyler.exe` path | Script cannot find BatchStyler after rename |
| [training/add_style_helper.py](../training/add_style_helper.py) line 232 | `"dist" / "PetersPictureStyler" / "style_chains"` | Training helper copies chains to wrong dist path |

### Documentation — no runtime effect, but should be consistent

| File | Occurrences |
|------|-------------|
| [README.md](../README.md) | Headline (line 3, 5), 8× `PetersPictureStyler` in path/command examples |
| [training/index.md](../training/index.md) | 1× |
| [scripts/index.md](../scripts/index.md) | 1× |
| [docs/20mp.md](20mp.md) | 3× (just written — update alongside) |
| [docs/old_implementation_plans/\*.md](old_implementation_plans/) | 5× across 4 files — **historical docs, leave or update as desired** |

### Data files — header comment only, no runtime effect

| File | Note |
|------|------|
| `style_chains/**/*.yml` (8 files) | First line: `# PetersPictureStyler – style chain` |
| `sample_images/style-chains/*.yml` (4+ files) | Same header comment |
| `training/add_style_helper.ipynb` | Cached output cell + source line 179 |
| `training/export_cyclegan_to_onnx.ipynb` | 1× in markdown cell |

---

## Execution steps (ordered)

### Step 1 — Spec files (PyInstaller produces the EXE names)

**[picture_styler.spec](../picture_styler.spec)**
- Line 126: `name="PetersPictureStyler"` → `name="PictureStyler"`
- Line 197: `name="PetersPictureStyler"` → `name="PictureStyler"`
- Line 203: `"PetersPictureStyler.exe"` → `"PictureStyler.exe"`
- Lines 2–5: update header comments

**[picture_styler-mac.spec](../picture_styler-mac.spec)**
- Line 136: `name="PetersPictureStyler_app"` → `name="PictureStyler_app"`
- Line 207: `name="PetersPictureStyler-mac"` → `name="PictureStyler-mac"`
- Line 213: `"PetersPictureStyler.exe"` → `"PictureStyler.exe"`
- Lines 78, 90–92: `PetersPictureStyler_app` / `PetersPictureStyler` → `PictureStyler_app` / `PictureStyler`

### Step 2 — Build scripts

**[compile.ps1](../compile.ps1)** — replace all 10 occurrences of `PetersPictureStyler`  
**[compile-mac.sh](../compile-mac.sh)** — replace all 15 occurrences of `PetersPictureStyler`

### Step 3 — App source (user-visible strings)

| File | Old | New |
|------|-----|-----|
| [src/stylist/main_window.py](../src/stylist/main_window.py) | `"Peter's Picture Stylist"` | `"Picture Styler"` |
| [src/stylist/app.py](../src/stylist/app.py) | `"Peter's Picture Stylist"` | `"Picture Styler"` |
| [src/stylist/help_dialogs.py](../src/stylist/help_dialogs.py) | `"<b>Peter's Picture Stylist</b>"` + any other "Peter" text | `"<b>Picture Styler</b>"` (remove all "Peter" occurrences) |

### Step 4 — style_chain_schema.py (affects all future .yml headers)

[src/core/style_chain_schema.py](../src/core/style_chain_schema.py)
- Line 9: `# PetersPictureStyler – style chain` → `# PictureStyler – style chain`
- Line 97: `created_by: str = "PetersPictureStyler"` → `created_by: str = "PictureStyler"`

### Step 5 — Scripts (functional: paths to BatchStyler)

- [scripts/create_sample_overview.bat](../scripts/create_sample_overview.bat)
- [scripts/create_sample_overview.sh](../scripts/create_sample_overview.sh)
- [scripts/sample_pic_slide_gen.bat](../scripts/sample_pic_slide_gen.bat)
- [training/add_style_helper.py](../training/add_style_helper.py)

### Step 6 — README and active docs

- [README.md](../README.md): headline + all path examples (10 occurrences)
- [training/index.md](../training/index.md), [scripts/index.md](../scripts/index.md)
- [docs/20mp.md](20mp.md): 3 occurrences

### Step 7 — Data file comments (low priority)

- All `style_chains/**/*.yml` header lines
- `sample_images/style-chains/*.yml` header lines

### Step 8 — Verify and commit

```
pytest                    # must stay 458 passed, 9 skipped
.\compile.ps1             # must produce dist\PictureStyler\PictureStyler.exe
git add -A
git commit -m "feat: rename PetersPictureStyler -> PictureStyler"
```

---

## What you explicitly asked about — checklist

| Item | Covered in step |
|------|-----------------|
| `compile.ps1` exe name | Step 2 |
| `compile-mac.sh` binary name | Steps 1 + 2 |
| Window title in app | Step 3 |
| Help → Credits: remove "Peter" entirely | Step 3 ✓ |
| README | Step 6 |

## Additional items found (not in your original list)

| Item | Why it matters |
|------|----------------|
| `picture_styler.spec` / `picture_styler-mac.spec` — EXE `name=` | Controls actual compiled binary name; **must change** |
| `src/core/style_chain_schema.py` `created_by` default | All `.yml` chain files written by the app get old app name in header |
| `scripts/*.bat` / `create_sample_overview.sh` | Hard-coded paths to `dist\PetersPictureStyler\` — scripts break after build rename |
| `training/add_style_helper.py` | Copies chains to `dist/PetersPictureStyler/` — wrong after rename |
| `src/stylist/app.py` `setApplicationName` | Sets OS-level app name (macOS dock, About panel) |

## Out of scope (no action needed)

| Item | Reason |
|------|--------|
| `docs/old_implementation_plans/*.md` | Historical docs, rename is cosmetic only |
| `training/*.ipynb` notebook output cells | Cached output, not active code |
| Tests | No test references the string "PetersPictureStyler" |
| Python package name / `pyproject.toml` | Package is `style_transfer`; unrelated to display name |

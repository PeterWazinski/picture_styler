# BatchStyler CLI — Extension Implementation Plan

**Status: DRAFT — awaiting review**

---

## Overview of Changes

| # | Requirement | Scope |
|---|-------------|-------|
| 1 | Rename `--outdir` → `--output-dir` | `app.py`, `commands.py` signatures, tests |
| 2 | Add `--input-dir INPUT-DIR` | `app.py`, `commands.py`, tests |
| 3 | Add `--apply-random-style-chain CHAIN-DIR` | `app.py`, `commands.py`, tests |
| 4 | Rewrite `-h` help text | `app.py` |

---

## Requirement 1 — Rename `--outdir` to `--output-dir`

### What changes

**`src/batch_styler/app.py`**
- `parser.add_argument("--outdir", ...)` → `parser.add_argument("--output-dir", ...)`
- `dest` becomes `output_dir` (argparse converts `-` to `_` automatically, so `args.output_dir`)
- All references to `args.outdir` → `args.output_dir`
- Update `_USAGE` string

**`src/batch_styler/commands.py`**
- No changes needed — `out_dir` is already the parameter name in every `cmd_*` function.
  The rename only affects the CLI argument in `app.py`.

**`tests/scripts/test_batch_styler.py`**
- Tests call `cmd_apply_style_chain(..., out_dir=...)` directly — no change needed there.
- Tests that exercise the CLI via `argparse` (currently none; integration tests call commands directly) — no change needed.
- Rename docstring/comment references to `--outdir` in:
  - `test_chain_outdir_writes_to_custom_dir` (line 545, docstring only)
  - `test_chain_outdir_with_strength_suffix` (line 589, docstring only)
  - `test_chain_overview_outdir` (line 965, docstring only)

### Backward compatibility note
`--outdir` was not documented externally as a stable API. No deprecation alias needed unless
users have scripts — confirm with product owner before merging.

---

## Requirement 2 — Add `--input-dir INPUT-DIR`

### Behaviour
- When `--input-dir DIR` is given the positional `<image>` argument is **optional** (omitted).
- **`<image>` and `--input-dir` are mutually exclusive.** Providing both is an error:
  `sys.exit("Error: <image> and --input-dir are mutually exclusive — provide one or the other.")`.
- The program collects all `*.jpg`, `*.jpeg`, and `*.png` files in `INPUT-DIR` (non-recursive,
  case-insensitive on Windows via `glob`).
- If no images are found → `sys.exit("Error: no JPEG/PNG images found in <DIR>")`.
- Each collected image is passed individually to the selected command in sorted order.
- `--input-dir` is **only valid** for commands that produce per-image output (i.e.
  `--apply-style-chain` and `--apply-random-style-chain`). It is **not** valid for
  `--style-overview` or `--style-chain-overview`, which already produce a single PDF.
  Attempting to combine them → `sys.exit("Error: --input-dir cannot be used with --style-overview or --style-chain-overview.")`.

### What changes

**`src/batch_styler/app.py`**

1. Make `image` positional optional: `parser.add_argument("image", nargs="?", ...)`.
2. Add new argument:
   ```python
   parser.add_argument(
       "--input-dir", type=Path, default=None, metavar="DIR", dest="input_dir",
       help="Process all JPEG/PNG images in DIR instead of a single <image>.",
   )
   ```
3. Add validation logic after `parse_args()`:
   ```python
   # Exactly one of image / --input-dir must be given
   if args.image is None and args.input_dir is None:
       sys.exit("Error: provide either <image> or --input-dir.")
   if args.image is not None and args.input_dir is not None:
       sys.exit("Error: <image> and --input-dir are mutually exclusive.")
   if args.input_dir is not None and (args.style_overview or args.style_chain_overview):
       sys.exit("Error: --input-dir cannot be used with --style-overview or --style-chain-overview.")
   ```
4. Build `image_paths: list[Path]`:
   ```python
   if args.input_dir is not None:
       input_dir = args.input_dir.resolve()
       if not input_dir.is_dir():
           sys.exit(f"Error: --input-dir directory does not exist: {input_dir}")
       exts = {".jpg", ".jpeg", ".png"}
       image_paths = sorted(p for p in input_dir.iterdir()
                            if p.suffix.lower() in exts)
       if not image_paths:
           sys.exit(f"Error: no JPEG/PNG images found in {input_dir}")
   else:
       image_paths = [args.image.resolve()]
       for p in image_paths:
           if not p.exists():
               sys.exit(f"Error: image not found: {p}")
   ```
5. For `--apply-style-chain` and `--apply-random-style-chain` (req. 3), wrap the
   existing single-image call in a `for image_path in image_paths:` loop.

**`src/batch_styler/commands.py`**
- No changes — `cmd_apply_style_chain` already accepts a single `image_path`.  
  The loop lives in `app.py`.

**`tests/scripts/test_batch_styler.py`** — new test class `TestInputDir`:

| Test | What it verifies |
|------|-----------------|
| `test_input_dir_applies_to_all_images` | With 3 images in dir, `engine.apply` called 3× per step |
| `test_input_dir_no_images_exits` | Empty dir → `SystemExit` |
| `test_input_dir_with_output_dir` | Results land in `--output-dir`, not source dirs |
| `test_input_dir_rejected_with_style_overview` | `SystemExit` when combined with `--style-overview` |
| `test_image_and_input_dir_mutually_exclusive` | Providing both → `SystemExit` |
| `test_neither_image_nor_input_dir_exits` | Providing neither → `SystemExit` |

---

## Requirement 3 — Add `--apply-random-style-chain CHAIN-DIR`

### Behaviour
- Randomly picks **one** `.yml`/`.yaml` file from `CHAIN-DIR` per image.
- When `--input-dir` is combined: each image gets an **independently** random chain
  (not the same chain for all images).
- Uses `random.choice(chain_files)` — reproducible via seeding if needed in future.
- Same output filename convention as `--apply-style-chain`:
  `<image-stem>_<chain-stem>.jpg` (or `<chain-stem>_<strength_scale>.jpg`).
- If `CHAIN-DIR` contains no `.yml`/`.yaml` files → `sys.exit(...)`.

### What changes

**`src/batch_styler/app.py`**

1. Add to the mode group:
   ```python
   mode_group.add_argument(
       "--apply-random-style-chain", type=Path, metavar="CHAIN_DIR",
       dest="apply_random_style_chain",
       help="Pick a random style-chain YAML from CHAIN_DIR and apply it to the image.",
   )
   ```
2. Add import: `import random`
3. Add dispatch block:
   ```python
   if args.apply_random_style_chain:
       chain_dir = args.apply_random_style_chain.resolve()
       if not chain_dir.is_dir():
           sys.exit(f"Error: chain directory does not exist: {chain_dir}")
       chain_files = sorted(chain_dir.glob("*.yml")) + sorted(chain_dir.glob("*.yaml"))
       chain_files = sorted(set(chain_files))
       if not chain_files:
           sys.exit(f"Error: no .yml/.yaml files found in {chain_dir}")
       for image_path in image_paths:
           chosen = random.choice(chain_files)
           cmd_apply_style_chain(
               image_path, chosen,
               tile_size=args.tile_size,
               overlap=args.overlap,
               use_float16=args.float16,
               strength_scale=args.strength_scale,
               out_dir=out_dir,
           )
       return
   ```
   Note: reuses `cmd_apply_style_chain` — no new command function needed.

**`src/batch_styler/commands.py`**
- No changes.

**`tests/scripts/test_batch_styler.py`** — new test class `TestApplyRandomStyleChain`:

| Test | What it verifies |
|------|-----------------|
| `test_random_chain_applies_a_chain` | `engine.apply` called ≥1 time; output file created |
| `test_random_chain_picks_from_dir` | Chosen chain path is one of the files in the dir |
| `test_random_chain_empty_dir_exits` | No `.yml` files → `SystemExit` |
| `test_random_chain_with_input_dir_processes_all` | 3 images × random chain → 3 output files |
| `test_random_chain_different_per_image` | With many images + mocked `random.choice`, each gets an independent draw |

---

## Requirement 4 — Rewrite `-h` help text

### Target output

```
BatchStyler.exe  —  batch style-transfer tool

COMMANDS THAT CREATE CONTACT SHEETS (PDF overview)
  --style-overview <image>
        Apply all available styles to <image> at 100/150/200% strength and
        write a DIN-A4 landscape PDF contact sheet.
        Output: <image-dir>/<stem>_style_overview.pdf

  --style-chain-overview <chain-dir> <image>
        Apply every .yml chain in <chain-dir> to <image> and write a
        portrait A4 PDF with one result per chain.
        Output: <image-dir>/<stem>_<chain-dir-name>_overview.pdf

COMMANDS THAT CREATE ONE OR MORE JPEG OUTPUT IMAGES
  --apply-style-chain <chain.yml>
        Apply the style chain defined in <chain.yml> step by step.
        Output: <image-dir>/<stem>_<chain-stem>.jpg

  --apply-style <name>
        Apply a single named style (case-insensitive). Only valid with
        --style-overview.

  --apply-random-style-chain <chain-dir>
        Pick a random .yml chain from <chain-dir> and apply it.
        Combine with --input-dir to process a whole folder of pictures,
        each with a different randomly chosen chain.

OPTIONAL PARAMETERS (apply to all JPEG-producing commands)
  --input-dir <dir>
        Process all JPEG/PNG images in <dir> instead of a single <image>.

  --output-dir <dir>
        Write output file(s) to <dir> instead of the source image folder.
        <dir> must already exist.

  --tile-size <N>
        Tile size for ONNX inference in pixels. Default: 1024 (or YAML value).

  --overlap <N>
        Tile overlap in pixels. Default: 128 (or YAML value).

  --strength-scale <N>
        Scale all chain-step strengths by N percent (1–300).
        Example: --strength-scale 60 turns 100% → 60%, 150% → 90%.

  --float16
        Enable float16 inference (faster on supported GPUs / DirectML).

EXAMPLES
  BatchStyler.exe --style-overview portrait.jpg
  BatchStyler.exe --style-overview portrait.jpg --apply-style "Candy"
  BatchStyler.exe --apply-style-chain rainbow.yml portrait.jpg
  BatchStyler.exe --apply-style-chain rainbow.yml portrait.jpg --strength-scale 80
  BatchStyler.exe --apply-style-chain rainbow.yml portrait.jpg --output-dir C:\output
  BatchStyler.exe --apply-random-style-chain C:\chains portrait.jpg
  BatchStyler.exe --input-dir C:\my_pics --apply-random-style-chain C:\chains --output-dir C:\out
  BatchStyler.exe --style-chain-overview C:\chains portrait.jpg
```

### What changes

**`src/batch_styler/app.py`** — replace the `_USAGE` constant entirely with the new text above,
updating `--outdir` → `--output-dir` throughout.

---

## Files Changed — Summary

| File | Changes |
|------|---------|
| `src/batch_styler/app.py` | Rename `--outdir`, add `--input-dir`, add `--apply-random-style-chain`, rewrite `_USAGE`, add `import random`, make `image` positional optional, add validation, wrap dispatch in loop |
| `src/batch_styler/commands.py` | No changes |
| `tests/scripts/test_batch_styler.py` | Rename docstring references to `--outdir`; add `TestInputDir` (6 tests); add `TestApplyRandomStyleChain` (5 tests) |

Total new tests: **11**

---

## Implementation Order

1. Rename `--outdir` → `--output-dir` (trivial, isolated)
2. Make `<image>` optional + add `--input-dir` validation + loop
3. Add `--apply-random-style-chain`
4. Rewrite help text
5. Write new tests

Each step keeps all existing tests green before moving to the next.

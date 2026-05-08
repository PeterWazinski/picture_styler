"""BatchStyler CLI entry point.

Usage::

    python -m src.batch_styler.app --style-overview path/to/photo.jpg
    python -m src.batch_styler.app --apply-style-chain my_chain.yml path/to/photo.jpg
    python -m src.batch_styler.app --style-chain-overview chains/ path/to/photo.jpg
    python -m src.batch_styler.app --apply-random-style-chain chains/ --input-dir pics/

When compiled with PyInstaller the entry point is ``BatchStyler.exe``.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# ── Repository root (must come before any src.* import) ─────────────────────
# When compiled with PyInstaller, sys.executable points to BatchStyler.exe.
# In dev mode, __file__ is src/batch_styler/app.py → up 3 levels = repo root.
if not getattr(sys, "frozen", False):
    _repo = Path(__file__).resolve().parent.parent.parent
    if str(_repo) not in sys.path:
        sys.path.insert(0, str(_repo))

import src.batch_styler.catalog as _catalog  # noqa: E402
from src.batch_styler.commands import (  # noqa: E402
    cmd_apply_style_chain,
    cmd_style_chain_overview,
    cmd_style_overview,
)
from src.core.registry import StyleRegistry  # noqa: E402


# ---------------------------------------------------------------------------
# CLI help / usage string
# ---------------------------------------------------------------------------

_USAGE = (
    "BatchStyler.exe  \u2014  batch style-transfer tool\n"
    "\n"
    "COMMANDS THAT CREATE CONTACT SHEETS (PDF overview)\n"
    "  --style-overview <image>\n"
    "        Apply all available styles to <image> at 100/150/200% strength and\n"
    "        write a DIN-A4 landscape PDF contact sheet.\n"
    "        Output: <image-dir>/<stem>_style_overview.pdf\n"
    "        Combine with --input-dir to produce one PDF per image in a folder.\n"
    "\n"
    "  --style-chain-overview <chain-dir> <image>\n"
    "        Apply every .yml chain in <chain-dir> to <image> and write a\n"
    "        portrait A4 PDF with one result per chain.\n"
    "        Output: <image-dir>/<stem>_<chain-dir-name>_overview.pdf\n"
    "        Combine with --input-dir to produce one PDF per image in a folder.\n"
    "\n"
    "COMMANDS THAT CREATE ONE OR MORE JPEG OUTPUT IMAGES\n"
    "  --apply-style-chain <chain.yml>\n"
    "        Apply the style chain defined in <chain.yml> step by step.\n"
    "        Output: <image-dir>/<stem>_<chain-stem>.jpg\n"
    "\n"
    "  --apply-style <name>\n"
    "        Apply a single named style (case-insensitive). Only valid with\n"
    "        --style-overview.\n"
    "\n"
    "  --apply-random-style-chain <chain-dir>\n"
    "        Pick a random .yml chain from <chain-dir> and apply it.\n"
    "        Combine with --input-dir to process a whole folder of pictures,\n"
    "        each with a different randomly chosen chain.\n"
    "\n"
    "OPTIONAL PARAMETERS (apply to all JPEG-producing commands)\n"
    "  --input-dir <dir>\n"
    "        Process all JPEG/PNG images in <dir> instead of a single <image>.\n"        "        Supported by all modes including --style-overview and\n"
        "        --style-chain-overview (one PDF per image).\n"    "\n"
    "  --output-dir <dir>\n"
    "        Write output file(s) to <dir> instead of the source image folder.\n"
    "        <dir> must already exist.\n"
    "\n"
    "  --tile-size <N>\n"
    "        Tile size for ONNX inference in pixels. Default: 1024 (or YAML value).\n"
    "\n"
    "  --overlap <N>\n"
    "        Tile overlap in pixels. Default: 128 (or YAML value).\n"
    "\n"
    "  --strength-scale <N>\n"
    "        Scale all chain-step strengths by N percent (1\u2013300).\n"
    "        Example: --strength-scale 60 turns 100%\u219260%, 150%\u219290%.\n"
    "\n"
    "  --float16\n"
    "        Enable float16 inference (faster on supported GPUs / DirectML).\n"
    "\n"
    "Available styles:\n"
    + _catalog._list_styles_for_help()
    + "\n"
    "\n"
    "EXAMPLES\n"
    "  BatchStyler.exe --style-overview portrait.jpg\n"
    "  BatchStyler.exe --style-overview portrait.jpg --apply-style \"Candy\"\n"
    "  BatchStyler.exe --apply-style-chain rainbow.yml portrait.jpg\n"
    "  BatchStyler.exe --apply-style-chain rainbow.yml portrait.jpg --strength-scale 80\n"
    "  BatchStyler.exe --apply-style-chain rainbow.yml portrait.jpg --output-dir C:\\\\output\n"
    "  BatchStyler.exe --apply-random-style-chain C:\\\\chains portrait.jpg\n"
    "  BatchStyler.exe --input-dir C:\\\\my_pics --apply-random-style-chain C:\\\\chains --output-dir C:\\\\out\n"
    "  BatchStyler.exe --style-chain-overview C:\\\\chains portrait.jpg\n"
    "  BatchStyler.exe --style-overview --input-dir C:\\\\pics --output-dir C:\\\\out\n"
    "  BatchStyler.exe --style-chain-overview C:\\\\chains --input-dir C:\\\\pics --output-dir C:\\\\out\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})


def _collect_images(input_dir: Path) -> list[Path]:
    """Return sorted list of JPEG/PNG files in *input_dir* (non-recursive)."""
    return sorted(p for p in input_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTENSIONS)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch style transfer.",
        add_help=True,
    )
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument(
        "--style-overview", action="store_true", dest="style_overview",
        help="Create a PDF contact sheet with all styles.",
    )
    mode_group.add_argument(
        "--apply-style-chain", type=Path, metavar="CHAIN", dest="apply_style_chain",
        help="Apply a saved style-chain YAML to the image.",
    )
    mode_group.add_argument(
        "--style-chain-overview", type=Path, metavar="CHAIN_DIR", dest="style_chain_overview",
        help="Apply all .yml chains in CHAIN_DIR and produce a portrait A4 PDF.",
    )
    mode_group.add_argument(
        "--apply-random-style-chain", type=Path, metavar="CHAIN_DIR",
        dest="apply_random_style_chain",
        help="Pick a random style-chain YAML from CHAIN_DIR and apply it to the image.",
    )
    parser.add_argument(
        "image", type=Path, nargs="?", default=None,
        help="Source image file (JPEG or PNG). Omit when using --input-dir.",
    )
    parser.add_argument(
        "--input-dir", type=Path, default=None, metavar="DIR", dest="input_dir",
        help="Process all JPEG/PNG images in DIR instead of a single <image>.",
    )
    parser.add_argument(
        "--tile-size", type=int, default=None,
        help="Tile size for inference in pixels. Default: use YAML value or 1024.",
    )
    parser.add_argument(
        "--overlap", type=int, default=None,
        help="Tile overlap in pixels. Default: use YAML value or 128.",
    )
    parser.add_argument(
        "--strength-scale", type=int, default=None, metavar="PCT", dest="strength_scale",
        help="Scale all chain step strengths by this percentage (1\u2013300). Capped at 300%%.",
    )
    parser.add_argument(
        "--float16", action="store_true", default=False,
        help="Use float16 inference (faster on GPU/DML)",
    )
    parser.add_argument(
        "--apply-style", type=str, default=None, metavar="NAME", dest="apply_style",
        help="Apply only this style (case-insensitive name). Only for --style-overview.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None, metavar="DIR", dest="output_dir",
        help="Write output file(s) to DIR instead of the source image folder. DIR must already exist.",
    )
    args = parser.parse_args()

    no_mode = (
        not args.style_overview
        and not args.apply_style_chain
        and not args.style_chain_overview
        and not args.apply_random_style_chain
    )
    if no_mode:
        print(_USAGE)
        sys.exit(1)

    # ── image source: exactly one of <image> or --input-dir ─────────────────
    if args.image is not None and args.input_dir is not None:
        sys.exit("Error: <image> and --input-dir are mutually exclusive — provide one or the other.")
    if args.image is None and args.input_dir is None:
        # --style-overview and --style-chain-overview historically require a positional image
        sys.exit("Error: provide either <image> or --input-dir.")

    # ── resolve output dir ───────────────────────────────────────────────────
    out_dir: Path | None = None
    if args.output_dir is not None:
        out_dir = args.output_dir.resolve()
        if not out_dir.is_dir():
            sys.exit(f"Error: --output-dir directory does not exist: {out_dir}")

    # ── build image path list ────────────────────────────────────────────────
    if args.input_dir is not None:
        input_dir = args.input_dir.resolve()
        if not input_dir.is_dir():
            sys.exit(f"Error: --input-dir directory does not exist: {input_dir}")
        image_paths = _collect_images(input_dir)
        if not image_paths:
            sys.exit(f"Error: no JPEG/PNG images found in {input_dir}")
    else:
        single = args.image.resolve()
        if not single.exists():
            sys.exit(f"Error: image not found: {single}")
        image_paths = [single]

    if args.strength_scale is not None and not (1 <= args.strength_scale <= 300):
        sys.exit("Error: --strength-scale must be between 1 and 300.")

    if args.apply_style and not args.style_overview:
        sys.exit("Error: --apply-style can only be used with --style-overview.")

    # ── dispatch ─────────────────────────────────────────────────────────────
    if args.apply_style_chain:
        for image_path in image_paths:
            cmd_apply_style_chain(
                image_path, args.apply_style_chain.resolve(),
                tile_size=args.tile_size,
                overlap=args.overlap,
                use_float16=args.float16,
                strength_scale=args.strength_scale,
                out_dir=out_dir,
            )
        return

    if args.apply_random_style_chain:
        chain_dir = args.apply_random_style_chain.resolve()
        if not chain_dir.is_dir():
            sys.exit(f"Error: chain directory does not exist: {chain_dir}")
        chain_files = sorted(set(
            list(chain_dir.glob("*.yml")) + list(chain_dir.glob("*.yaml"))
        ))
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

    if args.style_chain_overview:
        chain_dir = args.style_chain_overview.resolve()
        if not chain_dir.is_dir():
            sys.exit(f"Error: chain directory does not exist: {chain_dir}")
        for image_path in image_paths:
            print(f"Creating style chain overview for {image_path}")
            cmd_style_chain_overview(
                image_path, chain_dir,
                tile_size=args.tile_size,
                overlap=args.overlap,
                use_float16=args.float16,
                strength_scale=args.strength_scale,
                out_dir=out_dir,
            )
        return

    # --style-overview
    catalog_path = _catalog.REPO_ROOT / "styles" / "catalog.json"
    if not catalog_path.exists():
        sys.exit(f"Error: catalog not found: {catalog_path}")

    registry = StyleRegistry(catalog_path)
    styles = registry.list_styles()
    if not styles:
        sys.exit("No styles found in catalog.")

    if args.apply_style:
        matched = registry.find_by_name(args.apply_style)
        if matched is None:
            available = ", ".join(f"'{s.name}'" for s in registry.list_styles())
            sys.exit(
                f"Error: style '{args.apply_style}' not found in catalog.\n"
                f"Available styles: {available}"
            )
        styles = [matched]

    pdf_tile_size: int = args.tile_size if args.tile_size is not None else 1024
    pdf_overlap: int = args.overlap if args.overlap is not None else 128

    for image_path in image_paths:
        print(f"Creating style overview for {image_path}")
        cmd_style_overview(
            image_path, styles,
            tile_size=pdf_tile_size,
            overlap=pdf_overlap,
            strength=1.0,
            use_float16=args.float16,
            out_dir=out_dir,
        )


if __name__ == "__main__":
    main()


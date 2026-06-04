#!/bin/bash

#
# Build PetersPictureStyler app for macOS with PyInstaller.
#
# Description:
#   1. Installs / upgrades PyInstaller into the project venv.
#   2. Cleans any previous build/ and dist/ artifacts.
#   3. Invokes PyInstaller with picture_styler-mac.spec to produce a one-directory
#      bundle: dist/PetersPictureStyler/
#   4. Copies styles/ into the output directory so styles can be added later
#      without recompiling.
#
#   Output: dist/PetersPictureStyler/
#             PetersPictureStyler    ← executable GUI app
#             BatchStyler            ← headless CLI for batch style transfer
#             styles/                ← drop new style folders here
#             app.log                ← written at runtime
#
#   Copy the entire dist/PetersPictureStyler/ folder to any macOS machine.
#   To add a new style later, just drop its folder into styles/ and
#   append the entry to styles/catalog.json — no recompile needed.
#
# Notes:
#   * Only the Stylist UI app is compiled — the Trainer is a developer-only
#     workflow that requires the full dev environment (torch, torchvision).
#   * Run from the project root, or just call the script from anywhere — it
#     uses the script's directory to locate the venv and spec file automatically.
#   * The venv must already exist (.venv/).  Run:
#       python3.13 -m venv .venv && .venv/bin/pip install -r requirements-mac.txt
#     (requirements-mac.txt uses onnxruntime instead of the Windows-only
#     onnxruntime-directml that is in requirements.txt).
#   * torch / torchvision are excluded from the bundle (inference uses ONNX
#     Runtime only).
#

set -euo pipefail

Root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VenvPy="$Root/.venv/bin/python"
SpecFile="$Root/picture_styler-mac.spec"
OutputDir="$Root/dist/PetersPictureStyler-mac"
OutputExe="$OutputDir/PetersPictureStyler"
BatchExe="$OutputDir/BatchStyler"

# Verify the venv exists before doing anything else
if [ ! -f "$VenvPy" ]; then
    echo "Error: Python venv not found at $VenvPy"
    echo "Run: python3.13 -m venv .venv && .venv/bin/pip install -r requirements-mac.txt"
    exit 1
fi

# ── 1. Install / upgrade PyInstaller ─────────────────────────────────────
echo ""
echo "$(printf '\033[36m=== Installing / upgrading PyInstaller ===\033[0m')"
"$VenvPy" -m pip install --upgrade pyinstaller

# ── 2. Clean previous artifacts ──────────────────────────────────────────
echo ""
echo "$(printf '\033[36m=== Cleaning previous build artifacts ===\033[0m')"
for dir in "$Root/build" "$Root/dist"; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        echo "  Removed: $dir"
    fi
done

# ── 3. Run PyInstaller ───────────────────────────────────────────────────
echo ""
echo "$(printf '\033[36m=== Building PetersPictureStyler-mac/ (this takes a few minutes) ===\033[0m')"
"$VenvPy" -m PyInstaller "$SpecFile" --noconfirm

# ── 3b. Remove intermediate EXE stubs left in dist/ root ──────────────────
#    PyInstaller creates intermediate stubs as part of the COLLECT process.
#    These are not the final deliverables and should be removed.
echo ""
echo "$(printf '\033[36m=== Removing intermediate EXE stubs from dist/ ===\033[0m')"
for stub in "$Root/dist/PetersPictureStyler_app" "$Root/dist/BatchStyler" "$Root/dist/PetersPictureStyler"; do
    if [ -f "$stub" ]; then
        rm -f "$stub"
        echo "  Removed: $stub"
    fi
done

# ── 4. Rename GUI executable inside output directory ─────────────────────
#    The spec file names it PetersPictureStyler_app to avoid naming collision
#    with the COLLECT directory. Rename it to the final name inside the bundle.
echo ""
echo "$(printf '\033[36m=== Renaming GUI executable ===\033[0m')"
if [ -f "$OutputDir/PetersPictureStyler_app" ]; then
    mv "$OutputDir/PetersPictureStyler_app" "$OutputDir/PetersPictureStyler"
    echo "  Renamed: PetersPictureStyler_app → PetersPictureStyler"
fi

# ── 4b. Fix runtime library path and re-sign ────────────────────────────
#    PyInstaller 6.x on macOS does not embed an LC_RPATH entry pointing to
#    _internal/, so the bootloader falls back to looking in a nonexistent
#    /tmp/_MEI... temp directory and fails.  We add the rpath manually with
#    install_name_tool, then re-sign each executable (without --deep so that
#    the Qt / Python frameworks inside _internal/ keep their own signatures).
echo ""
echo "$(printf '\033[36m=== Adding @loader_path/_internal RPATH ===\033[0m')"
for exe in "$OutputDir/PetersPictureStyler" "$OutputDir/BatchStyler"; do
    if [ -f "$exe" ]; then
        install_name_tool -add_rpath @loader_path/_internal "$exe" 2>/dev/null || true
        echo "  Added rpath to: $(basename "$exe")"
    fi
done

echo ""
echo "$(printf '\033[36m=== Re-signing executables (ad-hoc, no --deep) ===\033[0m')"
for exe in "$OutputDir/PetersPictureStyler" "$OutputDir/BatchStyler"; do
    if [ -f "$exe" ]; then
        codesign -f -s - "$exe" > /dev/null 2>&1
        echo "  Signed: $(basename "$exe")"
    fi
done

# ── 5. Copy styles/ into the output directory ────────────────────────────
echo ""
echo "$(printf '\033[36m=== Copying styles/ into output directory ===\033[0m')"
SrcStyles="$Root/styles"
DstStyles="$OutputDir/styles"
if [ -d "$DstStyles" ]; then
    rm -rf "$DstStyles"
fi
cp -r "$SrcStyles" "$DstStyles"
StyleCount=$(find "$DstStyles" -maxdepth 1 -type d ! -name styles | wc -l)
echo "  Copied $StyleCount style folder(s) to $DstStyles"

# ── 6. Copy style_chains/ into the output directory ──────────────────────
echo ""
echo "$(printf '\033[36m=== Copying style_chains/ into output directory ===\033[0m')"
SrcChains="$Root/style_chains"
DstChains="$OutputDir/style_chains"
if [ -d "$DstChains" ]; then
    rm -rf "$DstChains"
fi

if [ -d "$SrcChains" ]; then
    cp -r "$SrcChains" "$DstChains"
    ChainCount=$(find "$DstChains" -maxdepth 1 -type d ! -name style_chains | wc -l)
    echo "  Copied $ChainCount chain folder(s) to $DstChains"
else
    # Create an empty placeholder so the app finds the directory on first run
    mkdir -p "$DstChains"
    echo '{"chains":[]}' > "$DstChains/catalog.json"
    echo "  style_chains/ not found -- created empty placeholder at $DstChains"
fi

# ── 6. Report result ─────────────────────────────────────────────────────
if [ -f "$OutputExe" ]; then
    ExeSize=$(du -h "$OutputExe" | cut -f1)
    BatchSize=$([ -f "$BatchExe" ] && du -h "$BatchExe" | cut -f1 || echo "?")
    DirSize=$(du -sh "$OutputDir" | cut -f1)

    echo ""
    echo "$(printf '\033[32m=== Build successful ===\033[0m')"
    echo "    $OutputDir/  ($DirSize total)"
    echo "    $OutputExe  ($ExeSize)"
    echo "    $BatchExe  ($BatchSize)"
    echo ""
    echo "$(printf '\033[33mCopy the entire dist/PetersPictureStyler/ folder to any macOS machine.\033[0m')"
    echo "$(printf '\033[33mTo add a new style: drop its folder into styles/ and update styles/catalog.json.\033[0m')"
else
    echo "Error: Expected output not found: $OutputExe"
    exit 1
fi

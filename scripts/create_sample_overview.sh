#!/usr/bin/env bash
set -euo pipefail

# ── paths relative to this scripts/ folder ───────────────────────────────────
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BATCHSTYLER="$ROOT/dist/PictureStyler/BatchStyler"
SAMPLE_PICS="$ROOT/sample_images/sample_pics"
STYLE_OUT="$ROOT/sample_images/style-overviews"
CHAIN_OUT="$ROOT/sample_images/style-chain-overviews"
CHAIN_DIR="$ROOT/sample_images/style-chains"

# ── sanity checks ─────────────────────────────────────────────────────────────
if [ ! -f "$BATCHSTYLER" ]; then
    echo "ERROR: BatchStyler not found at $BATCHSTYLER"
    echo "       Run compile-mac.sh first."
    exit 1
fi
if [ ! -d "$SAMPLE_PICS" ]; then
    echo "ERROR: sample_pics folder not found: $SAMPLE_PICS"
    exit 1
fi

# ── ensure output dirs exist ──────────────────────────────────────────────────
mkdir -p "$STYLE_OUT"
mkdir -p "$CHAIN_OUT"

# ── delete old PDFs ───────────────────────────────────────────────────────────
echo "Deleting old style-overview PDFs..."
rm -f "$STYLE_OUT"/*.pdf

echo "Deleting old style-chain-overview PDFs..."
rm -f "$CHAIN_OUT"/*.pdf

# ── style overviews (one PDF per sample pic) ──────────────────────────────────
echo ""
echo "=== Creating style overviews ==="
"$BATCHSTYLER" --style-overview --input-dir "$SAMPLE_PICS" --output-dir "$STYLE_OUT" || \
    echo "WARNING: style-overview failed"

# ── style-chain overviews (one PDF per sample pic) ────────────────────────────
echo ""
echo "=== Creating style-chain overviews ==="
"$BATCHSTYLER" --style-chain-overview "$CHAIN_DIR" --input-dir "$SAMPLE_PICS" --output-dir "$CHAIN_OUT" || \
    echo "WARNING: style-chain-overview failed"

echo ""
echo "Done."
echo "  Style overviews   : $STYLE_OUT"
echo "  Chain overviews   : $CHAIN_OUT"

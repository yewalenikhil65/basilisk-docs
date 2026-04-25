#!/usr/bin/env bash
# =============================================================================
# build_docs.sh — Generate Basilisk CFD documentation (verbose)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BASILISK_DIR="$SCRIPT_DIR/basilisk"

echo "========================================"
echo " Basilisk Documentation Builder"
echo "========================================"
echo ""

# ── 1. Prerequisites ────────────────────────────────────────────────────────
echo "[1/5] Checking prerequisites..."
for cmd in doxygen dot python3; do
    if command -v "$cmd" &>/dev/null; then
        echo "  ✓ $cmd found: $(command -v $cmd)"
    else
        echo "  ✗ $cmd MISSING — install with: brew install doxygen graphviz python3"
        exit 1
    fi
done
echo ""

# ── 2. Source ────────────────────────────────────────────────────────────────
echo "[2/5] Checking Basilisk source..."
if [ -f "$BASILISK_DIR/src/common.h" ]; then
    FILE_COUNT=$(find "$BASILISK_DIR/src" -name '*.h' -o -name '*.c' | grep -v -E '(examples|test|darcsit|gl/|wsServer|paraver|ppr/|ast/|jview)' | wc -l | tr -d ' ')
    echo "  ✓ Source found at $BASILISK_DIR/src"
    echo "  ✓ $FILE_COUNT .h/.c files to process (after excludes)"
else
    echo "  ✗ Source not found. Downloading tarball..."
    curl -L --progress-bar http://basilisk.fr/basilisk/basilisk.tar.gz -o basilisk.tar.gz
    echo "  Extracting..."
    tar xzf basilisk.tar.gz
    rm basilisk.tar.gz
    echo "  ✓ Extracted"
fi
echo ""

# ── 3. Test filter ───────────────────────────────────────────────────────────
echo "[3/5] Testing Basilisk C filter on common.h..."
python3 basilisk_filter.py "$BASILISK_DIR/src/common.h" > /dev/null 2>&1 && echo "  ✓ Filter works" || {
    echo "  ✗ Filter failed! Trying to see error:"
    python3 basilisk_filter.py "$BASILISK_DIR/src/common.h" 2>&1 | tail -5
    exit 1
}
echo ""

# ── 4. Doxygen ───────────────────────────────────────────────────────────────
echo "[4/5] Running Doxygen..."
echo "  Config: CALL_GRAPH=NO, CALLER_GRAPH=NO (fast build)"
echo "  Graphs: include deps, collaboration, class hierarchy, directory"
echo "  This should take 1-3 minutes..."
echo ""
rm -rf output

START=$(date +%s)
doxygen Doxyfile 2>&1 | while IFS= read -r line; do
    # Show progress lines (Generating ..., Parsing ..., etc.)
    case "$line" in
        Parsing*|Generating*|Reading*|Searching*|Building*|Running*|Patching*|Adding*|Computing*|Creating*|Writing*|Finalizing*|lookup*|Preprocessing*)
            echo "  $line"
            ;;
        *warning:*|*error:*)
            echo "  ⚠ $line"
            ;;
    esac
done
END=$(date +%s)
ELAPSED=$((END - START))
echo ""
echo "  Doxygen finished in ${ELAPSED}s"
echo ""

# ── 5. Literate site ────────────────────────────────────────────────────────
echo "[5/5] Generating literate documentation site..."
python3 generate_literate_site.py \
    --src "$BASILISK_DIR/src" \
    --doxygen-html ./output/html \
    --out ./output/literate 2>&1 | while IFS= read -r line; do
    echo "  $line"
done
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo "========================================"
echo " BUILD COMPLETE"
echo "========================================"
if [ -f output/html/index.html ]; then
    HTML=$(find output/html -name '*.html' | wc -l | tr -d ' ')
    SVG=$(find output/html -name '*.svg' | wc -l | tr -d ' ')
    LIT=$(find output/literate -name '*.html' 2>/dev/null | wc -l | tr -d ' ')
    echo ""
    echo " Doxygen API:    $HTML pages, $SVG diagrams"
    echo " Literate docs:  $LIT pages"
    echo ""
    echo " Open:"
    echo "   open output/literate/index.html   ← start here"
    echo "   open output/html/index.html       ← API reference"
else
    echo ""
    echo " ✗ Doxygen output not found. Check errors above."
    exit 1
fi

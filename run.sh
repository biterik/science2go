#!/bin/bash
# Science2Go - Quick launcher
# Finds the "science2go" conda environment for whichever user/Mac runs it
# (no hard-coded user names), then starts the GUI.
#
# Usage:
#   ./run.sh          (normal launch)
#   bash run.sh       (if not executable)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
# The code lives in science2go-main/ when launched from the repo root
[ -f main.py ] || cd "$SCRIPT_DIR/science2go-main"

PYTHON=""
CANDIDATES=()
if command -v conda >/dev/null 2>&1; then
    CANDIDATES+=("$(conda info --base 2>/dev/null)/envs/science2go/bin/python")
fi
CANDIDATES+=(
    "$HOME/miniforge3/envs/science2go/bin/python"
    "$HOME/mambaforge/envs/science2go/bin/python"
    "$HOME/miniconda3/envs/science2go/bin/python"
    "$HOME/anaconda3/envs/science2go/bin/python"
    "$HOME/.conda/envs/science2go/bin/python"
)
for p in "${CANDIDATES[@]}"; do
    if [ -x "$p" ]; then PYTHON="$p"; break; fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: science2go conda environment not found. Looked in:"
    printf '  %s\n' "${CANDIDATES[@]}"
    echo ""
    echo "Create it with:"
    echo "  conda env create -f \"$SCRIPT_DIR/environment.yml\""
    exit 1
fi

echo "Using: $PYTHON"
# Put the environment's bin/ (contains ffmpeg) first on PATH, like "conda activate"
export PATH="$(dirname "$PYTHON"):$PATH"
exec "$PYTHON" main.py "$@"

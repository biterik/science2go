#!/bin/bash
# Science2Go - Quick launcher
# Uses the science2go conda environment directly
#
# Usage:
#   ./run.sh          (normal launch)
#   bash run.sh       (if not executable)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use the science2go environment Python directly
PYTHON="/Users/oq50iqeq/miniforge3/envs/science2go/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Error: science2go conda environment not found at:"
    echo "  $PYTHON"
    echo ""
    echo "Create it with:"
    echo "  conda env create -f environment.yml"
    exit 1
fi

echo "Using: $PYTHON"
exec "$PYTHON" main.py "$@"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

mkdir -p data output log stats query/dml docs configs scripts
touch data/.gitkeep output/.gitkeep log/.gitkeep stats/.gitkeep

echo "initialized directories"

#!/usr/bin/env bash
# Compatibility shim for older local instructions. The Python orchestrator is portable.
set -euo pipefail
python scripts/rebuild_all.py "$@"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if codex exec --cd "$ROOT_DIR" resume --last "continue"; then
  exit 0
fi

codex exec --cd "$ROOT_DIR" "continue"

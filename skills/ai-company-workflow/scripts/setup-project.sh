#!/usr/bin/env bash
# Initialize the AI Company integration contract for a project.
# Usage: setup-project.sh /path/to/project
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/../templates/ai-company.example.yaml"
DEST_DIR="${1:-.}"
DEST="$DEST_DIR/.ai-company.yaml"

if [ ! -d "$DEST_DIR" ]; then
  echo "error: directory not found: $DEST_DIR" >&2
  exit 1
fi
if [ -f "$DEST" ]; then
  echo "exists: $DEST (not overwritten)"
  exit 0
fi
cp "$SRC" "$DEST"
echo "created: $DEST"
echo "next: edit the hooks (tracker / review_gate / deploy / notify), then run AI Company in that project."

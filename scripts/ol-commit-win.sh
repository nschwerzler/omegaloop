#!/usr/bin/env bash
# ol-commit-win.sh — Store a win from a worktree experiment
#
# Usage: ol-commit-win.sh <session-id> <win-number> <title> [description]
#
# This script:
#   1. Captures the diff from the worktree
#   2. Copies changed files to the win folder
#   3. Writes the win summary
#   4. Updates the manifest
#   5. Commits to main branch OmegaLoop folder

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[AR]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

SESSION_ID="${1:?Usage: ol-commit-win.sh <session-id> <win-number> <title> [description]}"
WIN_NUM="${2:?Win number required}"
TITLE="${3:?Win title required}"
DESCRIPTION="${4:-No description provided}"

REPO_ROOT=$(git rev-parse --show-toplevel)
AR_DIR="$REPO_ROOT/OmegaLoop/$SESSION_ID"
MANIFEST="$AR_DIR/manifest.json"

if [[ ! -f "$MANIFEST" ]]; then
  err "Session $SESSION_ID not found"
  exit 1
fi

WORKTREE_PATH=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['worktree_path'])")

if [[ ! -d "$WORKTREE_PATH" ]]; then
  err "Worktree not found at $WORKTREE_PATH"
  exit 1
fi

WIN_DIR_NAME=$(printf 'win-%03d' "$WIN_NUM")
WIN_DIR="$AR_DIR/wins/$WIN_DIR_NAME"
mkdir -p "$WIN_DIR/files"

log "Storing win #$WIN_NUM: $TITLE"

# 1. Commit changes in worktree
cd "$WORKTREE_PATH"
git add -A
git commit -m "AR-$SESSION_ID: Win #$WIN_NUM - $TITLE" --quiet 2>/dev/null || true

# 2. Capture diff
git diff HEAD~1 > "$WIN_DIR/changes.diff" 2>/dev/null || echo "No diff available" > "$WIN_DIR/changes.diff"
git show --stat HEAD > "$WIN_DIR/commit-info.txt" 2>/dev/null || true
git log -1 --format='%H' > "$WIN_DIR/commit-hash.txt" 2>/dev/null || true

# 3. Copy changed files
CHANGED_FILES=$(git diff --name-only HEAD~1 2>/dev/null || echo "")
for f in $CHANGED_FILES; do
  if [[ -f "$WORKTREE_PATH/$f" ]]; then
    mkdir -p "$WIN_DIR/files/$(dirname "$f")"
    cp "$WORKTREE_PATH/$f" "$WIN_DIR/files/$f"
  fi
done

# 4. Write summary
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$WIN_DIR/summary.md" << EOF
# Win #$WIN_NUM: $TITLE

**Session**: $SESSION_ID
**Timestamp**: $NOW

## Description
$DESCRIPTION

## Changed Files
$(echo "$CHANGED_FILES" | sed 's/^/- /')

## Diff Preview
\`\`\`diff
$(head -100 "$WIN_DIR/changes.diff")
\`\`\`
EOF

# 5. Update manifest
cd "$REPO_ROOT"
python3 << PYEOF
import json
from datetime import datetime, timezone

with open('$MANIFEST') as f:
    m = json.load(f)

m['win_count'] = int('$WIN_NUM')
m['updated_at'] = datetime.now(timezone.utc).isoformat()
m['consecutive_no_wins'] = 0

m.setdefault('wins', []).append({
    'win_id': '$WIN_DIR_NAME',
    'experiment_id': f"exp-{int('$WIN_NUM'):03d}",
    'title': '$TITLE',
    'commit_hash': open('$WIN_DIR/commit-hash.txt').read().strip() if open('$WIN_DIR/commit-hash.txt').read().strip() else 'unknown',
    'artifacts_path': 'wins/$WIN_DIR_NAME',
    'metrics_delta': {}
})

with open('$MANIFEST', 'w') as f:
    json.dump(m, f, indent=2)
PYEOF

# 6. Commit to main branch
git add "OmegaLoop/$SESSION_ID/"
git commit -m "OL: Win #$WIN_NUM in $SESSION_ID - $TITLE" --quiet

ok "Win #$WIN_NUM stored and committed: $TITLE"

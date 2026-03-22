#!/usr/bin/env bash
# ol-cleanup.sh — Clean up OmegaLoop worktrees and optionally archive sessions
#
# Usage:
#   ol-cleanup.sh list                    # List all sessions and their status
#   ol-cleanup.sh worktrees               # Remove all worktrees (keeps OmegaLoop data)
#   ol-cleanup.sh worktree <session-id>   # Remove specific worktree
#   ol-cleanup.sh archive <session-id>    # Mark session as completed
#   ol-cleanup.sh hub                     # Regenerate The OmegaLoop

set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'
log()  { echo -e "${BLUE}[AR]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || { echo "Not in a git repo"; exit 1; })
AR_ROOT="$REPO_ROOT/OmegaLoop"
COMMAND="${1:-list}"

case "$COMMAND" in
  list)
    echo ""
    echo "OmegaLoop Sessions in $REPO_ROOT"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for d in "$AR_ROOT"/*/; do
      [[ -f "$d/manifest.json" ]] || continue
      SID=$(basename "$d")
      STATUS=$(python3 -c "import json; print(json.load(open('$d/manifest.json'))['status'])" 2>/dev/null || echo "unknown")
      WINS=$(python3 -c "import json; print(json.load(open('$d/manifest.json'))['win_count'])" 2>/dev/null || echo "?")
      EXPS=$(python3 -c "import json; print(json.load(open('$d/manifest.json'))['experiment_count'])" 2>/dev/null || echo "?")
      PROMPT=$(python3 -c "import json; p=json.load(open('$d/manifest.json'))['research_prompt']; print(p[:60]+'...' if len(p)>60 else p)" 2>/dev/null || echo "?")
      echo -e "  ${GREEN}$SID${NC}  [$STATUS]  ${WINS} wins / ${EXPS} exp"
      echo -e "    ${YELLOW}$PROMPT${NC}"
    done
    echo ""
    WORKTREE_COUNT=$(git worktree list 2>/dev/null | grep -c "ol-worktrees" || echo "0")
    echo "Active worktrees: $WORKTREE_COUNT"
    echo ""
    ;;

  worktrees)
    log "Removing all AR worktrees..."
    for wt in "$REPO_ROOT/.git/ol-worktrees"/*/; do
      [[ -d "$wt" ]] || continue
      SID=$(basename "$wt")
      git worktree remove "$wt" --force 2>/dev/null && ok "Removed worktree: $SID" || true
      git branch -D "ar/$SID" 2>/dev/null || true
    done
    ok "All AR worktrees cleaned up"
    ;;

  worktree)
    SID="${2:?Session ID required}"
    WT="$REPO_ROOT/.git/ol-worktrees/$SID"
    if [[ -d "$WT" ]]; then
      git worktree remove "$WT" --force 2>/dev/null
      git branch -D "ar/$SID" 2>/dev/null || true
      ok "Removed worktree for $SID"
    else
      log "No worktree found for $SID"
    fi
    ;;

  archive)
    SID="${2:?Session ID required}"
    MANIFEST="$AR_ROOT/$SID/manifest.json"
    if [[ -f "$MANIFEST" ]]; then
      python3 -c "
import json
from datetime import datetime, timezone
m = json.load(open('$MANIFEST'))
m['status'] = 'completed'
m['updated_at'] = datetime.now(timezone.utc).isoformat()
json.dump(m, open('$MANIFEST', 'w'), indent=2)
"
      # Remove worktree if exists
      WT="$REPO_ROOT/.git/ol-worktrees/$SID"
      [[ -d "$WT" ]] && git worktree remove "$WT" --force 2>/dev/null && git branch -D "ar/$SID" 2>/dev/null || true

      cd "$REPO_ROOT"
      git add "OmegaLoop/$SID/manifest.json"
      git commit -m "OL: Complete session $SID" --quiet
      ok "Session $SID archived and committed"
    else
      echo "Session $SID not found"
    fi
    ;;

  hub)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$SCRIPT_DIR/generate-omegaloop.py" ]]; then
      python3 "$SCRIPT_DIR/generate-omegaloop.py" "$AR_ROOT"
    else
      echo "The OmegaLoop generator not found. Expected at: $SCRIPT_DIR/generate-omegaloop.py"
      exit 1
    fi
    ;;

  *)
    echo "Usage: ol-cleanup.sh {list|worktrees|worktree <id>|archive <id>|hub}"
    exit 1
    ;;
esac

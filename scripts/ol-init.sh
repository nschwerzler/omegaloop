#!/usr/bin/env bash
# ol-init.sh — Initialize an OmegaLoop session
#
# Usage: ol-init.sh "Research prompt here" [--max N] [--resume SESSION_ID]
#
# This script:
#   1. Detects the git repo root and current branch
#   2. Creates the OmegaLoop folder structure
#   3. Generates a unique session ID
#   4. Creates an isolated git worktree
#   5. Writes the initial manifest.json
#   6. Commits the session initialization
#
# Exit codes:
#   0 — Success
#   1 — Not in a git repo
#   2 — Uncommitted changes on current branch
#   3 — Invalid arguments

set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
BLUE='\033[0;34m'; PURPLE='\033[0;35m'; NC='\033[0m'

log()  { echo -e "${BLUE}[AR]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Parse arguments
PROMPT=""
MAX_EXPERIMENTS=50
RESUME_SESSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max)      MAX_EXPERIMENTS="$2"; shift 2 ;;
    --resume)   RESUME_SESSION="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: ol-init.sh \"Research prompt\" [--max N] [--resume SESSION_ID]"
      exit 0
      ;;
    *)          PROMPT="$1"; shift ;;
  esac
done

# --- Resume mode ---
if [[ -n "$RESUME_SESSION" ]]; then
  REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { err "Not in a git repo"; exit 1; }
  AR_DIR="$REPO_ROOT/OmegaLoop/$RESUME_SESSION"

  if [[ ! -f "$AR_DIR/manifest.json" ]]; then
    err "Session $RESUME_SESSION not found at $AR_DIR"
    exit 1
  fi

  log "Resuming session: $RESUME_SESSION"

  # Check if worktree exists, recreate if not
  WORKTREE_PATH=$(python3 -c "import json; print(json.load(open('$AR_DIR/manifest.json'))['worktree_path'])")
  WORKTREE_BRANCH=$(python3 -c "import json; print(json.load(open('$AR_DIR/manifest.json'))['worktree_branch'])")

  if [[ ! -d "$WORKTREE_PATH" ]]; then
    warn "Worktree not found, recreating..."
    git worktree add "$WORKTREE_PATH" "$WORKTREE_BRANCH" 2>/dev/null || {
      err "Could not recreate worktree. Branch $WORKTREE_BRANCH may not exist."
      exit 1
    }
    ok "Worktree recreated at $WORKTREE_PATH"
  fi

  # Update status
  python3 -c "
import json
m = json.load(open('$AR_DIR/manifest.json'))
m['status'] = 'looping'
json.dump(m, open('$AR_DIR/manifest.json', 'w'), indent=2)
"

  EXP_COUNT=$(python3 -c "import json; print(json.load(open('$AR_DIR/manifest.json'))['experiment_count'])")
  WIN_COUNT=$(python3 -c "import json; print(json.load(open('$AR_DIR/manifest.json'))['win_count'])")

  ok "Session resumed. $EXP_COUNT experiments done, $WIN_COUNT wins."
  echo "SESSION_ID=$RESUME_SESSION"
  echo "AR_DIR=$AR_DIR"
  echo "WORKTREE_PATH=$WORKTREE_PATH"
  exit 0
fi

# --- New session mode ---
if [[ -z "$PROMPT" ]]; then
  err "No research prompt provided"
  echo "Usage: ol-init.sh \"Research prompt\" [--max N]"
  exit 3
fi

# 1. Detect git repo
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { err "Not in a git repo"; exit 1; }
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO_NAME=$(basename "$REPO_ROOT")
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "no-remote")

log "Repo: $REPO_NAME ($REPO_ROOT)"
log "Branch: $CURRENT_BRANCH"

# 2. Check for uncommitted changes
if [[ -n "$(git status --porcelain)" ]]; then
  warn "Uncommitted changes detected. Stashing..."
  git stash push -m "OL: Auto-stash before session init"
fi

# 3. Generate session ID
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
PROMPT_HASH=$(echo "$PROMPT" | md5sum 2>/dev/null | cut -c1-6 || echo "$RANDOM")
SESSION_ID="${TIMESTAMP}-${PROMPT_HASH}"

log "Session ID: $SESSION_ID"

# 4. Create OmegaLoop folder structure
AR_DIR="$REPO_ROOT/OmegaLoop/$SESSION_ID"
mkdir -p "$AR_DIR"/{logs,wins,checkpoints/baseline}

# Copy .gitignore template if OmegaLoop is new
if [[ ! -f "$REPO_ROOT/OmegaLoop/.gitignore" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$SCRIPT_DIR/../templates/ol-gitignore" ]]; then
    cp "$SCRIPT_DIR/../templates/ol-gitignore" "$REPO_ROOT/OmegaLoop/.gitignore"
  else
    # Inline fallback
    echo -e "*.tmp\n*.swp\n*~\n.DS_Store\nThumbs.db\n.orchestrator/**/bin/\n.orchestrator/**/obj/" \
      > "$REPO_ROOT/OmegaLoop/.gitignore"
  fi
fi

# 5. Create worktree
WORKTREE_DIR="$REPO_ROOT/.git/ol-worktrees"
WORKTREE_PATH="$WORKTREE_DIR/$SESSION_ID"
WORKTREE_BRANCH="ar/$SESSION_ID"

mkdir -p "$WORKTREE_DIR"

git branch "$WORKTREE_BRANCH" "$CURRENT_BRANCH" 2>/dev/null || true
git worktree add "$WORKTREE_PATH" "$WORKTREE_BRANCH" 2>/dev/null || {
  err "Could not create worktree"
  exit 1
}
ok "Worktree created at $WORKTREE_PATH"

# 6. Write manifest.json
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$AR_DIR/manifest.json" << MANIFEST
{
  "schema_version": "1.0",
  "session_id": "$SESSION_ID",
  "created_at": "$NOW",
  "updated_at": "$NOW",
  "research_prompt": $(python3 -c "import json; print(json.dumps('$PROMPT'))"),
  "repo_root": "$REPO_ROOT",
  "repo_name": "$REPO_NAME",
  "base_branch": "$CURRENT_BRANCH",
  "worktree_branch": "$WORKTREE_BRANCH",
  "worktree_path": "$WORKTREE_PATH",
  "status": "analyzing",
  "experiment_count": 0,
  "win_count": 0,
  "max_experiments": $MAX_EXPERIMENTS,
  "last_checkpoint": null,
  "current_strategy": "low-hanging",
  "consecutive_no_wins": 0,
  "evaluation_criteria": {},
  "experiments": [],
  "wins": [],
  "insights": []
}
MANIFEST

# 7. Write research-prompt.md
cat > "$AR_DIR/research-prompt.md" << PROMPT_MD
# OmegaLoop Session: $SESSION_ID

## Research Prompt
> $PROMPT

## Context
- **Repository**: $REPO_NAME
- **Branch**: $CURRENT_BRANCH
- **Remote**: $REMOTE_URL
- **Started**: $NOW
- **Max Experiments**: $MAX_EXPERIMENTS

## Evaluation Criteria
_To be filled during analysis phase._

## Notes
_Add notes here as the research progresses._
PROMPT_MD

# 8. Commit initialization
cd "$REPO_ROOT"
git add "OmegaLoop/"
git commit -m "OL: Initialize session $SESSION_ID" --quiet

ok "Session initialized and committed"

# 9. Output for the calling agent
echo ""
echo "========================================="
echo "  OmegaLoop Session Ready"
echo "========================================="
echo "  SESSION_ID=$SESSION_ID"
echo "  AR_DIR=$AR_DIR"
echo "  WORKTREE_PATH=$WORKTREE_PATH"
echo "  MAX_EXPERIMENTS=$MAX_EXPERIMENTS"
echo "========================================="
echo ""
log "Next: Analyze the codebase in the worktree and establish baseline."
log "Then: Start the experiment loop."

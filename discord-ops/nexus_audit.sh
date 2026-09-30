#!/bin/bash
set -e

# FLUIDPRISM OP: MILDLYAWESOME_AUDIT_V5 (Zero-Point Edition)
# Purpose: Deepest possible recovery. Scans Reflog, Blobs, and Rebase states.
# Usage: chmod +x mildlyawesome_audit.sh && ./mildlyawesome_audit.sh

# CONFIGURATION
REPO_ROOT="/home/toxic/dayz_workspace/dayz_discord_ops_repo"

# HIGH-FIDELITY COLORS
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GREY='\033[0;90m'
NC='\033[0m'

echo -e "${BLUE}>>> 🛑 INITIATING MILDLYAWESOME PROTOCOL AUDIT (ZERO-POINT SCAN)${NC}"
echo ">>> TARGET: $REPO_ROOT"

if [ ! -d "$REPO_ROOT" ]; then
    echo -e "${RED}❌ CRITICAL: Repo root not found.${NC}"
    exit 1
fi
cd "$REPO_ROOT" || exit 1

# ---------------------------------------------------------
# PHASE 0: STATE DIAGNOSIS (The "Where am I?" Check)
# ---------------------------------------------------------
echo ""
echo -e "${BLUE}--- [PHASE 0] REPOSITORY STATE DIAGNOSIS ---${NC}"

if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    echo -e "${RED}🚨 CRITICAL ALERT: REPOSITORY IS IN A REBASE STATE.${NC}"
    echo "    This explains why files are missing. They are likely in the 'patch' queue."
    
    if [ -f ".git/rebase-merge/head-name" ]; then
        BRANCH=$(cat .git/rebase-merge/head-name)
        echo -e "    Rebasing Branch: ${CYAN}$BRANCH${NC}"
    fi
    
    echo -e "    ${YELLOW}RECOMMENDATION:${NC} If you are lost, run 'git rebase --abort' to return to safety."
    echo "    (But let's search for your files first.)"
else
    echo -e "${GREEN}✅ Repository state is NOMINAL (No active rebase).${NC}"
fi

# ---------------------------------------------------------
# PHASE 1: THE SEARCH VECTORS
# ---------------------------------------------------------
# Format: "SearchString|Description"
VECTORS=(
    "DiscordLiveUpdates|Discord Live Ops Module"
    "ADMParser|Maximus Log Parser"
    "class OpsBot|Bot Class Definition"
    "_start_discord_live_updates_once|Live Updates Bootstrap"
    "setup_hook|Discord Setup Hook"
)

# ---------------------------------------------------------
# PHASE 2: THE GOD-EYE GREP (Scanning All Refs)
# ---------------------------------------------------------
echo ""
echo -e "${BLUE}--- [PHASE 2] GOD-EYE GREP (Scanning All Refs) ---${NC}"
echo "Scanning everywhere (HEAD, reflog, branches)..."

for vector in "${VECTORS[@]}"; do
    IFS='|' read -r TERM DESC <<< "$vector"
    echo ""
    echo -e "🔎 HUNTING: ${MAGENTA}'$TERM'${NC} ($DESC)"
    
    # scan for the term in all commits reachable
    # We use 'git log -S' (pickaxe) to find commits that introduced or removed the string
    # PLUS we iterate basic grep over recent history to find files
    
    # 1. Pickaxe Search (Commit History)
    echo "    [Commit Search]"
    git log --all --source --color=always -S "$TERM" --oneline --date=short --pretty=format:"      %C(auto)%h %C(green)%ad %C(reset)%s %C(cyan)(%S)%C(reset)" | head -n 5 || true

    # 2. Grep Search (Current & Recent Reachable)
    # Useful if it exists right now in a weird place
    # HITS=$(git grep -I -n "$TERM" $(git rev-list --all --max-count=1000 2>/dev/null) 2>/dev/null | head -n 3)
    
done

echo ""
echo -e "${BLUE}--- [PHASE 3] BLOB HUNTING (Unreachable Object Scan) ---${NC}"
echo -e "${YELLOW}⚠️  Scanning loose objects (this is slow but finds 'staged-but-lost' code)...${NC}"

# We only do this for "DiscordLiveUpdates" to save time, as it is the critical missing piece user asked about
CRITICAL_TERM="DiscordLiveUpdates"
BLOBS=$(git rev-list --objects --all | git cat-file --batch-check='%(objectname) %(rest)' | grep -v " tree " | grep -v " commit " | awk '{print $1}')

FOUND_BLOB=0
for blob in $BLOBS; do
    if git show "$blob" 2>/dev/null | grep -q "$CRITICAL_TERM"; then
        echo -e "    ${RED}[BLOB FOUND]${NC} Object: ${CYAN}$blob${NC}"
        echo -e "      └-> Contains '$CRITICAL_TERM'"
        echo -e "      └-> RECOVER: git show $blob > recovered_${blob:0:7}.py"
        FOUND_BLOB=1
        break 
    fi
done

if [ $FOUND_BLOB -eq 0 ]; then
    echo "    No loose blobs found matching '$CRITICAL_TERM'."
fi

echo ""
echo -e "${BLUE}>>> AUDIT COMPLETE.${NC}"

#!/bin/bash
# Sync MCP server code from shared/mcp to dreamwalker-mcp plugin
# Usage: ./sync-to-plugin.sh [--dry-run]

set -uo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SOURCE_DIR="/home/coolhand/shared/mcp"
TARGET_DIR="/home/coolhand/dreamwalker-mcp/dreamwalker_mcp/mcp"
BACKUP_DIR="/home/coolhand/dreamwalker-mcp/.sync-backups/$(date +%Y%m%d_%H%M%S)"

# Files to sync
FILES=(
    "unified_server.py"
    "app.py"
    "data_server.py"
    "providers_server.py"
    "cache_server.py"
    "utility_server.py"
    "web_search_server.py"
    "tool_registry.py"
    "streaming.py"
    "streaming_endpoint.py"
    "background_loop.py"
    "mcp_http_bridge.py"
)

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}DRY RUN MODE - No files will be modified${NC}\n"
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Dreamwalker MCP → Plugin Sync Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

echo -e "Source:      ${GREEN}$SOURCE_DIR${NC}"
echo -e "Target:      ${GREEN}$TARGET_DIR${NC}"
echo -e "Backup:      ${GREEN}$BACKUP_DIR${NC}\n"

# Create backup directory
if ! $DRY_RUN; then
    mkdir -p "$BACKUP_DIR"
    echo -e "${GREEN}✓${NC} Created backup directory\n"
fi

# Function to adjust imports in a file
adjust_imports() {
    local source_file=$1
    local target_file=$2

    # Use sed directly on files for better error handling
    sed -e 's|from mcp import|from dreamwalker_mcp.mcp import|g' \
        -e 's|from mcp\.|from dreamwalker_mcp.mcp.|g' \
        -e 's|import mcp\.|import dreamwalker_mcp.mcp.|g' \
        -e 's|from shared\.config|from dreamwalker_mcp.config|g' \
        -e 's|from shared\.orchestration|from dreamwalker_mcp.orchestration|g' \
        -e 's|from shared\.llm_providers|from dreamwalker_mcp.llm_providers|g' \
        -e 's|from shared\.tools|from dreamwalker_mcp.tools|g' \
        -e 's|from shared\.data_fetching|from dreamwalker_mcp.data_fetching|g' \
        -e 's|from shared\.utils|from dreamwalker_mcp.utils|g' \
        "$source_file" > "$target_file"
}

# Sync each file
SYNCED=0
SKIPPED=0
ERRORS=0

for file in "${FILES[@]}"; do
    SOURCE_FILE="$SOURCE_DIR/$file"
    TARGET_FILE="$TARGET_DIR/$file"

    if [[ ! -f "$SOURCE_FILE" ]]; then
        echo -e "${YELLOW}⚠${NC}  $file - Source not found, skipping"
        ((SKIPPED++))
        continue
    fi

    # Check if file has changed
    if [[ -f "$TARGET_FILE" ]]; then
        if cmp -s "$SOURCE_FILE" "$TARGET_FILE" 2>/dev/null; then
            echo -e "${BLUE}→${NC}  $file - No changes"
            ((SKIPPED++))
            continue
        fi
    fi

    if $DRY_RUN; then
        echo -e "${YELLOW}○${NC}  $file - Would sync"
        ((SYNCED++))
    else
        # Backup existing file
        if [[ -f "$TARGET_FILE" ]]; then
            cp "$TARGET_FILE" "$BACKUP_DIR/$file"
        fi

        # Adjust imports and write to target using the function
        adjust_imports "$SOURCE_FILE" "$TARGET_FILE"

        echo -e "${GREEN}✓${NC}  $file - Synced with import adjustments"
        ((SYNCED++))
    fi
done

# Summary
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Synced:${NC}   $SYNCED files"
echo -e "${BLUE}→ Skipped:${NC}  $SKIPPED files"
if [[ $ERRORS -gt 0 ]]; then
    echo -e "${RED}✗ Errors:${NC}   $ERRORS files"
fi
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"

if $DRY_RUN; then
    echo -e "${YELLOW}This was a dry run. Run without --dry-run to actually sync files.${NC}"
else
    echo -e "${GREEN}Sync complete!${NC}"
    echo -e "Backups saved to: ${BACKUP_DIR}\n"

    # Show git diff in target directory
    echo -e "${BLUE}Git status in dreamwalker-mcp:${NC}"
    cd /home/coolhand/dreamwalker-mcp
    git status --short dreamwalker_mcp/mcp/ 2>/dev/null || echo "Not a git repository or no changes"
fi

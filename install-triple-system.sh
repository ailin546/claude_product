#!/bin/bash
# Triple-System Installer for Claude Code
# Installs Agency Agents + Superpowers + ECC into any project
#
# Usage (remote - from any project):
#   curl -sL https://raw.githubusercontent.com/ailin546/claude_product/main/install-triple-system.sh | bash
#   curl -sL https://raw.githubusercontent.com/ailin546/claude_product/main/install-triple-system.sh | bash -s /path/to/project
#
# Usage (local - from claude_product repo):
#   ./install-triple-system.sh [target-project-path]
#
# Source: https://github.com/ailin546/claude_product

set -e

REPO_URL="https://github.com/ailin546/claude_product.git"
BRANCH="main"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Triple-System Installer for Claude Code${NC}"
echo ""

# Determine source: local repo or remote clone
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" 2>/dev/null)" 2>/dev/null && pwd 2>/dev/null)" || SCRIPT_DIR=""
CLEANUP_TEMP=""

if [ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/.claude" ]; then
    # Running locally from the claude_product repo
    SOURCE_DIR="$SCRIPT_DIR"
    echo "Mode: local install"
else
    # Running remotely (curl | bash) — clone the repo to a temp dir
    echo "Mode: remote install (cloning from GitHub...)"
    TEMP_DIR=$(mktemp -d)
    CLEANUP_TEMP="$TEMP_DIR"

    if ! git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TEMP_DIR/claude_product" 2>/dev/null; then
        echo -e "${RED}Error: Failed to clone $REPO_URL${NC}"
        echo "Check your network connection and that the repo is accessible."
        rm -rf "$TEMP_DIR"
        exit 1
    fi

    SOURCE_DIR="$TEMP_DIR/claude_product"
    echo "  Cloned successfully."
fi

SOURCE_CLAUDE="$SOURCE_DIR/.claude"

# Determine target project
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" 2>/dev/null && pwd)" || {
    echo -e "${RED}Error: Target directory '$1' does not exist${NC}"
    [ -n "$CLEANUP_TEMP" ] && rm -rf "$CLEANUP_TEMP"
    exit 1
}
TARGET_CLAUDE="$TARGET/.claude"

echo "Source: $SOURCE_CLAUDE"
echo "Target: $TARGET_CLAUDE"
echo ""

# Check source exists
if [ ! -d "$SOURCE_CLAUDE" ]; then
    echo -e "${RED}Error: Source .claude/ not found at $SOURCE_CLAUDE${NC}"
    [ -n "$CLEANUP_TEMP" ] && rm -rf "$CLEANUP_TEMP"
    exit 1
fi

# Create target .claude/ if not exists
mkdir -p "$TARGET_CLAUDE"

# Copy function with count
copy_component() {
    local name="$1"
    local src="$SOURCE_CLAUDE/$2"
    local dst="$TARGET_CLAUDE/$2"

    echo -ne "${YELLOW}Copying $name...${NC} "
    if [ -d "$src" ]; then
        cp -r "$src" "$TARGET_CLAUDE/" 2>/dev/null && echo "done" || echo "skipped (not found)"
    else
        echo "skipped (not found)"
    fi
}

copy_component "agents"         "agents"
copy_component "skills"         "skills"
copy_component "commands"       "commands"
copy_component "rules"          "rules"
copy_component "scripts"        "scripts"
copy_component "strategies"     "strategies"
copy_component "examples"       "examples"
copy_component "best-practice"  "best-practice"
copy_component "mcp-configs"    "mcp-configs"

echo -ne "${YELLOW}Copying settings.json...${NC} "
if [ ! -f "$TARGET_CLAUDE/settings.json" ]; then
    cp "$SOURCE_CLAUDE/settings.json" "$TARGET_CLAUDE/" 2>/dev/null && echo "done" || echo "skipped"
else
    echo "skipped (already exists)"
fi

# Copy CLAUDE.md to project root if not exists
echo -ne "${YELLOW}Copying CLAUDE.md...${NC} "
if [ ! -f "$TARGET/CLAUDE.md" ]; then
    cp "$SOURCE_DIR/CLAUDE.md" "$TARGET/" 2>/dev/null && echo "done" || echo "skipped"
else
    echo "skipped (already exists)"
fi

# Cleanup temp clone if used
[ -n "$CLEANUP_TEMP" ] && rm -rf "$CLEANUP_TEMP"

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Installed:"
echo "  - Agency Agents: 78 specialized personas (WHO)"
echo "  - Superpowers:   14 workflow skills (HOW)"
echo "  - ECC:           92 skills + 48 commands + hooks (INFRASTRUCTURE)"
echo "  - Best Practice: 20 reference documents"
echo ""
echo "Next steps:"
echo "  git add .claude/ CLAUDE.md"
echo "  git commit -m 'Add triple-system for Claude Code'"
echo "  git push"
echo ""
echo "Works on:"
echo "  - Local Claude Code CLI: immediately"
echo "  - Cloud claude.ai/code:  after git commit & push"
echo "  - Other machines:        after git clone"

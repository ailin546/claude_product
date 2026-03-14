#!/bin/bash
# Triple-System Installer for Claude Code
# Installs Agency Agents + Superpowers + ECC into any project
#
# Usage:
#   curl -sL <raw-url>/install-triple-system.sh | bash
#   # or
#   ./install-triple-system.sh [target-project-path]
#
# Source: https://github.com/ailin546/claude_product

set -e

# Determine source (where this script's .claude/ lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_CLAUDE="$SCRIPT_DIR/.claude"

# Determine target project
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" && pwd)"
TARGET_CLAUDE="$TARGET/.claude"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Triple-System Installer for Claude Code${NC}"
echo "Source: $SOURCE_CLAUDE"
echo "Target: $TARGET_CLAUDE"
echo ""

# Check source exists
if [ ! -d "$SOURCE_CLAUDE" ]; then
    echo "Error: Source .claude/ not found at $SOURCE_CLAUDE"
    echo "Run this script from the claude_product directory."
    exit 1
fi

# Create target .claude/ if not exists
mkdir -p "$TARGET_CLAUDE"

# Copy components
echo -e "${YELLOW}Copying agents...${NC}"
cp -r "$SOURCE_CLAUDE/agents" "$TARGET_CLAUDE/" 2>/dev/null && echo "  $(ls "$TARGET_CLAUDE/agents/"*.md 2>/dev/null | wc -l) agents"

echo -e "${YELLOW}Copying skills...${NC}"
cp -r "$SOURCE_CLAUDE/skills" "$TARGET_CLAUDE/" 2>/dev/null && echo "  $(ls -d "$TARGET_CLAUDE/skills/"*/ 2>/dev/null | wc -l) skills"

echo -e "${YELLOW}Copying commands...${NC}"
cp -r "$SOURCE_CLAUDE/commands" "$TARGET_CLAUDE/" 2>/dev/null && echo "  $(ls "$TARGET_CLAUDE/commands/"*.md 2>/dev/null | wc -l) commands"

echo -e "${YELLOW}Copying rules...${NC}"
cp -r "$SOURCE_CLAUDE/rules" "$TARGET_CLAUDE/" 2>/dev/null && echo "  $(find "$TARGET_CLAUDE/rules" -name '*.md' 2>/dev/null | wc -l) rule files"

echo -e "${YELLOW}Copying scripts...${NC}"
cp -r "$SOURCE_CLAUDE/scripts" "$TARGET_CLAUDE/" 2>/dev/null && echo "  $(ls "$TARGET_CLAUDE/scripts/hooks/"* 2>/dev/null | wc -l) hook scripts"

echo -e "${YELLOW}Copying strategies...${NC}"
cp -r "$SOURCE_CLAUDE/strategies" "$TARGET_CLAUDE/" 2>/dev/null && echo "  copied"

echo -e "${YELLOW}Copying examples...${NC}"
cp -r "$SOURCE_CLAUDE/examples" "$TARGET_CLAUDE/" 2>/dev/null && echo "  copied"

echo -e "${YELLOW}Copying best-practice docs...${NC}"
cp -r "$SOURCE_CLAUDE/best-practice" "$TARGET_CLAUDE/" 2>/dev/null && echo "  copied"

echo -e "${YELLOW}Copying MCP configs...${NC}"
cp -r "$SOURCE_CLAUDE/mcp-configs" "$TARGET_CLAUDE/" 2>/dev/null && echo "  copied"

echo -e "${YELLOW}Copying settings.json...${NC}"
if [ ! -f "$TARGET_CLAUDE/settings.json" ]; then
    cp "$SOURCE_CLAUDE/settings.json" "$TARGET_CLAUDE/" && echo "  copied"
else
    echo "  skipped (already exists)"
fi

# Copy CLAUDE.md to project root if not exists
if [ ! -f "$TARGET/CLAUDE.md" ]; then
    cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/" && echo -e "${YELLOW}Copied CLAUDE.md to project root${NC}"
else
    echo -e "${YELLOW}CLAUDE.md already exists, skipped${NC}"
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Installed:"
echo "  - Agency Agents: 78 specialized personas (WHO)"
echo "  - Superpowers:   14 workflow skills (HOW)"
echo "  - ECC:           92 skills + 48 commands + hooks (INFRASTRUCTURE)"
echo "  - Best Practice: 20 reference documents"
echo ""
echo "Works on:"
echo "  - Local Claude Code CLI: immediately"
echo "  - Cloud claude.ai/code:  after git commit & push"
echo "  - Other machines:        after git clone"

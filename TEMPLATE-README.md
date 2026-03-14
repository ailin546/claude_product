# Claude Code Triple-System Template

A complete AI development framework integrating three complementary systems for Claude Code.

## What's Inside

| Layer | System | Source | Components |
|-------|--------|--------|-----------|
| **Infrastructure** | ECC | [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | 17 agents, 92 skills, 48 commands, hooks, rules |
| **Process** | Superpowers | [obra/superpowers](https://github.com/obra/superpowers) | TDD, debugging, brainstorming, quality gates |
| **Expertise** | Agency Agents | [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | 78 specialized personas |
| **Knowledge** | Best Practice | [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) | 20 reference documents |

## Quick Install

### Method 1: One-Line Remote Install (Recommended)

Run this from any project directory — no cloning needed:

```bash
curl -sL https://raw.githubusercontent.com/ailin546/claude_product/claude/explore-agency-agents-fymmN/install-triple-system.sh | bash
```

Or specify a target project:

```bash
curl -sL https://raw.githubusercontent.com/ailin546/claude_product/claude/explore-agency-agents-fymmN/install-triple-system.sh | bash -s /path/to/your/project
```

### Method 2: Local Install

Clone this repo, then run the script pointing to your target project:

```bash
git clone https://github.com/ailin546/claude_product.git
cd claude_product
./install-triple-system.sh /path/to/your/project
```

### Method 3: Copy Manually

```bash
# Copy the .claude/ directory and CLAUDE.md to your project
cp -r claude_product/.claude/ /path/to/your/project/
cp claude_product/CLAUDE.md /path/to/your/project/
```

### Method 4: Use as GitHub Template

1. Use this repo as a template when creating a new GitHub repository
2. Your new project will start with the full triple-system pre-configured

## After Installation

1. `git add .claude/ CLAUDE.md` — stage the config
2. `git commit -m "Add triple-system for Claude Code"` — commit
3. `git push` — push to remote

Now the triple-system works everywhere:
- **Local CLI**: immediately
- **Cloud claude.ai/code**: after push
- **Other machines**: after clone

## How It Works

```
User Request
    │
    ├─► ECC Infrastructure (automatic hooks)
    │   SessionStart → load previous context
    │   PostToolUse → auto-format, typecheck, quality gate
    │   Stop → persist state, extract patterns, track cost
    │
    ├─► Superpowers Process (workflow discipline)
    │   brainstorming → writing-plans → subagent-driven-development
    │   test-driven-development / systematic-debugging
    │   verification-before-completion
    │
    └─► Agency Agents Expertise (domain knowledge)
        Auto-routes to matching specialist persona
        (Security Engineer, Backend Architect, Code Reviewer, etc.)
```

## License

All source projects are MIT licensed.

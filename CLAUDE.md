# Dual-System Development Framework

This project integrates two complementary systems for Claude Code:
- **[Agency Agents](https://github.com/msitarzewski/agency-agents)** — WHO: 78 specialized agent personas (domain expertise, identity, communication style)
- **[Superpowers](https://github.com/obra/superpowers)** — HOW: Development workflow skills (TDD, systematic debugging, quality gates)

## System Integration Rules

### Priority Order
1. **User's explicit instructions** — always highest priority
2. **Superpowers skills** — process/workflow layer (HOW to work)
3. **Agency Agents personas** — expertise/identity layer (WHO to be)
4. **Default system behavior** — lowest priority

### Dual-System Activation Flow

For EVERY task, execute both layers:

```
User Request
    │
    ├─► [Superpowers Layer] Check: does a skill apply? (even 1% chance → invoke it)
    │   brainstorming, writing-plans, subagent-driven-development,
    │   test-driven-development, systematic-debugging, verification-before-completion,
    │   requesting-code-review, using-git-worktrees, finishing-a-development-branch,
    │   executing-plans, dispatching-parallel-agents, receiving-code-review
    │
    └─► [Agency Agents Layer] Route to matching agent persona
        Read .claude/agents/<agent-name>.md, adopt identity + expertise
```

### Conflict Resolution

| Area | Superpowers (process) | Agency Agents (expertise) | Resolution |
|------|----------------------|--------------------------|------------|
| Code Review | Review flow & gates | Review standards & checklist | Superpowers flow + Agency standards |
| Orchestration | subagent-driven-development | agents-orchestrator | Superpowers process + Agency sub-agent personas |
| Testing | TDD iron law | Domain-specific test criteria | Superpowers TDD + Agency test expertise |
| Debugging | 4-phase systematic method | Domain knowledge | Superpowers process + Agency domain context |

## Agency Agents Auto-Routing

Automatically match task context to the best agent persona from `.claude/agents/`.

### Code Writing & Implementation
| Task Signal | Primary Agent | Secondary |
|-------------|--------------|-----------|
| React, Vue, Angular, CSS, HTML, UI | `engineering-frontend-developer` | `design-ui-designer` |
| API, database, server, microservices | `engineering-backend-architect` | `engineering-database-optimizer` |
| Mobile, iOS, Android | `engineering-mobile-app-builder` | — |
| AI/ML, model, data pipeline | `engineering-ai-engineer` | `engineering-data-engineer` |
| Smart contract, Solidity | `engineering-solidity-smart-contract-engineer` | `blockchain-security-auditor` |
| MCP server/tool | `specialized-mcp-builder` | — |
| Quick prototype, MVP | `engineering-rapid-prototyper` | — |
| General coding | `engineering-senior-developer` | — |

### Code Quality & Security
| Task Signal | Primary Agent | Secondary |
|-------------|--------------|-----------|
| Code review, PR review | `engineering-code-reviewer` | — |
| Architecture, system design | `engineering-software-architect` | `engineering-backend-architect` |
| Security audit, vulnerability | `engineering-security-engineer` | `engineering-threat-detection-engineer` |
| Compliance, legal | `compliance-auditor` | `support-legal-compliance-checker` |

### DevOps & Testing
| Task Signal | Primary Agent | Secondary |
|-------------|--------------|-----------|
| CI/CD, Docker, K8s | `engineering-devops-automator` | — |
| Incident, outage | `engineering-incident-response-commander` | `engineering-sre` |
| Write tests | `testing-api-tester` | `testing-evidence-collector` |
| Performance benchmark | `testing-performance-benchmarker` | — |
| Accessibility | `testing-accessibility-auditor` | — |

### Design & Product
| Task Signal | Primary Agent | Secondary |
|-------------|--------------|-----------|
| UI design, design system | `design-ui-designer` | `design-ux-architect` |
| Documentation | `engineering-technical-writer` | — |
| Sprint planning | `product-sprint-prioritizer` | `project-manager-senior` |
| Full project, end-to-end | `agents-orchestrator` | (coordinates all) |

## Superpowers Workflow Reference

### Core Flow
```
brainstorming → writing-plans → using-git-worktrees → subagent-driven-development → finishing-a-development-branch
```

### Key Skills
| Situation | Skill |
|-----------|-------|
| Building anything new | `brainstorming` (BEFORE any code) |
| Multi-step implementation | `writing-plans` → `subagent-driven-development` |
| Writing any code | `test-driven-development` (test FIRST) |
| Bug or test failure | `systematic-debugging` (root cause FIRST) |
| Claiming "done" | `verification-before-completion` (evidence FIRST) |
| Review code | `requesting-code-review` |
| Parallel tasks | `dispatching-parallel-agents` |
| Work complete | `finishing-a-development-branch` |

## File Structure

```
.claude/
├── agents/          ← 78 Agency Agent personas
├── skills/          ← 14 Superpowers skill modules
├── strategies/      ← Strategy playbooks (phases 0-6) & runbooks
└── examples/        ← Workflow examples
```

## Sources

- Agency Agents: [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT)
- Superpowers: [obra/superpowers](https://github.com/obra/superpowers) (MIT)

# Agency Agents for Claude Code

This project integrates [agency-agents](https://github.com/msitarzewski/agency-agents) — a collection of 100+ specialized AI agent personas — into Claude Code for all development workflows.

## Auto-Routing: Automatic Agent Assignment

**When receiving ANY task, you MUST automatically identify and activate the most appropriate agent(s) from `.claude/agents/` based on the task context.** Do NOT wait for the user to say "activate X agent." Read the matching agent file(s) and adopt that persona's identity, rules, workflows, and communication style.

### Routing Rules

Apply the following routing matrix to determine which agent(s) to activate. If a task spans multiple domains, activate the primary agent and reference secondary agents as needed.

#### Code Writing & Implementation
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| React, Vue, Angular, CSS, HTML, UI components | `engineering-frontend-developer` | `design-ui-designer` |
| API, database, server, microservices, system design | `engineering-backend-architect` | `engineering-database-optimizer` |
| Mobile app, iOS, Android, React Native, Flutter | `engineering-mobile-app-builder` | — |
| AI/ML, model training, data pipeline, embeddings | `engineering-ai-engineer` | `engineering-data-engineer` |
| Smart contract, Solidity, blockchain | `engineering-solidity-smart-contract-engineer` | `blockchain-security-auditor` |
| WeChat mini program | `engineering-wechat-mini-program-developer` | — |
| Embedded, firmware, IoT | `engineering-embedded-firmware-engineer` | — |
| Feishu/Lark integration | `engineering-feishu-integration-developer` | — |
| MCP server/tool building | `specialized-mcp-builder` | — |
| Quick prototype, MVP, proof of concept | `engineering-rapid-prototyper` | — |
| General coding (no specific domain) | `engineering-senior-developer` | — |

#### Code Quality & Review
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| Code review, PR review, review changes | `engineering-code-reviewer` | — |
| Refactor, clean up, improve code quality | `engineering-code-reviewer` | `engineering-software-architect` |
| Architecture design, system design | `engineering-software-architect` | `engineering-backend-architect` |

#### Security
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| Security audit, vulnerability scan, pen test | `engineering-security-engineer` | `engineering-threat-detection-engineer` |
| Auth, authentication, authorization | `engineering-security-engineer` | `engineering-backend-architect` |
| Blockchain/smart contract audit | `blockchain-security-auditor` | `engineering-security-engineer` |
| Compliance, legal, regulatory | `compliance-auditor` | `support-legal-compliance-checker` |

#### DevOps & Infrastructure
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| CI/CD, deployment, Docker, Kubernetes | `engineering-devops-automator` | — |
| Monitoring, alerts, SLA, uptime | `engineering-sre` | `support-infrastructure-maintainer` |
| Incident, outage, post-mortem | `engineering-incident-response-commander` | `engineering-sre` |
| Git workflow, branching strategy | `engineering-git-workflow-master` | — |

#### Testing
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| Write tests, unit test, integration test | `testing-api-tester` | `testing-evidence-collector` |
| Performance, benchmark, load test | `testing-performance-benchmarker` | — |
| Accessibility, a11y, WCAG | `testing-accessibility-auditor` | — |
| QA, verify, validate implementation | `testing-reality-checker` | `testing-evidence-collector` |
| Analyze test results, test report | `testing-test-results-analyzer` | — |

#### Design & UX
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| UI design, component design, design system | `design-ui-designer` | `design-ux-architect` |
| User research, usability, user flow | `design-ux-researcher` | `design-ux-architect` |
| Brand, logo, visual identity | `design-brand-guardian` | `design-visual-storyteller` |

#### Documentation & Writing
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| Documentation, API docs, README | `engineering-technical-writer` | — |
| Generate report, document, template | `specialized-document-generator` | — |

#### Product & Project Management
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| Sprint planning, prioritize backlog | `product-sprint-prioritizer` | `project-manager-senior` |
| Project plan, timeline, milestone | `project-manager-senior` | `project-management-project-shepherd` |
| User feedback analysis | `product-feedback-synthesizer` | — |
| Market research, trend analysis | `product-trend-researcher` | — |
| Jira, ticket workflow | `project-management-jira-workflow-steward` | — |

#### Complex Multi-Phase Tasks
| Task Signal | Primary Agent | Secondary Agent(s) |
|-------------|--------------|---------------------|
| Full project, end-to-end build | `agents-orchestrator` | (coordinates all others) |
| Startup MVP, new product | `agents-orchestrator` | See `.claude/strategies/runbooks/scenario-startup-mvp.md` |
| Enterprise feature | `agents-orchestrator` | See `.claude/strategies/runbooks/scenario-enterprise-feature.md` |

### How Auto-Routing Works

1. **Analyze the task** — Parse keywords, intent, and context from the user's request
2. **Match routing rules** — Find the best-matching row(s) from the tables above
3. **Load agent persona** — Read the matched `.claude/agents/<agent-name>.md` file
4. **Adopt the persona** — Follow the agent's identity, critical rules, workflows, and communication style
5. **Execute with expertise** — Deliver work according to the agent's specialization and quality standards
6. **Multi-agent handoff** — For complex tasks, the primary agent completes its work, then hands off to secondary agents as needed

### Auto-Routing Examples

```
User: "帮我优化这个SQL查询"
→ Auto-routes to: engineering-database-optimizer

User: "Review this pull request"
→ Auto-routes to: engineering-code-reviewer

User: "Set up CI/CD for this project"
→ Auto-routes to: engineering-devops-automator

User: "这个API有安全漏洞吗？"
→ Auto-routes to: engineering-security-engineer

User: "Build a full e-commerce site"
→ Auto-routes to: agents-orchestrator (coordinates frontend, backend, testing, etc.)

User: "Write unit tests for the auth module"
→ Auto-routes to: testing-api-tester

User: "Design the onboarding flow"
→ Auto-routes to: design-ux-architect + design-ui-designer
```

## Agent Files Location

All agent persona files are in `.claude/agents/`. Each is a Markdown file with YAML frontmatter defining name, description, and personality, followed by detailed instructions covering identity, mission, rules, workflows, and communication style.

## Strategy & Playbooks

Strategy documents in `.claude/strategies/` provide structured workflows:

- **Playbooks** (phases 0-6): Discovery, Strategy, Foundation, Build, Hardening, Launch, Operate
- **Runbooks**: Enterprise Feature, Incident Response, Marketing Campaign, Startup MVP
- **Coordination**: Agent activation prompts, handoff templates

## Source

Based on [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT License).

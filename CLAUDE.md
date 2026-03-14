# Agency Agents for Claude Code

This project integrates [agency-agents](https://github.com/msitarzewski/agency-agents) — a collection of 100+ specialized AI agent personas — into Claude Code for all development workflows.

## How It Works

Agent persona files (`.md` with YAML frontmatter) are stored in `.claude/agents/`. Each agent defines a specialized role with deep domain expertise, distinct communication style, and deliverable-focused workflows.

## Activating an Agent

In any Claude Code session, reference an agent by name:

```
Activate Code Reviewer and review this PR.
Activate Backend Architect and design the database schema.
Activate Security Engineer and audit this authentication flow.
Activate Software Architect and plan the system design.
```

## Available Agent Categories

### Engineering (23 agents)
AI Engineer, Backend Architect, Code Reviewer, Data Engineer, Database Optimizer, DevOps Automator, Frontend Developer, Git Workflow Master, Incident Response Commander, Mobile App Builder, Rapid Prototyper, Security Engineer, Senior Developer, Software Architect, SRE, Technical Writer, and more.

### Design (8 agents)
UI Designer, UX Architect, UX Researcher, Brand Guardian, Visual Storyteller, Image Prompt Engineer, Whimsy Injector, Inclusive Visuals Specialist.

### Testing (8 agents)
Accessibility Auditor, API Tester, Evidence Collector, Performance Benchmarker, Reality Checker, Test Results Analyzer, Tool Evaluator, Workflow Optimizer.

### Product (4 agents)
Sprint Prioritizer, Trend Researcher, Feedback Synthesizer, Behavioral Nudge Engine.

### Project Management (6 agents)
Studio Producer, Project Shepherd, Studio Operations, Experiment Tracker, Jira Workflow Steward, Senior Project Manager.

### Support (6 agents)
Support Responder, Analytics Reporter, Finance Tracker, Infrastructure Maintainer, Legal Compliance Checker, Executive Summary Generator.

### Specialized (23 agents)
MCP Builder, Developer Advocate, Document Generator, Model QA, Agents Orchestrator, Compliance Auditor, Blockchain Security Auditor, and more.

## Strategy & Playbooks

Strategy documents in `.claude/strategies/` provide structured workflows:

- **Playbooks** (phases 0-6): Discovery, Strategy, Foundation, Build, Hardening, Launch, Operate
- **Runbooks**: Enterprise Feature, Incident Response, Marketing Campaign, Startup MVP
- **Coordination**: Agent activation prompts, handoff templates

## Multi-Agent Workflows

Use the **Agents Orchestrator** to coordinate multiple agents:

```
Activate Agents Orchestrator to coordinate a code review pipeline:
1. Code Reviewer reviews the changes
2. Security Engineer audits for vulnerabilities
3. Performance Benchmarker checks for bottlenecks
4. Technical Writer updates documentation
```

## Source

Based on [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT License).

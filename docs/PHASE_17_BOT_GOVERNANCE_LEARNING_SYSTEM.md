# Phase 17 — Bot Governance + Learning System

## Overview

Phase 17 adds a controlled bot governance and learning system so every AI/bot/parser/automation action can be measured, reviewed, improved, and governed over time.

## Architecture

```
Bot Action → Record → Feedback → Learning Candidate → Prompt/Rule Version → Approval → Activation
                ↓                        ↓
         Performance Snapshot    Guardrail Check
```

### Key Principles
- Learning system observes and proposes
- Humans approve improvements
- All prompt/rule changes are versioned and auditable
- Bots cannot self-modify in production

## Models (12 tables)

| Table | Purpose |
|-------|---------|
| `bot_agents` | Registry of all bot/AI agents |
| `bot_action_records` | Every action a bot proposes/takes |
| `bot_feedback_records` | Human feedback on bot actions |
| `bot_performance_snapshots` | Periodic scorecards |
| `bot_prompt_versions` | Versioned prompts with approval lifecycle |
| `bot_rule_versions` | Versioned rule configs with approval lifecycle |
| `bot_learning_candidates` | Improvement proposals |
| `bot_training_cases` | Input/output pairs for evaluation |
| `bot_evaluation_runs` | Deterministic evaluation against training cases |
| `bot_evaluation_results` | Per-case evaluation results |
| `bot_guardrail_violations` | Blocked unsafe actions |
| `bot_quality_reviews` | Periodic HOD quality reviews |

## Default Bot Agents

- AI Assistant, Gmail Parser, Document Intelligence
- Workflow Exception Detector, Container Risk Checker
- Finance Credit Checker, Notification Checker
- Exception Detector, Approval Router

## Permissions

| Role | Capabilities |
|------|-------------|
| ADMIN | Full access, pause/resume bots, activate versions, run evaluations |
| STAFF | View performance, submit feedback, create learning candidates |
| VIEW_ONLY | Read-only dashboard/list/detail |

## Guardrails

Blocked actions:
- Autonomous write proposals
- Gmail send/modify/delete
- Secrets in metadata
- Approval bypass attempts
- Low-confidence auto-apply

## How Phase 17 Prepares Phase 18

Phase 17 establishes the measurement and governance framework. Future phases can:
- Use performance data to auto-route approvals
- Identify high-performing bots for reduced oversight
- Build predictive models from training cases
- Optimize prompts based on evaluation results

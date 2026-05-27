# Phase 16 — Approval Engine + HOD Bot Governance

## Overview

Phase 16 adds a formal approval layer on top of exceptions, finance holds, workflow-sensitive actions, document intelligence suggestions, Gmail suggestions, credit waivers, release actions, and bot actions.

No risky operational action happens only because a user, AI, OCR, Gmail parser, or automation suggested it. Sensitive actions pass through a structured approval workflow.

## Architecture

```
Action Request → Policy Match → Approval Steps → Decision → Execute/Lock Release
                                     ↓
                              Audit Trail + Notifications
```

### Key Principles
- Approval engine governs decisions
- Execution happens only after explicit allowed user action
- All approvals and overrides are audited
- Bot/AI actions remain proposals until approved
- Maker-checker enforced for high-risk actions

## Models

| Table | Purpose |
|-------|---------|
| `approval_requests` | Core approval records with lifecycle |
| `approval_steps` | Multi-step approval chain |
| `approval_policies` | Configurable policy rules per type/risk |
| `approval_policy_rules` | Condition-based policy rules |
| `approval_request_evidence` | Supporting evidence for decisions |
| `approval_action_locks` | Prevent action execution until approved |
| `approval_delegations` | HOD/ADMIN delegation during absence |
| `approval_overrides` | Manual override audit trail |
| `bot_governance_actions` | Bot/AI action proposals |

## Approval Lifecycle

```
draft → pending → in_review → approved → executed
                           ↘ rejected
                           ↘ changes_requested → pending
                 → cancelled
                 → expired
```

## Default Policies

| Type | Risk | Approver | Steps | Maker-Checker |
|------|------|----------|-------|---------------|
| Finance Hold Waiver | High | ADMIN | 1 | Yes |
| Finance Hold Waiver | Critical | ADMIN | 2 | Yes |
| Release Action | High/Critical | ADMIN | 1-2 | Yes |
| Document Intelligence Apply | Medium | STAFF | 1 | No |
| Document Intelligence Apply | High | ADMIN | 1 | Yes |
| Workflow Transition | High | ADMIN | 1 | Yes |
| Credit Limit Override | High | ADMIN | 1 | Yes |
| Bot Action | Medium/High | ADMIN | 1-2 | Yes (high) |

## Permissions

| Role | Capabilities |
|------|-------------|
| ADMIN | Full access, policy edit, override, execute, approve/reject |
| STAFF | Create/submit requests, approve if assigned and policy allows |
| VIEW_ONLY | Read-only list/detail/summary |

## Bot Governance

- Bot actions are recorded as proposals
- Proposals must be submitted for approval before execution
- ADMIN reviews and approves/rejects bot actions
- No bot action executes without explicit human approval

## How Phase 16 Prepares Phase 17

Phase 16 establishes the governance framework. Phase 17 (Bot Governance + Learning System) will expand:
- Bot learning from approval decisions
- Predictive approval routing
- Automated risk scoring refinement
- Approval analytics and optimization

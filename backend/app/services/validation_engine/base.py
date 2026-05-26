"""Validation engine runner for Phase 9.

Runs deterministic, read-only checks for a recorded operational event,
persists ValidationIssue rows for any failed rule, and reports the highest
severity status seen.
"""
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.operational_event import OperationalEvent
from app.models.rule_definition import RuleDefinition
from app.models.validation_issue import ValidationIssue
from app.services.rule_engine import RuleResult, get_rules_by_key
from app.services.validation_engine import checks as rule_checks


SEVERITY_ORDER = {"info": 1, "warning": 2, "critical": 3}


# Backwards-compatible placeholders used by Phase 8 code paths.
class IdentityValidator:
    pass


class MissingDataValidator:
    pass


class ScopeValidator:
    pass


class DuplicateValidator:
    pass


class WorkflowStateValidator:
    pass


def run_validation_for_event(db: Session, event: OperationalEvent) -> list[RuleResult]:
    rules = get_rules_by_key(db)
    enabled = {key: rule for key, rule in rules.items() if rule.is_enabled}
    if not enabled:
        return []

    new_state = event.new_state_json or {}
    metadata = event.metadata_json or {}
    results: list[RuleResult] = []

    if event.entity_type == "shipment":
        results.extend(rule_checks.run_shipment_checks(db, event, new_state, enabled))
    elif event.entity_type == "task":
        results.extend(rule_checks.run_task_checks(event, new_state, enabled))
    elif event.entity_type == "charge":
        results.extend(rule_checks.run_charge_checks(event, new_state, enabled))
    elif event.entity_type == "document":
        results.extend(rule_checks.run_document_checks(event, new_state, enabled))
    elif event.entity_type == "bl_management":
        results.extend(rule_checks.run_bl_checks(event, new_state, enabled))
    elif event.entity_type == "email_suggestion":
        results.extend(rule_checks.run_email_suggestion_checks(event, new_state, metadata, enabled))
    elif event.entity_type == "user":
        results.extend(rule_checks.run_user_checks(event, new_state, enabled))

    # Apply rule severity overrides where the rule definition wants stricter
    # severity than the check returned.
    for result in results:
        rule = enabled.get(result.rule_key)
        if rule and rule.severity:
            result.severity = rule.severity
    return results


def create_validation_issues_from_results(
    db: Session,
    event: OperationalEvent,
    results: Iterable[RuleResult],
) -> list[ValidationIssue]:
    created: list[ValidationIssue] = []
    for result in results:
        if result.passed:
            continue
        issue = ValidationIssue(
            event_id=event.id,
            rule_key=result.rule_key,
            entity_type=result.entity_type or event.entity_type,
            entity_id=result.entity_id or event.entity_id,
            entity_label=event.entity_label,
            shipment_id=event.shipment_id,
            severity=result.severity,
            status="open",
            message=result.message,
            recommended_action=result.recommended_action,
            metadata_json=result.metadata or None,
            created_at=datetime.utcnow(),
        )
        db.add(issue)
        created.append(issue)
    if created:
        db.flush()
    return created


def summarize_validation_status(results: Iterable[RuleResult]) -> str:
    failed = [result for result in results if not result.passed]
    if not failed:
        return "passed"
    severity = max(
        (SEVERITY_ORDER.get(result.severity, 0) for result in failed),
        default=0,
    )
    if severity >= SEVERITY_ORDER["critical"]:
        return "manual_review_required"
    if severity >= SEVERITY_ORDER["warning"]:
        return "warning"
    return "warning" if failed else "passed"


def list_enabled_rules(db: Session) -> list[RuleDefinition]:
    return [rule for rule in db.query(RuleDefinition).all() if rule.is_enabled]


def critical_severity_seen(results: Iterable[RuleResult]) -> bool:
    return any(not result.passed and result.severity == "critical" for result in results)


def first_failed_with_severity(
    results: Iterable[RuleResult], severity: str
) -> Optional[RuleResult]:
    for result in results:
        if not result.passed and result.severity == severity:
            return result
    return None

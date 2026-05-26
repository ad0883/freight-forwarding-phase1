from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.schemas.validation import ValidationIssueRead
from app.services.audit_service import record_audit_log
from app.services.validation_issue_service import (
    acknowledge_issue,
    dismiss_issue,
    list_validation_issues,
    resolve_issue,
)


router = APIRouter(prefix="/validation-issues", tags=["validation-issues"])

OperationalUser = Depends(require_roles("ADMIN", "STAFF"))


@router.get("", response_model=list[ValidationIssueRead])
def list_issues(
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = None,
    rule_key: Optional[str] = None,
    entity_type: Optional[str] = None,
    shipment_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: AuthenticatedUser = OperationalUser,
) -> list[ValidationIssueRead]:
    issues = list_validation_issues(
        db,
        status_filter=status,
        severity=severity,
        rule_key=rule_key,
        entity_type=entity_type,
        shipment_id=shipment_id,
        date_from=datetime.combine(date_from, time.min) if date_from else None,
        date_to=datetime.combine(date_to, time.max) if date_to else None,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [ValidationIssueRead.model_validate(issue) for issue in issues]


@router.get("/{issue_id}", response_model=ValidationIssueRead)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = OperationalUser,
) -> ValidationIssueRead:
    from app.services.validation_issue_service import get_validation_issue

    issue = get_validation_issue(db, issue_id)
    return ValidationIssueRead.model_validate(issue)


@router.patch("/{issue_id}/acknowledge", response_model=ValidationIssueRead)
def acknowledge(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ValidationIssueRead:
    issue = acknowledge_issue(db, issue_id, current_user)
    record_audit_log(
        db,
        current_user,
        "validation_issue.acknowledge",
        "validation_issue",
        entity_id=issue.id,
        entity_label=issue.rule_key,
        description="Validation issue acknowledged.",
        metadata={"rule_key": issue.rule_key, "severity": issue.severity},
        request=request,
    )
    return ValidationIssueRead.model_validate(issue)


@router.patch("/{issue_id}/resolve", response_model=ValidationIssueRead)
def resolve(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ValidationIssueRead:
    issue = resolve_issue(db, issue_id, current_user)
    record_audit_log(
        db,
        current_user,
        "validation_issue.resolve",
        "validation_issue",
        entity_id=issue.id,
        entity_label=issue.rule_key,
        description="Validation issue resolved.",
        metadata={"rule_key": issue.rule_key, "severity": issue.severity},
        request=request,
    )
    return ValidationIssueRead.model_validate(issue)


@router.patch("/{issue_id}/dismiss", response_model=ValidationIssueRead)
def dismiss(
    issue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = OperationalUser,
) -> ValidationIssueRead:
    issue = dismiss_issue(db, issue_id, current_user)
    record_audit_log(
        db,
        current_user,
        "validation_issue.dismiss",
        "validation_issue",
        entity_id=issue.id,
        entity_label=issue.rule_key,
        description="Validation issue dismissed.",
        metadata={"rule_key": issue.rule_key, "severity": issue.severity},
        request=request,
    )
    return ValidationIssueRead.model_validate(issue)

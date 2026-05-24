from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.charge import Charge
from app.models.party import Party
from app.models.shipment import Shipment
from app.models.task import Task
from app.services.audit_service import record_audit_log


router = APIRouter(prefix="/admin", tags=["admin-tools"])

TEST_MARKERS = [
    "Codex Test",
    "Phase2 Test",
    "Phase3 Test",
    "INV-TEST",
    "TEST123",
    "Test Exporter",
]


@router.post("/cleanup-test-data")
def cleanup_test_data(
    request: Request,
    dry_run: bool = True,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> dict[str, Any]:
    candidates = _cleanup_candidates(db)
    result = {
        "dry_run": True,
        "requested_dry_run": dry_run,
        "message": "Cleanup is dry-run only. No records were modified.",
        "candidates": candidates,
        "total_candidates": sum(item["count"] for item in candidates.values()),
    }
    record_audit_log(
        db,
        current_user,
        "admin.cleanup_test_data_dry_run",
        "admin_tool",
        description="Admin ran dry-run test data cleanup.",
        metadata={
            "requested_dry_run": dry_run,
            "total_candidates": result["total_candidates"],
            "candidate_counts": {key: value["count"] for key, value in candidates.items()},
        },
        request=request,
    )
    return result


def _cleanup_candidates(db: Session) -> dict[str, dict[str, Any]]:
    return {
        "shipments": _candidate_summary(
            db.query(Shipment)
            .filter(
                or_(
                    *_ilike_any(Shipment.shipment_code),
                    *_ilike_any(Shipment.booking_ref),
                    *_ilike_any(Shipment.bl_number),
                    *_ilike_any(Shipment.commodity),
                )
            )
            .order_by(Shipment.created_at.desc())
            .all(),
            "shipment_code",
        ),
        "parties": _candidate_summary(
            db.query(Party)
            .filter(or_(*_ilike_any(Party.name), *_ilike_any(Party.email), *_ilike_any(Party.contact_person)))
            .order_by(Party.created_at.desc())
            .all(),
            "name",
        ),
        "charges": _candidate_summary(
            db.query(Charge)
            .filter(or_(*_ilike_any(Charge.invoice_no), *_ilike_any(Charge.notes)))
            .order_by(Charge.created_at.desc())
            .all(),
            "invoice_no",
        ),
        "tasks": _candidate_summary(
            db.query(Task)
            .filter(or_(*_ilike_any(Task.title), *_ilike_any(Task.description)))
            .order_by(Task.created_at.desc())
            .all(),
            "title",
        ),
    }


def _ilike_any(column):
    return [column.ilike(f"%{marker}%") for marker in TEST_MARKERS]


def _candidate_summary(records, label_attr: str) -> dict[str, Any]:
    return {
        "count": len(records),
        "sample": [
            {
                "id": record.id,
                "label": getattr(record, label_attr, None) or f"{record.__class__.__name__} #{record.id}",
            }
            for record in records[:20]
        ],
    }

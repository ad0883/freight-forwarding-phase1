"""Phase 19 CHA/customs coordination service."""
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.customs import (
    CustomsActivityLog, CustomsCase, CustomsCaseMilestone,
    CustomsChecklistItem, CustomsDocumentRequirement, CustomsDutyRecord,
    CustomsPartyAssignment, CustomsQuery, CustomsQueryComment,
    CustomsReferenceNumber,
)

logger = logging.getLogger(__name__)


def _gen_case_number() -> str:
    return f"CUS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


# --- Cases ---

def create_customs_case(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> CustomsCase:
    now = datetime.utcnow()
    case = CustomsCase(
        shipment_id=data["shipment_id"], case_number=_gen_case_number(),
        customs_direction=data.get("customs_direction", "export"),
        case_type=data.get("case_type", "shipping_bill"),
        status="not_started", priority=data.get("priority", "p3"),
        port_of_filing=data.get("port_of_filing"),
        customs_location=data.get("customs_location"),
        filing_mode=data.get("filing_mode"),
        created_by_user_id=user.id, created_by_name=user.name,
        created_at=now, updated_at=now,
    )
    db.add(case)
    db.flush()
    _seed_milestones(db, case)
    _seed_document_requirements(db, case)
    db.commit()
    db.refresh(case)
    return case


def get_customs_case(db: Session, case_id: int) -> Optional[CustomsCase]:
    return db.query(CustomsCase).filter(CustomsCase.id == case_id).first()


def list_customs_cases(db: Session, *, shipment_id: Optional[int] = None, status_filter: Optional[str] = None, direction: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[CustomsCase]:
    q = db.query(CustomsCase)
    if shipment_id: q = q.filter(CustomsCase.shipment_id == shipment_id)
    if status_filter: q = q.filter(CustomsCase.status == status_filter)
    if direction: q = q.filter(CustomsCase.customs_direction == direction)
    return q.order_by(CustomsCase.created_at.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0)).all()


def update_customs_status(db: Session, case_id: int, status: str, user: AuthenticatedUser, notes: Optional[str] = None) -> CustomsCase:
    case = get_customs_case(db, case_id)
    if not case: raise ValueError("Customs case not found")
    now = datetime.utcnow()
    case.status = status
    case.updated_at = now
    if status == "cleared": case.cleared_at = now
    if status == "ooc_received": case.ooc_at = now
    if status == "leo_received": case.leo_at = now
    if status == "filed": case.filed_at = now
    _log_activity(db, case, f"status_change_to_{status}", f"Status changed to {status}" + (f": {notes}" if notes else ""), user)
    db.commit()
    db.refresh(case)
    return case


def assign_cha(db: Session, case_id: int, cha_party_id: int, user: AuthenticatedUser) -> CustomsCase:
    case = get_customs_case(db, case_id)
    if not case: raise ValueError("Customs case not found")
    from app.models.party import Party
    party = db.query(Party).filter(Party.id == cha_party_id).first()
    case.cha_party_id = cha_party_id
    case.cha_name = party.name if party else None
    case.updated_at = datetime.utcnow()
    assignment = CustomsPartyAssignment(
        customs_case_id=case.id, party_id=cha_party_id, party_role="cha",
        assigned_at=datetime.utcnow(), assigned_by_user_id=user.id, assigned_by_name=user.name, status="active",
    )
    db.add(assignment)
    _log_activity(db, case, "cha_assigned", f"CHA assigned: {case.cha_name}", user)
    db.commit()
    db.refresh(case)
    return case


def close_customs_case(db: Session, case_id: int, user: AuthenticatedUser, notes: Optional[str] = None) -> CustomsCase:
    return update_customs_status(db, case_id, "closed", user, notes)


# --- Milestones ---

def _seed_milestones(db: Session, case: CustomsCase) -> None:
    milestones = {
        "export": ["documents_received", "cha_assigned", "shipping_bill_draft_prepared", "shipping_bill_filed", "leo_received", "customs_closed"],
        "import": ["pre_alert_received", "cha_assigned", "boe_draft_prepared", "boe_filed", "assessment_completed", "duty_paid", "ooc_received", "customs_closed"],
    }
    for key in milestones.get(case.customs_direction, milestones["export"]):
        db.add(CustomsCaseMilestone(customs_case_id=case.id, milestone_key=key, title=key.replace("_", " ").title(), status="pending", created_at=datetime.utcnow(), updated_at=datetime.utcnow()))


def complete_milestone(db: Session, milestone_id: int, user: AuthenticatedUser) -> CustomsCaseMilestone:
    m = db.query(CustomsCaseMilestone).filter(CustomsCaseMilestone.id == milestone_id).first()
    if not m: raise ValueError("Milestone not found")
    m.status = "completed"
    m.completed_at = datetime.utcnow()
    m.completed_by_user_id = user.id
    m.completed_by_name = user.name
    m.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(m)
    return m


# --- Checklist ---

def complete_checklist_item(db: Session, item_id: int, user: AuthenticatedUser) -> CustomsChecklistItem:
    item = db.query(CustomsChecklistItem).filter(CustomsChecklistItem.id == item_id).first()
    if not item: raise ValueError("Checklist item not found")
    item.status = "completed"
    item.completed_at = datetime.utcnow()
    item.completed_by_user_id = user.id
    item.completed_by_name = user.name
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


def waive_checklist_item(db: Session, item_id: int, user: AuthenticatedUser, reason: str) -> CustomsChecklistItem:
    item = db.query(CustomsChecklistItem).filter(CustomsChecklistItem.id == item_id).first()
    if not item: raise ValueError("Checklist item not found")
    item.status = "waived"
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


# --- Document Requirements ---

def _seed_document_requirements(db: Session, case: CustomsCase) -> None:
    docs = {
        "export": ["commercial_invoice", "packing_list", "bl_awb", "shipping_bill", "iec", "gst_certificate", "ad_code"],
        "import": ["commercial_invoice", "packing_list", "bl_awb", "bill_of_entry", "iec", "gst_certificate", "insurance"],
    }
    for doc_type in docs.get(case.customs_direction, docs["export"]):
        db.add(CustomsDocumentRequirement(customs_case_id=case.id, document_type=doc_type, required=True, status="pending", visible_to_customer=True, visible_to_cha=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))


# --- Queries ---

def create_customs_query(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> CustomsQuery:
    q = CustomsQuery(
        customs_case_id=data["customs_case_id"], shipment_id=data.get("shipment_id"),
        query_type=data.get("query_type", "other"), source=data.get("source", "customs_query"),
        status="open", severity=data.get("severity", "medium"),
        title=data["title"], description=data.get("description"),
        raised_by=user.name, raised_at=datetime.utcnow(),
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def resolve_customs_query(db: Session, query_id: int, user: AuthenticatedUser, notes: Optional[str] = None) -> CustomsQuery:
    q = db.query(CustomsQuery).filter(CustomsQuery.id == query_id).first()
    if not q: raise ValueError("Query not found")
    q.status = "resolved"
    q.resolved_at = datetime.utcnow()
    q.resolved_by_user_id = user.id
    q.resolved_by_name = user.name
    q.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(q)
    return q


def add_query_comment(db: Session, query_id: int, text: str, user: AuthenticatedUser, visible_to_customer: bool = False) -> CustomsQueryComment:
    c = CustomsQueryComment(customs_query_id=query_id, author_type="internal_user", author_user_id=user.id, author_name=user.name, comment_text=text, visible_to_customer=visible_to_customer, visible_to_cha=True, created_at=datetime.utcnow())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# --- References ---

def add_reference(db: Session, case_id: int, data: dict[str, Any], user: AuthenticatedUser) -> CustomsReferenceNumber:
    ref = CustomsReferenceNumber(customs_case_id=case_id, reference_type=data["reference_type"], reference_value=data["reference_value"], source=data.get("source", "manual"), verified=False, created_at=datetime.utcnow())
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def verify_reference(db: Session, ref_id: int, user: AuthenticatedUser) -> CustomsReferenceNumber:
    ref = db.query(CustomsReferenceNumber).filter(CustomsReferenceNumber.id == ref_id).first()
    if not ref: raise ValueError("Reference not found")
    ref.verified = True
    ref.verified_by_user_id = user.id
    ref.verified_by_name = user.name
    db.commit()
    db.refresh(ref)
    return ref


# --- Duties ---

def create_duty_record(db: Session, case_id: int, data: dict[str, Any], user: AuthenticatedUser) -> CustomsDutyRecord:
    d = CustomsDutyRecord(
        customs_case_id=case_id, shipment_id=data.get("shipment_id"),
        duty_type=data.get("duty_type", "basic_customs_duty"),
        currency=data.get("currency", "INR"),
        assessed_amount=data.get("assessed_amount"), paid_amount=data.get("paid_amount"),
        outstanding_amount=data.get("outstanding_amount"),
        payment_status=data.get("payment_status", "pending"),
        payment_reference=data.get("payment_reference"),
        recorded_by_user_id=user.id, recorded_by_name=user.name,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


# --- Summary ---

def get_customs_summary(db: Session) -> dict[str, Any]:
    active = db.query(CustomsCase).filter(CustomsCase.status.notin_(["closed", "cancelled"])).all()
    open_queries = db.query(CustomsQuery).filter(CustomsQuery.status == "open").count()
    return {
        "total_active": len(active),
        "documents_pending": sum(1 for c in active if c.status == "documents_pending"),
        "ooc_pending": sum(1 for c in active if c.customs_direction == "import" and not c.ooc_at),
        "leo_pending": sum(1 for c in active if c.customs_direction == "export" and not c.leo_at),
        "queries_open": open_queries,
        "filed": sum(1 for c in active if c.status == "filed"),
    }


# --- Activity Log ---

def _log_activity(db: Session, case: CustomsCase, activity_type: str, summary: str, user: Optional[AuthenticatedUser] = None) -> None:
    db.add(CustomsActivityLog(customs_case_id=case.id, shipment_id=case.shipment_id, activity_type=activity_type, safe_summary=summary, created_by_user_id=user.id if user else None, created_by_name=user.name if user else None, created_at=datetime.utcnow()))

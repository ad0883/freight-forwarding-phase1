"""Phase 19 CHA/customs coordination API routes."""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.models.customs import (
    CustomsCase, CustomsCaseMilestone, CustomsChecklistItem,
    CustomsDocumentRequirement, CustomsDutyRecord, CustomsQuery,
    CustomsQueryComment, CustomsReferenceNumber,
)
from app.services.audit_service import record_audit_log
from app.services.customs_service import (
    add_query_comment, add_reference, assign_cha, close_customs_case,
    complete_checklist_item, complete_milestone, create_customs_case,
    create_customs_query, create_duty_record, get_customs_case,
    get_customs_summary, list_customs_cases, resolve_customs_query,
    update_customs_status, verify_reference, waive_checklist_item,
)

router = APIRouter(prefix="/customs", tags=["customs"])
shipment_customs_router = APIRouter(prefix="/shipments", tags=["shipment-customs"])

AnyUser = Depends(require_roles("ADMIN", "STAFF", "VIEW_ONLY"))
OperationalUser = Depends(require_roles("ADMIN", "STAFF"))
AdminUser = Depends(require_roles("ADMIN"))


# --- Schemas ---
class CustomsCaseRead(BaseModel):
    id: int; shipment_id: int; case_number: str; customs_direction: str
    case_type: str; status: str; priority: str
    cha_party_id: Optional[int] = None; cha_name: Optional[str] = None
    port_of_filing: Optional[str] = None; filed_at: Optional[datetime] = None
    ooc_at: Optional[datetime] = None; leo_at: Optional[datetime] = None
    cleared_at: Optional[datetime] = None; created_at: datetime
    class Config:
        from_attributes = True

class CustomsCaseCreate(BaseModel):
    shipment_id: int
    customs_direction: str = "export"
    case_type: str = "shipping_bill"
    priority: str = "p3"
    port_of_filing: Optional[str] = None
    customs_location: Optional[str] = None

class MilestoneRead(BaseModel):
    id: int; customs_case_id: int; milestone_key: str; title: str
    status: str; completed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class ChecklistRead(BaseModel):
    id: int; customs_case_id: int; item_key: str; title: str
    status: str; required: bool; blocking: bool
    completed_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class DocReqRead(BaseModel):
    id: int; customs_case_id: int; document_type: str; required: bool
    status: str; visible_to_customer: bool
    class Config:
        from_attributes = True

class QueryRead(BaseModel):
    id: int; customs_case_id: int; query_type: str; status: str
    severity: str; title: str; created_at: datetime
    resolved_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class QueryCreate(BaseModel):
    customs_case_id: int
    query_type: str = "other"
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    severity: str = "medium"

class RefRead(BaseModel):
    id: int; customs_case_id: int; reference_type: str
    reference_value: str; verified: bool; created_at: datetime
    class Config:
        from_attributes = True

class RefCreate(BaseModel):
    reference_type: str
    reference_value: str

class DutyRead(BaseModel):
    id: int; customs_case_id: int; duty_type: str; currency: str
    assessed_amount: Optional[Any] = None; paid_amount: Optional[Any] = None
    payment_status: str; payment_reference: Optional[str] = None
    class Config:
        from_attributes = True

class DutyCreate(BaseModel):
    duty_type: str = "basic_customs_duty"
    currency: str = "INR"
    assessed_amount: Optional[float] = None
    payment_status: str = "pending"


# --- Summary ---
@router.get("/summary")
def customs_summary(db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return get_customs_summary(db)

# --- List / Create ---
@router.get("", response_model=list[CustomsCaseRead])
def list_cases(shipment_id: Optional[int] = None, status: Optional[str] = None, direction: Optional[str] = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [CustomsCaseRead.model_validate(c) for c in list_customs_cases(db, shipment_id=shipment_id, status_filter=status, direction=direction, limit=limit, offset=offset)]

@router.post("", response_model=CustomsCaseRead, status_code=201)
def create_case(body: CustomsCaseCreate, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    case = create_customs_case(db, body.model_dump(), current_user)
    record_audit_log(db, current_user, "customs.create", "customs_case", entity_id=case.id, entity_label=case.case_number, description=f"Customs case created for shipment {case.shipment_id}", request=request)
    return CustomsCaseRead.model_validate(case)

# --- Queries (before {case_id}) ---
@router.get("/queries", response_model=list[QueryRead])
def list_all_queries(status: Optional[str] = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    q = db.query(CustomsQuery)
    if status: q = q.filter(CustomsQuery.status == status)
    return [QueryRead.model_validate(x) for x in q.order_by(CustomsQuery.created_at.desc()).limit(limit).all()]

@router.post("/queries", response_model=QueryRead, status_code=201)
def create_query(body: QueryCreate, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    q = create_customs_query(db, body.model_dump(), current_user)
    record_audit_log(db, current_user, "customs.query_create", "customs_query", entity_id=q.id, description=f"Customs query: {q.title[:100]}", request=request)
    return QueryRead.model_validate(q)

@router.get("/queries/{query_id}", response_model=QueryRead)
def get_query(query_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    q = db.query(CustomsQuery).filter(CustomsQuery.id == query_id).first()
    if not q: raise HTTPException(404, "Query not found")
    return QueryRead.model_validate(q)

@router.post("/queries/{query_id}/comments", status_code=201)
def query_comment(query_id: int, comment_text: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    c = add_query_comment(db, query_id, comment_text, current_user)
    return {"id": c.id, "status": "created"}

@router.post("/queries/{query_id}/resolve")
def query_resolve(query_id: int, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: q = resolve_customs_query(db, query_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "customs.query_resolve", "customs_query", entity_id=q.id, description="Customs query resolved.", request=request)
    return QueryRead.model_validate(q)

# --- Detail ---
@router.get("/{case_id}", response_model=CustomsCaseRead)
def get_case(case_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    c = get_customs_case(db, case_id)
    if not c: raise HTTPException(404, "Customs case not found")
    return CustomsCaseRead.model_validate(c)

@router.post("/{case_id}/assign-cha")
def assign_cha_route(case_id: int, cha_party_id: int = Query(...), request: Request = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: case = assign_cha(db, case_id, cha_party_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "customs.assign_cha", "customs_case", entity_id=case.id, description=f"CHA assigned: {case.cha_name}", request=request)
    return CustomsCaseRead.model_validate(case)

@router.post("/{case_id}/status")
def update_status(case_id: int, status: str = Query(...), notes: Optional[str] = None, request: Request = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: case = update_customs_status(db, case_id, status, current_user, notes)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "customs.status_update", "customs_case", entity_id=case.id, description=f"Status: {status}", request=request)
    return CustomsCaseRead.model_validate(case)

@router.post("/{case_id}/close")
def close_case(case_id: int, notes: Optional[str] = None, request: Request = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: case = close_customs_case(db, case_id, current_user, notes)
    except ValueError as e: raise HTTPException(400, str(e))
    record_audit_log(db, current_user, "customs.close", "customs_case", entity_id=case.id, description="Customs case closed.", request=request)
    return CustomsCaseRead.model_validate(case)

# --- Milestones ---
@router.get("/{case_id}/milestones", response_model=list[MilestoneRead])
def list_milestones(case_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [MilestoneRead.model_validate(m) for m in db.query(CustomsCaseMilestone).filter(CustomsCaseMilestone.customs_case_id == case_id).order_by(CustomsCaseMilestone.id).all()]

@router.patch("/milestones/{milestone_id}", response_model=MilestoneRead)
def milestone_complete(milestone_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: m = complete_milestone(db, milestone_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    return MilestoneRead.model_validate(m)

# --- Checklist ---
@router.get("/{case_id}/checklist", response_model=list[ChecklistRead])
def list_checklist(case_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [ChecklistRead.model_validate(i) for i in db.query(CustomsChecklistItem).filter(CustomsChecklistItem.customs_case_id == case_id).order_by(CustomsChecklistItem.id).all()]

@router.post("/checklist/{item_id}/complete", response_model=ChecklistRead)
def checklist_complete(item_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: i = complete_checklist_item(db, item_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    return ChecklistRead.model_validate(i)

@router.post("/checklist/{item_id}/waive", response_model=ChecklistRead)
def checklist_waive(item_id: int, reason: str = Query(...), db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    try: i = waive_checklist_item(db, item_id, current_user, reason)
    except ValueError as e: raise HTTPException(400, str(e))
    return ChecklistRead.model_validate(i)

# --- Documents ---
@router.get("/{case_id}/documents", response_model=list[DocReqRead])
def list_doc_reqs(case_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [DocReqRead.model_validate(d) for d in db.query(CustomsDocumentRequirement).filter(CustomsDocumentRequirement.customs_case_id == case_id).order_by(CustomsDocumentRequirement.id).all()]

# --- References ---
@router.get("/{case_id}/references", response_model=list[RefRead])
def list_refs(case_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [RefRead.model_validate(r) for r in db.query(CustomsReferenceNumber).filter(CustomsReferenceNumber.customs_case_id == case_id).order_by(CustomsReferenceNumber.id).all()]

@router.post("/{case_id}/references", response_model=RefRead, status_code=201)
def create_ref(case_id: int, body: RefCreate, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    ref = add_reference(db, case_id, body.model_dump(), current_user)
    return RefRead.model_validate(ref)

@router.post("/references/{reference_id}/verify", response_model=RefRead)
def verify_ref(reference_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    try: ref = verify_reference(db, reference_id, current_user)
    except ValueError as e: raise HTTPException(400, str(e))
    return RefRead.model_validate(ref)

# --- Duties ---
@router.get("/{case_id}/duties", response_model=list[DutyRead])
def list_duties(case_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [DutyRead.model_validate(d) for d in db.query(CustomsDutyRecord).filter(CustomsDutyRecord.customs_case_id == case_id).order_by(CustomsDutyRecord.id).all()]

@router.post("/{case_id}/duties", response_model=DutyRead, status_code=201)
def create_duty(case_id: int, body: DutyCreate, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    d = create_duty_record(db, case_id, body.model_dump(), current_user)
    return DutyRead.model_validate(d)

# --- Shipment-specific ---
@shipment_customs_router.get("/{shipment_id}/customs", response_model=list[CustomsCaseRead])
def shipment_customs(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    return [CustomsCaseRead.model_validate(c) for c in list_customs_cases(db, shipment_id=shipment_id)]

@shipment_customs_router.post("/{shipment_id}/customs", response_model=CustomsCaseRead, status_code=201)
def shipment_create_customs(shipment_id: int, body: CustomsCaseCreate, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = OperationalUser):
    data = body.model_dump()
    data["shipment_id"] = shipment_id
    case = create_customs_case(db, data, current_user)
    return CustomsCaseRead.model_validate(case)

@shipment_customs_router.get("/{shipment_id}/customs-summary")
def shipment_customs_summary(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = AnyUser):
    cases = list_customs_cases(db, shipment_id=shipment_id)
    return {"shipment_id": shipment_id, "total_cases": len(cases), "cases": [{"id": c.id, "case_number": c.case_number, "direction": c.customs_direction, "status": c.status, "ooc_at": c.ooc_at.isoformat() if c.ooc_at else None, "leo_at": c.leo_at.isoformat() if c.leo_at else None} for c in cases]}

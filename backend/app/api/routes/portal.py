"""Phase 18 exporter/importer portal API routes."""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, get_current_user, require_roles
from app.models.portal import (
    PortalAccount, PortalNotification, PortalRequest, PortalRequestComment,
    PortalShipmentAccess,
)
from app.services.audit_service import record_audit_log
from app.services.portal_service import (
    add_portal_comment, check_shipment_access, create_portal_account,
    create_portal_request, get_allowed_shipment_ids, get_portal_account,
    get_portal_shipment_detail, grant_shipment_access, list_portal_notifications,
    list_portal_requests, list_portal_shipments, mark_notification_read,
    revoke_shipment_access,
)

router = APIRouter(prefix="/portal", tags=["portal"])
admin_portal_router = APIRouter(prefix="/admin/portal", tags=["admin-portal"])

AdminUser = Depends(require_roles("ADMIN"))


# --- Schemas ---
class PortalAccountRead(BaseModel):
    id: int; email: str; full_name: str; account_type: str; status: str
    party_id: Optional[int] = None; company_name: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class PortalShipmentRead(BaseModel):
    id: int; shipment_code: Optional[str] = None; type: Optional[str] = None
    status: Optional[str] = None; workflow_state: Optional[str] = None
    origin_port: Optional[str] = None; destination_port: Optional[str] = None
    etd: Optional[str] = None; eta: Optional[str] = None
    shipping_line: Optional[str] = None; created_at: Optional[str] = None
    can_view_documents: Optional[bool] = None; can_upload_documents: Optional[bool] = None
    can_view_finance: Optional[bool] = None; can_raise_requests: Optional[bool] = None

class PortalRequestRead(BaseModel):
    id: int; request_number: str; shipment_id: Optional[int] = None
    request_type: str; title: str; description: Optional[str] = None
    status: str; priority: str; created_at: datetime
    resolved_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class PortalRequestCreate(BaseModel):
    shipment_id: Optional[int] = None
    request_type: str = "other"
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None

class PortalCommentCreate(BaseModel):
    comment_text: str = Field(min_length=1, max_length=2000)

class PortalCommentRead(BaseModel):
    id: int; author_type: str; author_name: Optional[str] = None
    comment_text: str; visible_to_customer: bool; created_at: datetime
    class Config:
        from_attributes = True

class PortalNotificationRead(BaseModel):
    id: int; title: str; message: Optional[str] = None
    notification_type: str; status: str; created_at: datetime
    read_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class AdminPortalAccountCreate(BaseModel):
    email: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    account_type: str = "exporter"
    party_id: Optional[int] = None
    company_name: Optional[str] = None

class AdminGrantAccess(BaseModel):
    shipment_id: int
    access_level: str = "view_only"
    can_view_documents: bool = True
    can_upload_documents: bool = False
    can_view_finance: bool = False
    can_raise_requests: bool = True


# --- Portal dependency ---
def get_portal_user(db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(status_code=403, detail="No portal account found")
    return acct


# --- Portal Routes ---

@router.get("/me", response_model=PortalAccountRead)
def portal_me(db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(404, "No portal account")
    return PortalAccountRead.model_validate(acct)


@router.get("/dashboard")
def portal_dashboard(db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    shipment_ids = get_allowed_shipment_ids(db, acct)
    requests = db.query(PortalRequest).filter(PortalRequest.portal_account_id == acct.id, PortalRequest.status.in_(["open", "acknowledged", "in_review"])).count()
    notifications = db.query(PortalNotification).filter(PortalNotification.portal_account_id == acct.id, PortalNotification.status == "unread").count()
    return {"active_shipments": len(shipment_ids), "open_requests": requests, "unread_notifications": notifications}


@router.get("/shipments")
def portal_shipments(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    return list_portal_shipments(db, acct, limit=limit)


@router.get("/shipments/{shipment_id}")
def portal_shipment_detail(shipment_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    detail = get_portal_shipment_detail(db, acct, shipment_id)
    if not detail:
        raise HTTPException(404, "Shipment not found or access denied")
    return detail


@router.get("/requests", response_model=list[PortalRequestRead])
def portal_requests_list(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    return [PortalRequestRead.model_validate(r) for r in list_portal_requests(db, acct, limit=limit)]


@router.post("/shipments/{shipment_id}/requests", response_model=PortalRequestRead, status_code=201)
def portal_create_request(shipment_id: int, body: PortalRequestCreate, db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    access = check_shipment_access(db, acct, shipment_id)
    if not access or not access.can_raise_requests:
        raise HTTPException(403, "Cannot raise requests for this shipment")
    data = body.model_dump()
    data["shipment_id"] = shipment_id
    req = create_portal_request(db, acct, data)
    return PortalRequestRead.model_validate(req)


@router.post("/requests/{request_id}/comments", response_model=PortalCommentRead, status_code=201)
def portal_add_comment(request_id: int, body: PortalCommentCreate, db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    req = db.query(PortalRequest).filter(PortalRequest.id == request_id, PortalRequest.portal_account_id == acct.id).first()
    if not req:
        raise HTTPException(404, "Request not found")
    comment = add_portal_comment(db, acct, request_id, body.comment_text)
    return PortalCommentRead.model_validate(comment)


@router.get("/requests/{request_id}/comments", response_model=list[PortalCommentRead])
def portal_list_comments(request_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    comments = db.query(PortalRequestComment).filter(PortalRequestComment.portal_request_id == request_id, PortalRequestComment.visible_to_customer.is_(True)).order_by(PortalRequestComment.created_at.asc()).all()
    return [PortalCommentRead.model_validate(c) for c in comments]


@router.get("/notifications", response_model=list[PortalNotificationRead])
def portal_notifications(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    return [PortalNotificationRead.model_validate(n) for n in list_portal_notifications(db, acct, limit=limit)]


@router.patch("/notifications/{notification_id}/read")
def portal_mark_read(notification_id: int, db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)):
    acct = get_portal_account(db, current_user.id)
    if not acct:
        raise HTTPException(403, "No portal account")
    n = mark_notification_read(db, notification_id, acct)
    if not n:
        raise HTTPException(404, "Notification not found")
    return {"status": "read"}


# --- Admin Portal Management ---

@admin_portal_router.get("/accounts", response_model=list[PortalAccountRead])
def admin_list_accounts(db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    accounts = db.query(PortalAccount).order_by(PortalAccount.created_at.desc()).limit(100).all()
    return [PortalAccountRead.model_validate(a) for a in accounts]


@admin_portal_router.post("/accounts", response_model=PortalAccountRead, status_code=201)
def admin_create_account(body: AdminPortalAccountCreate, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    acct = create_portal_account(db, body.model_dump(), current_user)
    record_audit_log(db, current_user, "portal.account_create", "portal_account", entity_id=acct.id, entity_label=acct.email, description=f"Portal account created: {acct.full_name}", request=request)
    return PortalAccountRead.model_validate(acct)


@admin_portal_router.post("/accounts/{portal_account_id}/grant-shipment-access", status_code=201)
def admin_grant_access(portal_account_id: int, body: AdminGrantAccess, request: Request, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    access = grant_shipment_access(db, portal_account_id, body.shipment_id, current_user, **body.model_dump(exclude={"shipment_id"}))
    record_audit_log(db, current_user, "portal.grant_access", "portal_shipment_access", entity_id=access.id, description=f"Shipment access granted to portal account {portal_account_id}", request=request)
    return {"id": access.id, "status": "granted"}


@admin_portal_router.post("/accounts/{portal_account_id}/revoke-shipment-access")
def admin_revoke_access(portal_account_id: int, shipment_id: int = Query(...), request: Request = None, db: Session = Depends(get_db), current_user: AuthenticatedUser = AdminUser):
    revoked = revoke_shipment_access(db, portal_account_id, shipment_id)
    if revoked:
        record_audit_log(db, current_user, "portal.revoke_access", "portal_shipment_access", description=f"Shipment {shipment_id} access revoked from portal account {portal_account_id}", request=request)
    return {"revoked": revoked}

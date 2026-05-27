"""Phase 18 portal access and business logic service."""
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.portal import (
    PortalAccount, PortalActivityLog, PortalDocumentAccess,
    PortalNotification, PortalPartyLink, PortalRequest,
    PortalRequestComment, PortalShipmentAccess,
)

logger = logging.getLogger(__name__)

HIDDEN_FIELDS = {"internal_notes", "margin", "profit", "vendor_payable", "gmail_token", "oauth_code", "bot_governance", "approval_policy", "audit_log"}


def _gen_request_number() -> str:
    return f"PRQ-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


# --- Access Control ---

def get_portal_account(db: Session, user_id: int) -> Optional[PortalAccount]:
    return db.query(PortalAccount).filter(PortalAccount.user_id == user_id, PortalAccount.status == "active").first()


def get_allowed_shipment_ids(db: Session, portal_account: PortalAccount) -> list[int]:
    access = db.query(PortalShipmentAccess.shipment_id).filter(
        PortalShipmentAccess.portal_account_id == portal_account.id,
        PortalShipmentAccess.access_level != "blocked",
    ).all()
    party_access = db.query(PortalShipmentAccess.shipment_id).filter(
        PortalShipmentAccess.party_id == portal_account.party_id,
        PortalShipmentAccess.access_level != "blocked",
    ).all() if portal_account.party_id else []
    ids = set(r[0] for r in access) | set(r[0] for r in party_access)
    return list(ids)


def check_shipment_access(db: Session, portal_account: PortalAccount, shipment_id: int) -> Optional[PortalShipmentAccess]:
    access = db.query(PortalShipmentAccess).filter(
        PortalShipmentAccess.shipment_id == shipment_id,
        PortalShipmentAccess.access_level != "blocked",
    ).filter(
        (PortalShipmentAccess.portal_account_id == portal_account.id) |
        (PortalShipmentAccess.party_id == portal_account.party_id)
    ).first()
    return access


# --- Shipments ---

def list_portal_shipments(db: Session, portal_account: PortalAccount, limit: int = 50) -> list[dict]:
    from app.models.shipment import Shipment
    ids = get_allowed_shipment_ids(db, portal_account)
    if not ids:
        return []
    shipments = db.query(Shipment).filter(Shipment.id.in_(ids), Shipment.is_archived.is_(False)).order_by(Shipment.created_at.desc()).limit(limit).all()
    return [_safe_shipment_summary(s) for s in shipments]


def get_portal_shipment_detail(db: Session, portal_account: PortalAccount, shipment_id: int) -> Optional[dict]:
    access = check_shipment_access(db, portal_account, shipment_id)
    if not access:
        return None
    from app.models.shipment import Shipment
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        return None
    return _safe_shipment_detail(s, access)


def _safe_shipment_summary(s) -> dict:
    return {
        "id": s.id, "shipment_code": s.shipment_code, "type": s.type,
        "status": s.status, "workflow_state": getattr(s, "workflow_state", None),
        "origin_port": s.origin_port, "destination_port": s.destination_port,
        "etd": str(s.etd) if s.etd else None, "eta": str(s.eta) if s.eta else None,
        "shipping_line": s.shipping_line, "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _safe_shipment_detail(s, access) -> dict:
    d = _safe_shipment_summary(s)
    d["can_view_documents"] = access.can_view_documents
    d["can_upload_documents"] = access.can_upload_documents
    d["can_view_finance"] = access.can_view_finance
    d["can_raise_requests"] = access.can_raise_requests
    return d


# --- Requests ---

def create_portal_request(db: Session, portal_account: PortalAccount, data: dict[str, Any]) -> PortalRequest:
    req = PortalRequest(
        request_number=_gen_request_number(),
        portal_account_id=portal_account.id,
        party_id=portal_account.party_id,
        shipment_id=data.get("shipment_id"),
        request_type=data.get("request_type", "other"),
        title=data["title"],
        description=data.get("description"),
        status="open", priority=data.get("priority", "p3"),
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def list_portal_requests(db: Session, portal_account: PortalAccount, limit: int = 50) -> list[PortalRequest]:
    return db.query(PortalRequest).filter(PortalRequest.portal_account_id == portal_account.id).order_by(PortalRequest.created_at.desc()).limit(limit).all()


def add_portal_comment(db: Session, portal_account: PortalAccount, request_id: int, text: str) -> PortalRequestComment:
    comment = PortalRequestComment(
        portal_request_id=request_id, author_type="portal_user",
        author_user_id=portal_account.user_id, author_name=portal_account.full_name,
        comment_text=text, visible_to_customer=True, created_at=datetime.utcnow(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


# --- Notifications ---

def list_portal_notifications(db: Session, portal_account: PortalAccount, limit: int = 50) -> list[PortalNotification]:
    return db.query(PortalNotification).filter(PortalNotification.portal_account_id == portal_account.id).order_by(PortalNotification.created_at.desc()).limit(limit).all()


def mark_notification_read(db: Session, notification_id: int, portal_account: PortalAccount) -> Optional[PortalNotification]:
    n = db.query(PortalNotification).filter(PortalNotification.id == notification_id, PortalNotification.portal_account_id == portal_account.id).first()
    if n:
        n.status = "read"
        n.read_at = datetime.utcnow()
        db.commit()
        db.refresh(n)
    return n


# --- Admin Management ---

def create_portal_account(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> PortalAccount:
    acct = PortalAccount(
        email=data["email"], full_name=data["full_name"],
        account_type=data.get("account_type", "exporter"),
        status="active", party_id=data.get("party_id"),
        company_name=data.get("company_name"),
        created_by_user_id=user.id, created_by_name=user.name,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


def grant_shipment_access(db: Session, portal_account_id: int, shipment_id: int, user: AuthenticatedUser, **kwargs) -> PortalShipmentAccess:
    acct = db.query(PortalAccount).filter(PortalAccount.id == portal_account_id).first()
    access = PortalShipmentAccess(
        portal_account_id=portal_account_id,
        party_id=acct.party_id if acct else None,
        shipment_id=shipment_id,
        access_level=kwargs.get("access_level", "view_only"),
        can_view_documents=kwargs.get("can_view_documents", True),
        can_upload_documents=kwargs.get("can_upload_documents", False),
        can_view_finance=kwargs.get("can_view_finance", False),
        can_raise_requests=kwargs.get("can_raise_requests", True),
        can_comment=kwargs.get("can_comment", True),
        granted_by_user_id=user.id, granted_by_name=user.name,
        created_at=datetime.utcnow(),
    )
    db.add(access)
    db.commit()
    db.refresh(access)
    return access


def revoke_shipment_access(db: Session, portal_account_id: int, shipment_id: int) -> bool:
    deleted = db.query(PortalShipmentAccess).filter(
        PortalShipmentAccess.portal_account_id == portal_account_id,
        PortalShipmentAccess.shipment_id == shipment_id,
    ).delete()
    db.commit()
    return deleted > 0

import hashlib
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bl_management import BLManagement
from app.models.charge import Charge
from app.models.demurrage import Demurrage
from app.models.document import Document
from app.models.email import EmailConnection, EmailMessageCache, EmailSuggestion
from app.models.followup import FollowUpLog
from app.models.shipment import Shipment
from app.models.task import Task
from app.schemas.charge import is_valid_charge_status
from app.services.dashboard_service import invalidate_dashboard_cache
from app.services.email_parser_service import (
    CONFIDENCE_NO_SHIPMENT_THRESHOLD,
    build_suggestions_for_classification,
    is_valid_shipment_code,
    parse_email,
)


logger = logging.getLogger(__name__)


class EmailSuggestionConflict(Exception):
    def __init__(self, conflicts: list[dict[str, Any]]):
        self.conflicts = conflicts


SHIPMENT_UPDATE_FIELDS = {
    "booking_ref",
    "bl_number",
    "container_no",
    "vessel_name",
    "voyage_no",
    "origin_port",
    "dest_port",
    "etd",
    "eta",
    "shipping_line",
    "status",
    "do_received_date",
}

BL_UPDATE_FIELDS = {
    "draft_received",
    "approval_date",
    "final_bl_date",
    "bl_type",
    "surrender_done",
    "telex_release",
}

DEMURRAGE_UPDATE_FIELDS = {"start_date", "free_days"}


def process_cached_message(db: Session, message: EmailMessageCache) -> int:
    parsed = parse_email(
        message.subject,
        message.snippet,
        message.body_preview,
        sender=message.sender,
    )
    message.classification = parsed["classification"]
    extracted_data = parsed["extracted_data"]
    shipment, confidence = match_shipment(db, extracted_data)
    if shipment:
        message.matched_shipment_id = shipment.id
    suggestions = build_suggestions_for_classification(
        message.classification,
        extracted_data,
        message.received_at,
        has_matched_shipment=bool(shipment),
        confidence=confidence,
    )
    if not suggestions:
        if message.classification == "unknown":
            message.processed_status = "ignored"
        elif not shipment and confidence < CONFIDENCE_NO_SHIPMENT_THRESHOLD:
            message.processed_status = "manual_review"
        else:
            message.processed_status = "new"
        db.commit()
        return 0

    created = 0
    for suggestion in suggestions:
        suggestion_data = {**extracted_data, **suggestion["data"]}
        suggestion_shipment = shipment or _shipment_from_code(db, suggestion_data.get("shipment_code"))
        if suggestion_shipment and not message.matched_shipment_id:
            message.matched_shipment_id = suggestion_shipment.id
        extracted_hash = compute_extracted_hash(suggestion_data)
        if _suggestion_exists(
            db,
            email_message_id=message.id,
            suggestion_type=suggestion["suggestion_type"],
            shipment_id=suggestion_shipment.id if suggestion_shipment else None,
            extracted_hash=extracted_hash,
        ):
            continue
        email_suggestion = EmailSuggestion(
            email_message_id=message.id,
            user_id=message.user_id,
            gmail_account_email=message.gmail_account_email,
            shipment_id=suggestion_shipment.id if suggestion_shipment else None,
            suggestion_type=suggestion["suggestion_type"],
            confidence=confidence,
            extracted_data_json=suggestion_data,
            extracted_data_hash=extracted_hash,
            status="pending",
        )
        db.add(email_suggestion)
        created += 1
    message.processed_status = "suggested"
    db.commit()
    return created


def match_shipment(db: Session, extracted_data: dict[str, Any]) -> tuple[Optional[Shipment], float]:
    shipment_code = extracted_data.get("shipment_code")
    if shipment_code and is_valid_shipment_code(shipment_code):
        shipment = _match_shipment_field(db, Shipment.shipment_code, shipment_code)
        if shipment:
            return shipment, 0.9
    for field, confidence in [
        ("booking_ref", 0.7),
        ("container_no", 0.7),
        ("bl_number", 0.7),
    ]:
        value = extracted_data.get(field)
        if value:
            shipment = _match_shipment_field(db, getattr(Shipment, field), value)
            if shipment:
                return shipment, confidence
    if extracted_data:
        return None, 0.5
    return None, 0.3


def patch_suggestion(
    db: Session,
    suggestion: EmailSuggestion,
    shipment_id: Optional[int],
    extracted_data_json: Optional[dict[str, Any]],
) -> EmailSuggestion:
    if shipment_id is not None:
        shipment = db.query(Shipment.id).filter(Shipment.id == shipment_id).first()
        if not shipment:
            raise HTTPException(status_code=400, detail="Shipment does not exist")
        suggestion.shipment_id = shipment_id
    if extracted_data_json is not None:
        suggestion.extracted_data_json = extracted_data_json
        suggestion.extracted_data_hash = compute_extracted_hash(extracted_data_json)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def apply_suggestion(
    db: Session,
    suggestion: EmailSuggestion,
    user_id: int,
    force: bool = False,
) -> EmailSuggestion:
    if suggestion.status == "applied":
        raise HTTPException(status_code=400, detail="Suggestion is already applied")
    if suggestion.status in {"rejected", "ignored", "dismissed"}:
        raise HTTPException(status_code=400, detail="Suggestion is not pending")
    handlers = {
        "update_shipment": _apply_update_shipment,
        "update_document": _apply_update_document,
        "update_bl": _apply_update_bl,
        "update_demurrage": _apply_update_demurrage,
        "create_charge": _apply_create_charge,
        "create_followup": _apply_create_followup,
        "create_task": _apply_create_task,
    }
    handler = handlers.get(suggestion.suggestion_type)
    if not handler:
        raise HTTPException(status_code=400, detail="Unknown suggestion type cannot be applied")
    suggestion.reviewed_by = user_id
    handler(db, suggestion, force)
    suggestion.status = "applied"
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.applied_at = datetime.utcnow()
    suggestion.email_message.processed_status = "approved"
    db.commit()
    db.refresh(suggestion)
    invalidate_dashboard_cache()
    return suggestion


def reject_suggestion(db: Session, suggestion: EmailSuggestion, user_id: int) -> EmailSuggestion:
    suggestion.status = "rejected"
    suggestion.reviewed_by = user_id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.email_message.processed_status = "rejected"
    db.commit()
    db.refresh(suggestion)
    return suggestion


def dismiss_suggestion(db: Session, suggestion: EmailSuggestion, user_id: int) -> EmailSuggestion:
    suggestion.status = "dismissed"
    suggestion.reviewed_by = user_id
    suggestion.reviewed_at = datetime.utcnow()
    if suggestion.email_message.processed_status == "suggested":
        suggestion.email_message.processed_status = "ignored"
    db.commit()
    db.refresh(suggestion)
    return suggestion


def delete_suggestion(db: Session, suggestion: EmailSuggestion) -> None:
    db.delete(suggestion)
    db.commit()


def bulk_reject_pending(
    db: Session,
    user_id: int,
    *,
    suggestion_ids: Optional[Iterable[int]] = None,
    reviewer_user_id: Optional[int] = None,
) -> int:
    if reviewer_user_id is None:
        reviewer_user_id = user_id
    query = (
        db.query(EmailSuggestion)
        .join(EmailSuggestion.email_message)
        .join(EmailMessageCache.connection)
        .filter(
            EmailConnection.user_id == user_id,
            EmailSuggestion.status == "pending",
        )
    )
    ids = list(suggestion_ids or [])
    if ids:
        query = query.filter(EmailSuggestion.id.in_(ids))
    rejected = 0
    now = datetime.utcnow()
    for suggestion in query.all():
        suggestion.status = "rejected"
        suggestion.reviewed_by = reviewer_user_id
        suggestion.reviewed_at = now
        if suggestion.email_message.processed_status == "suggested":
            suggestion.email_message.processed_status = "rejected"
        rejected += 1
    if rejected:
        db.commit()
    return rejected


def clear_pending_suggestions(
    db: Session,
    user_id: int,
    *,
    reviewer_user_id: Optional[int] = None,
    gmail_account_email: Optional[str] = None,
    current_account_only: bool = False,
    low_confidence: bool = False,
    no_shipment: bool = False,
    older_than: Optional[datetime] = None,
    suggestion_type: Optional[str] = None,
) -> int:
    """Reject pending suggestions matching the requested filters."""
    if reviewer_user_id is None:
        reviewer_user_id = user_id
    query = (
        db.query(EmailSuggestion)
        .join(EmailSuggestion.email_message)
        .join(EmailMessageCache.connection)
        .filter(
            EmailConnection.user_id == user_id,
            EmailSuggestion.status == "pending",
        )
    )
    if current_account_only:
        active_email = _active_account_email(db, user_id)
        if not active_email:
            return 0
        query = query.filter(EmailMessageCache.gmail_account_email == active_email)
    elif gmail_account_email:
        query = query.filter(EmailMessageCache.gmail_account_email == gmail_account_email)
    if low_confidence:
        query = query.filter(EmailSuggestion.confidence < CONFIDENCE_NO_SHIPMENT_THRESHOLD)
    if no_shipment:
        query = query.filter(EmailSuggestion.shipment_id.is_(None))
    if older_than:
        query = query.filter(EmailSuggestion.created_at <= older_than)
    if suggestion_type:
        query = query.filter(EmailSuggestion.suggestion_type == suggestion_type)
    rejected = 0
    now = datetime.utcnow()
    for suggestion in query.all():
        suggestion.status = "rejected"
        suggestion.reviewed_by = reviewer_user_id
        suggestion.reviewed_at = now
        if suggestion.email_message.processed_status == "suggested":
            suggestion.email_message.processed_status = "rejected"
        rejected += 1
    if rejected:
        db.commit()
    return rejected


def cleanup_for_account(
    db: Session,
    *,
    user_id: int,
    gmail_account_email: Optional[str],
    reviewer_user_id: int,
    hide_messages: bool = True,
    reject_pending: bool = True,
) -> dict[str, int]:
    suggestion_query = (
        db.query(EmailSuggestion)
        .join(EmailSuggestion.email_message)
        .join(EmailMessageCache.connection)
        .filter(EmailConnection.user_id == user_id)
    )
    message_query = (
        db.query(EmailMessageCache)
        .join(EmailMessageCache.connection)
        .filter(EmailConnection.user_id == user_id)
    )
    if gmail_account_email:
        suggestion_query = suggestion_query.filter(
            EmailMessageCache.gmail_account_email == gmail_account_email
        )
        message_query = message_query.filter(
            EmailMessageCache.gmail_account_email == gmail_account_email
        )

    suggestions_rejected = 0
    messages_hidden = 0
    now = datetime.utcnow()
    if reject_pending:
        for suggestion in suggestion_query.filter(EmailSuggestion.status == "pending").all():
            suggestion.status = "dismissed"
            suggestion.reviewed_by = reviewer_user_id
            suggestion.reviewed_at = now
            if suggestion.email_message.processed_status == "suggested":
                suggestion.email_message.processed_status = "ignored"
            suggestions_rejected += 1
    if hide_messages:
        for message in message_query.filter(EmailMessageCache.visibility == "visible").all():
            message.visibility = "hidden"
            if message.processed_status == "suggested":
                message.processed_status = "ignored"
            messages_hidden += 1
    if suggestions_rejected or messages_hidden:
        db.commit()
    return {
        "suggestions_rejected": suggestions_rejected,
        "messages_hidden": messages_hidden,
    }


def compute_extracted_hash(payload: Optional[dict[str, Any]]) -> str:
    """Stable hash for deduplication. Empty/None coerced to {}."""
    payload = payload or {}
    canonical = _canonicalize(payload)
    serialized = json.dumps(canonical, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value.keys())}
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (Decimal,)):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip()
    return value


def _apply_update_shipment(db: Session, suggestion: EmailSuggestion, force: bool) -> None:
    shipment = _require_shipment(db, suggestion, force)
    data = suggestion.extracted_data_json or {}
    updates = {
        field: _coerce_field_value(field, data[field])
        for field in SHIPMENT_UPDATE_FIELDS
        if data.get(field) not in (None, "")
    }
    _apply_field_updates(shipment, updates, force)


def _apply_update_document(db: Session, suggestion: EmailSuggestion, force: bool) -> None:
    shipment = _require_shipment(db, suggestion, force)
    data = suggestion.extracted_data_json or {}
    doc_type = data.get("doc_type")
    if not doc_type:
        raise HTTPException(status_code=400, detail="Document type is required")
    document = (
        db.query(Document)
        .filter(Document.shipment_id == shipment.id, Document.doc_type == doc_type)
        .first()
    )
    updates = {
        key: _coerce_field_value(key, data[key])
        for key in ["status", "date_received", "date_sent", "notes"]
        if data.get(key) not in (None, "")
    }
    if not document:
        if not force:
            raise EmailSuggestionConflict(
                [
                    {
                        "field": "doc_type",
                        "existing_value": None,
                        "suggested_value": doc_type,
                        "message": "Document is missing. Force apply to create it.",
                    }
                ]
            )
        document = Document(shipment_id=shipment.id, doc_type=doc_type, is_required=True)
        db.add(document)
    _apply_field_updates(document, updates, force)


def _apply_update_bl(db: Session, suggestion: EmailSuggestion, force: bool) -> None:
    shipment = _require_shipment(db, suggestion, force)
    data = suggestion.extracted_data_json or {}
    record = db.query(BLManagement).filter(BLManagement.shipment_id == shipment.id).first()
    if not record:
        record = BLManagement(shipment_id=shipment.id)
        db.add(record)
        db.flush()
    updates = {
        field: _coerce_field_value(field, data[field])
        for field in BL_UPDATE_FIELDS
        if data.get(field) not in (None, "")
    }
    _apply_field_updates(record, updates, force)


def _apply_update_demurrage(db: Session, suggestion: EmailSuggestion, force: bool) -> None:
    shipment = _require_shipment(db, suggestion, force)
    if shipment.type != "import":
        raise HTTPException(status_code=400, detail="Demurrage suggestions apply only to import shipments")
    data = suggestion.extracted_data_json or {}
    record = db.query(Demurrage).filter(Demurrage.shipment_id == shipment.id).first()
    if not record:
        record = Demurrage(shipment_id=shipment.id)
        db.add(record)
        db.flush()
    updates = {
        field: _coerce_field_value(field, data[field])
        for field in DEMURRAGE_UPDATE_FIELDS
        if data.get(field) not in (None, "")
    }
    _apply_field_updates(record, updates, force)


def _apply_create_charge(db: Session, suggestion: EmailSuggestion, force: bool) -> None:
    shipment = _require_shipment(db, suggestion, force)
    data = suggestion.extracted_data_json or {}
    if data.get("amount") in (None, ""):
        raise HTTPException(status_code=400, detail="Charge amount is required")
    direction = data.get("direction") or "payable"
    status = data.get("status") or "pending"
    if not is_valid_charge_status(direction, status):
        raise HTTPException(status_code=400, detail=f"{status} is not valid for {direction} charges")
    amount = Decimal(str(data["amount"]))
    invoice_no = data.get("invoice_no")
    duplicate_query = db.query(Charge).filter(
        Charge.shipment_id == shipment.id,
        Charge.direction == direction,
        Charge.amount == amount,
        Charge.status != "cancelled",
    )
    if invoice_no:
        duplicate_query = duplicate_query.filter(func.lower(Charge.invoice_no) == invoice_no.lower())
    if duplicate_query.first() and not force:
        raise EmailSuggestionConflict(
            [
                {
                    "field": "invoice_no",
                    "existing_value": invoice_no,
                    "suggested_value": invoice_no,
                    "message": "Possible duplicate charge. Force apply to create anyway.",
                }
            ]
        )
    db.add(
        Charge(
            shipment_id=shipment.id,
            charge_type=data.get("charge_type") or "ocean_freight",
            direction=direction,
            amount=amount,
            currency=(data.get("currency") or "INR").upper(),
            party_id=data.get("party_id"),
            status=status,
            invoice_no=invoice_no,
            date=_to_date(data.get("date")),
            notes=data.get("notes"),
        )
    )


def _apply_create_followup(db: Session, suggestion: EmailSuggestion, force: bool) -> None:
    shipment = _require_shipment(db, suggestion, force)
    data = suggestion.extracted_data_json or {}
    db.add(
        FollowUpLog(
            shipment_id=shipment.id,
            party_id=data.get("party_id"),
            channel=data.get("channel") or "email",
            summary=data.get("summary") or "Freight-related email received.",
            next_action=data.get("next_action"),
            status=data.get("status") or "open",
            logged_by=suggestion.reviewed_by or 1,
            date=_to_date(data.get("date")) or date.today(),
        )
    )


def _apply_create_task(db: Session, suggestion: EmailSuggestion, force: bool) -> None:
    shipment = _require_shipment(db, suggestion, force)
    data = suggestion.extracted_data_json or {}
    db.add(
        Task(
            shipment_id=shipment.id,
            title=data.get("title") or "Review freight email",
            description=data.get("description"),
            due_date=_to_date(data.get("due_date")),
            priority=data.get("priority") or "info",
            status=data.get("status") or "open",
            auto_generated=True,
        )
    )


def _require_shipment(db: Session, suggestion: EmailSuggestion, force: bool = False) -> Shipment:
    if not suggestion.shipment_id:
        raise HTTPException(status_code=400, detail="Suggestion must be assigned to a shipment before applying")
    shipment = db.query(Shipment).filter(Shipment.id == suggestion.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=400, detail="Shipment does not exist")
    if shipment.is_archived and not force:
        raise EmailSuggestionConflict(
            [
                {
                    "field": "shipment_id",
                    "existing_value": shipment.shipment_code,
                    "suggested_value": shipment.shipment_code,
                    "message": f"Shipment {shipment.shipment_code} is archived. Force apply only if this is intentional.",
                }
            ]
        )
    return shipment


def _apply_field_updates(target: Any, updates: dict[str, Any], force: bool) -> None:
    conflicts = []
    for field, suggested_value in updates.items():
        existing_value = getattr(target, field, None)
        if _has_value(existing_value) and _values_differ(existing_value, suggested_value) and not force:
            conflicts.append(
                {
                    "field": field,
                    "existing_value": _json_value(existing_value),
                    "suggested_value": _json_value(suggested_value),
                    "message": "Existing value differs from suggested value.",
                }
            )
    if conflicts:
        raise EmailSuggestionConflict(conflicts)
    for field, value in updates.items():
        setattr(target, field, value)


def _coerce_field_value(field: str, value: Any) -> Any:
    if field.endswith("_date") or field in {"eta", "etd", "draft_received", "approval_date", "final_bl_date", "start_date"}:
        return _to_date(value)
    return value


def _to_date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def _has_value(value: Any) -> bool:
    return value not in (None, "")


def _values_differ(existing_value: Any, suggested_value: Any) -> bool:
    return str(_json_value(existing_value)) != str(_json_value(suggested_value))


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _match_shipment_field(db: Session, column: Any, value: str) -> Optional[Shipment]:
    return db.query(Shipment).filter(func.lower(column) == value.lower()).first()


def _shipment_from_code(db: Session, value: Optional[Any]) -> Optional[Shipment]:
    if not isinstance(value, str) or not value.strip():
        return None
    if not is_valid_shipment_code(value.strip()):
        return None
    return _match_shipment_field(db, Shipment.shipment_code, value.strip())


def _suggestion_exists(
    db: Session,
    *,
    email_message_id: int,
    suggestion_type: str,
    shipment_id: Optional[int],
    extracted_hash: Optional[str],
) -> bool:
    query = db.query(EmailSuggestion.id).filter(
        EmailSuggestion.email_message_id == email_message_id,
        EmailSuggestion.suggestion_type == suggestion_type,
    )
    if shipment_id is None:
        query = query.filter(EmailSuggestion.shipment_id.is_(None))
    else:
        query = query.filter(EmailSuggestion.shipment_id == shipment_id)
    if extracted_hash:
        query = query.filter(EmailSuggestion.extracted_data_hash == extracted_hash)
    return query.first() is not None


def _active_account_email(db: Session, user_id: int) -> Optional[str]:
    connection = (
        db.query(EmailConnection)
        .filter(EmailConnection.user_id == user_id, EmailConnection.is_active.is_(True))
        .order_by(EmailConnection.updated_at.desc(), EmailConnection.id.desc())
        .first()
    )
    if not connection:
        return None
    return connection.gmail_account_email or connection.email_address

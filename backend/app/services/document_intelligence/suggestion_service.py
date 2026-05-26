from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.bl_management import BLManagement
from app.models.document_intelligence import (
    DocumentExtractedField,
    DocumentExtraction,
    DocumentIntelligenceSuggestion,
)
from app.models.shipment import Shipment
from app.services.audit_service import record_audit_log
from app.services.event_service import OperationalEventType, record_operational_event


def create_suggestions_from_extraction(db: Session, extraction: DocumentExtraction) -> list[DocumentIntelligenceSuggestion]:
    shipment = db.query(Shipment).filter(Shipment.id == extraction.shipment_id).first() if extraction.shipment_id else None
    suggestions: list[DocumentIntelligenceSuggestion] = []
    fields = list(extraction.fields)
    if not shipment:
        suggestions.append(
            _suggestion(
                extraction,
                "manual_review",
                "document_extraction",
                extraction.id,
                "review_unlinked_document",
                0.50,
                {"reason": "No linked shipment for document extraction"},
            )
        )
    else:
        for field in fields:
            if field.status == "low_confidence":
                continue
            if field.field_key in {"origin_port", "destination_port", "vessel_name", "voyage_number"}:
                target_attr = {
                    "origin_port": "origin_port",
                    "destination_port": "dest_port",
                    "vessel_name": "vessel_name",
                    "voyage_number": "voyage_no",
                }[field.field_key]
                if not getattr(shipment, target_attr, None):
                    suggestions.append(
                        _suggestion(
                            extraction,
                            "update_shipment",
                            "shipment",
                            shipment.id,
                            f"review_{target_attr}",
                            field.confidence,
                            {
                                "field": target_attr,
                                "current_value": None,
                                "suggested_value": field.normalized_value or field.field_value,
                            },
                        )
                    )
            if field.field_key == "bl_number" and not shipment.bl_number:
                suggestions.append(
                    _suggestion(
                        extraction,
                        "update_bl",
                        "shipment",
                        shipment.id,
                        "review_bl_number",
                        field.confidence,
                        {"field": "bl_number", "suggested_value": field.normalized_value or field.field_value},
                    )
                )
            if field.field_key == "container_number":
                suggestions.append(
                    _suggestion(
                        extraction,
                        "update_container",
                        "container",
                        None,
                        "review_container_number",
                        field.confidence,
                        {"container_number": field.normalized_value or field.field_value},
                    )
                )
        amount = _first_field(fields, "amount")
        currency = _first_field(fields, "currency")
        if amount:
            suggestions.append(
                _suggestion(
                    extraction,
                    "create_charge",
                    "charge",
                    None,
                    "review_charge_from_document",
                    min(amount.confidence or 0.60, currency.confidence if currency else 0.60),
                    {
                        "amount": amount.normalized_value or amount.field_value,
                        "currency": currency.normalized_value if currency else None,
                        "direction": "receivable",
                        "note": "Review-only suggestion. Phase 13 does not create charges automatically.",
                    },
                )
            )

    for suggestion in suggestions:
        db.add(suggestion)
    db.flush()
    return suggestions


def approve_suggestion(
    db: Session,
    suggestion_id: int,
    user: AuthenticatedUser,
    *,
    notes: Optional[str] = None,
    request=None,
) -> DocumentIntelligenceSuggestion:
    suggestion = _get_suggestion(db, suggestion_id)
    _review_suggestion(suggestion, user, "approved", notes)
    db.commit()
    db.refresh(suggestion)
    _audit_and_event(db, suggestion, user, "document_intelligence.suggestion_approve", OperationalEventType.DOCUMENT_INTELLIGENCE_SUGGESTION_APPROVED.value, request)
    return suggestion


def reject_suggestion(
    db: Session,
    suggestion_id: int,
    user: AuthenticatedUser,
    *,
    reason: Optional[str] = None,
    request=None,
) -> DocumentIntelligenceSuggestion:
    suggestion = _get_suggestion(db, suggestion_id)
    _review_suggestion(suggestion, user, "rejected", reason)
    db.commit()
    db.refresh(suggestion)
    _audit_and_event(db, suggestion, user, "document_intelligence.suggestion_reject", OperationalEventType.DOCUMENT_INTELLIGENCE_SUGGESTION_REJECTED.value, request)
    return suggestion


def dismiss_suggestion(
    db: Session,
    suggestion_id: int,
    user: AuthenticatedUser,
    *,
    reason: Optional[str] = None,
    request=None,
) -> DocumentIntelligenceSuggestion:
    suggestion = _get_suggestion(db, suggestion_id)
    _review_suggestion(suggestion, user, "dismissed", reason)
    db.commit()
    db.refresh(suggestion)
    _audit_and_event(db, suggestion, user, "document_intelligence.suggestion_dismiss", OperationalEventType.DOCUMENT_INTELLIGENCE_SUGGESTION_REJECTED.value, request)
    return suggestion


def apply_suggestion(
    db: Session,
    suggestion_id: int,
    user: AuthenticatedUser,
    *,
    request=None,
) -> DocumentIntelligenceSuggestion:
    _get_suggestion(db, suggestion_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Applying document intelligence suggestions is disabled in Phase 13. Approve or reject the suggestion for review tracking only.",
    )


def _get_suggestion(db: Session, suggestion_id: int) -> DocumentIntelligenceSuggestion:
    suggestion = (
        db.query(DocumentIntelligenceSuggestion)
        .filter(DocumentIntelligenceSuggestion.id == suggestion_id)
        .first()
    )
    if not suggestion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document intelligence suggestion not found")
    return suggestion


def _review_suggestion(
    suggestion: DocumentIntelligenceSuggestion,
    user: AuthenticatedUser,
    status_value: str,
    notes: Optional[str],
) -> None:
    suggestion.status = status_value
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.reviewed_by_user_id = user.id
    suggestion.reviewed_by_name = user.name
    suggestion.metadata_json = {
        **(suggestion.metadata_json or {}),
        **({"review_notes": notes} if notes else {}),
    }


def _suggestion(
    extraction: DocumentExtraction,
    suggestion_type: str,
    target_entity_type: str,
    target_entity_id: Optional[int],
    suggested_action: str,
    confidence: Optional[float],
    payload: dict,
) -> DocumentIntelligenceSuggestion:
    return DocumentIntelligenceSuggestion(
        extraction_id=extraction.id,
        document_version_id=extraction.document_version_id,
        shipment_id=extraction.shipment_id,
        suggestion_type=suggestion_type,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        suggested_action=suggested_action,
        confidence=confidence,
        status="pending",
        payload_json=payload,
        metadata_json={"source": "document_intelligence"},
    )


def _first_field(fields: list[DocumentExtractedField], field_key: str) -> Optional[DocumentExtractedField]:
    return next((field for field in fields if field.field_key == field_key), None)


def _audit_and_event(
    db: Session,
    suggestion: DocumentIntelligenceSuggestion,
    user: AuthenticatedUser,
    action: str,
    event_type: str,
    request,
) -> None:
    record_audit_log(
        db,
        user,
        action,
        "document_intelligence_suggestion",
        entity_id=suggestion.id,
        entity_label=suggestion.suggestion_type,
        description="Document intelligence suggestion reviewed.",
        metadata={
            "status": suggestion.status,
            "document_version_id": suggestion.document_version_id,
            "shipment_id": suggestion.shipment_id,
        },
        request=request,
    )
    record_operational_event(
        db,
        event_type,
        "document_intelligence_suggestion",
        entity_id=suggestion.id,
        entity_label=suggestion.suggestion_type,
        shipment_id=suggestion.shipment_id,
        actor_user=user,
        source="user",
        new_state={"status": suggestion.status, "suggestion_type": suggestion.suggestion_type},
        metadata={"document_version_id": suggestion.document_version_id},
        request=request,
        run_validation=False,
    )

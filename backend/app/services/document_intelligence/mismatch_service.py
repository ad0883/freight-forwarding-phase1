from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.bl_management import BLManagement
from app.models.charge import Charge
from app.models.container import Container
from app.models.document_intelligence import (
    DocumentExtractedField,
    DocumentExtraction,
    DocumentMismatchResult,
)
from app.models.shipment import Shipment
from app.models.validation_issue import ValidationIssue
from app.services.notification_service import create_notification


DECLARED_TYPE_ALIASES = {
    "INVOICE": "COMMERCIAL_INVOICE",
    "FREIGHT_INVOICE": "FREIGHT_INVOICE",
    "PACKING_LIST": "PACKING_LIST",
    "BL_DRAFT": "BL_DRAFT",
    "FINAL_BL": "FINAL_BL",
    "DO": "DO",
    "BOE": "BOE",
    "PRE_ALERT": "PRE_ALERT",
    "ARRIVAL_NOTICE": "ARRIVAL_NOTICE",
    "COO": "COO",
}


def compare_extraction_to_system(db: Session, extraction: DocumentExtraction) -> list[DocumentMismatchResult]:
    fields = list(extraction.fields)
    shipment = db.query(Shipment).filter(Shipment.id == extraction.shipment_id).first() if extraction.shipment_id else None
    mismatches: list[DocumentMismatchResult] = []

    if extraction.status in {"low_confidence", "manual_review_required"}:
        mismatches.append(
            _mismatch(
                extraction,
                "document_intelligence_low_confidence",
                "warning",
                None,
                None,
                str(extraction.overall_confidence or 0),
                "Document intelligence confidence is below the configured review threshold.",
                "Review extracted fields before relying on this document.",
            )
        )

    declared = _canonical_type(extraction.document_type)
    detected = _canonical_type(extraction.detected_document_type)
    if detected and detected != "UNKNOWN" and declared and declared != detected:
        mismatches.append(
            _mismatch(
                extraction,
                "document_type_mismatch",
                "warning",
                "document_type",
                declared,
                detected,
                f"Uploaded document type {declared} differs from detected type {detected}.",
                "Confirm that the file was uploaded under the correct checklist item.",
            )
        )

    for field in _fields(fields, "shipment_code"):
        matched = db.query(Shipment).filter(Shipment.shipment_code == field.normalized_value).first()
        if not matched:
            mismatches.append(
                _from_field(
                    extraction,
                    field,
                    "shipment_code_not_found",
                    "critical",
                    None,
                    "Extracted shipment code was not found in the system.",
                    "Check whether this document belongs to another shipment or the extracted code is wrong.",
                )
            )
        elif extraction.shipment_id and matched.id != extraction.shipment_id:
            mismatches.append(
                _from_field(
                    extraction,
                    field,
                    "shipment_code_mismatch",
                    "critical",
                    shipment.shipment_code if shipment else None,
                    "Extracted shipment code points to a different shipment.",
                    "Do not approve this document until the shipment link is confirmed.",
                )
            )

    if shipment:
        _compare_simple_field(mismatches, extraction, fields, "bl_number", shipment.bl_number, "bl_number_mismatch")
        _compare_simple_field(mismatches, extraction, fields, "origin_port", shipment.origin_port, "origin_port_mismatch")
        _compare_simple_field(mismatches, extraction, fields, "destination_port", shipment.dest_port, "destination_port_mismatch")
        _compare_containers(db, mismatches, extraction, fields, shipment)
        _compare_amounts(db, mismatches, extraction, fields, shipment)
        _compare_free_days(db, mismatches, extraction, fields, shipment)

    for mismatch in mismatches:
        db.add(mismatch)
    db.flush()
    create_validation_issues_for_mismatches(db, mismatches)
    return mismatches


def create_validation_issues_for_mismatches(
    db: Session, mismatches: Iterable[DocumentMismatchResult]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    today = date.today().isoformat()
    for mismatch in mismatches:
        if mismatch.severity not in {"warning", "critical"}:
            continue
        existing = (
            db.query(ValidationIssue)
            .filter(
                ValidationIssue.rule_key == mismatch.rule_key,
                ValidationIssue.entity_type == "document_extraction",
                ValidationIssue.entity_id == mismatch.extraction_id,
                ValidationIssue.status == "open",
            )
            .first()
        )
        if existing:
            mismatch.validation_issue_id = existing.id
            continue
        issue = ValidationIssue(
            rule_key=mismatch.rule_key,
            entity_type="document_extraction",
            entity_id=mismatch.extraction_id,
            entity_label=mismatch.field_key or mismatch.rule_key,
            shipment_id=mismatch.shipment_id,
            severity=mismatch.severity,
            status="open",
            message=mismatch.message,
            recommended_action=mismatch.recommended_action,
            metadata_json={
                "document_version_id": mismatch.document_version_id,
                "mismatch_id": mismatch.id,
                "field_key": mismatch.field_key,
                "date": today,
            },
        )
        db.add(issue)
        db.flush()
        mismatch.validation_issue_id = issue.id
        issues.append(issue)
        _create_mismatch_notification(db, mismatch)
    return issues


def _create_mismatch_notification(db: Session, mismatch: DocumentMismatchResult) -> None:
    priority = "critical" if mismatch.severity == "critical" else "warning"
    dedupe_key = f"document_mismatch_{priority}:{mismatch.id}"
    create_notification(
        db,
        title="Document mismatch needs review",
        message=mismatch.message,
        category="document",
        priority=priority,
        target_role="STAFF",
        entity_type="document_mismatch",
        entity_id=mismatch.id,
        entity_label=mismatch.field_key or mismatch.rule_key,
        action_url=f"/shipments/{mismatch.shipment_id}" if mismatch.shipment_id else "/validation-issues",
        dedupe_key=dedupe_key,
        source="workflow",
        metadata={
            "rule_key": mismatch.rule_key,
            "shipment_id": mismatch.shipment_id,
            "document_version_id": mismatch.document_version_id,
        },
    )


def _compare_simple_field(
    mismatches: list[DocumentMismatchResult],
    extraction: DocumentExtraction,
    fields: list[DocumentExtractedField],
    field_key: str,
    system_value: Optional[str],
    rule_key: str,
) -> None:
    if not system_value:
        return
    for field in _fields(fields, field_key):
        if _norm(system_value) != _norm(field.normalized_value or field.field_value):
            mismatches.append(
                _from_field(
                    extraction,
                    field,
                    rule_key,
                    "warning",
                    system_value,
                    f"Extracted {field_key.replace('_', ' ')} differs from the shipment record.",
                    "Review the document and existing shipment data before approving.",
                )
            )


def _compare_containers(
    db: Session,
    mismatches: list[DocumentMismatchResult],
    extraction: DocumentExtraction,
    fields: list[DocumentExtractedField],
    shipment: Shipment,
) -> None:
    system_containers = {
        _norm(row.container_number)
        for row in db.query(Container).filter(Container.shipment_id == shipment.id, Container.is_active.is_(True)).all()
    }
    for field in _fields(fields, "container_number"):
        value = _norm(field.normalized_value or field.field_value)
        if field.status == "low_confidence":
            mismatches.append(
                _from_field(
                    extraction,
                    field,
                    "container_number_format_invalid",
                    "warning",
                    None,
                    "Extracted container number does not pass ISO format validation.",
                    "Confirm the container number before using it.",
                )
            )
        elif system_containers and value not in system_containers:
            mismatches.append(
                _from_field(
                    extraction,
                    field,
                    "container_number_not_in_shipment",
                    "warning",
                    ", ".join(sorted(system_containers)),
                    "Extracted container number is not linked to this shipment.",
                    "Add the container only after manual verification.",
                )
            )


def _compare_amounts(
    db: Session,
    mismatches: list[DocumentMismatchResult],
    extraction: DocumentExtraction,
    fields: list[DocumentExtractedField],
    shipment: Shipment,
) -> None:
    amount_fields = _fields(fields, "amount")
    if not amount_fields:
        return
    charges = (
        db.query(Charge)
        .filter(Charge.shipment_id == shipment.id, Charge.status != "cancelled")
        .all()
    )
    charge_amounts = [(Decimal(row.amount), row.currency) for row in charges]
    currency = next((field.normalized_value for field in _fields(fields, "currency")), None)
    for field in amount_fields:
        amount = _decimal(field.normalized_value)
        if amount is None:
            continue
        if not charge_amounts:
            mismatches.append(
                _from_field(
                    extraction,
                    field,
                    "invoice_amount_mismatch",
                    "warning",
                    None,
                    "Invoice amount was extracted but no active charge exists for this shipment.",
                    "Create or update charges only after manual approval.",
                )
            )
            continue
        if not any(_amount_close(amount, system_amount) and (not currency or currency == charge_currency) for system_amount, charge_currency in charge_amounts):
            mismatches.append(
                _from_field(
                    extraction,
                    field,
                    "invoice_amount_mismatch",
                    "warning",
                    ", ".join(f"{code} {value}" for value, code in charge_amounts[:5]),
                    "Extracted invoice amount does not match active shipment charges.",
                    "Review charges before approving the document.",
                )
            )


def _compare_free_days(
    db: Session,
    mismatches: list[DocumentMismatchResult],
    extraction: DocumentExtraction,
    fields: list[DocumentExtractedField],
    shipment: Shipment,
) -> None:
    free_day_fields = _fields(fields, "free_days")
    if not free_day_fields:
        return
    bl = db.query(BLManagement).filter(BLManagement.shipment_id == shipment.id).first()
    # The legacy BL table does not store DO free days; this remains informational
    # unless a later phase adds a canonical system value.
    if bl is None:
        return


def _fields(fields: list[DocumentExtractedField], field_key: str) -> list[DocumentExtractedField]:
    return [field for field in fields if field.field_key == field_key]


def _from_field(
    extraction: DocumentExtraction,
    field: DocumentExtractedField,
    rule_key: str,
    severity: str,
    system_value: Optional[str],
    message: str,
    recommended_action: str,
) -> DocumentMismatchResult:
    return _mismatch(
        extraction,
        rule_key,
        severity,
        field.field_key,
        system_value,
        field.normalized_value or field.field_value,
        message,
        recommended_action,
    )


def _mismatch(
    extraction: DocumentExtraction,
    rule_key: str,
    severity: str,
    field_key: Optional[str],
    system_value: Optional[str],
    extracted_value: Optional[str],
    message: str,
    recommended_action: str,
) -> DocumentMismatchResult:
    return DocumentMismatchResult(
        extraction_id=extraction.id,
        document_version_id=extraction.document_version_id,
        shipment_id=extraction.shipment_id,
        rule_key=rule_key,
        severity=severity,
        status="open",
        field_key=field_key,
        system_value=str(system_value) if system_value is not None else None,
        extracted_value=str(extracted_value) if extracted_value is not None else None,
        message=message,
        recommended_action=recommended_action,
        metadata_json={"source": "document_intelligence"},
    )


def _canonical_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = value.strip().upper()
    return DECLARED_TYPE_ALIASES.get(key, key)


def _norm(value: Optional[str]) -> str:
    return " ".join(str(value or "").upper().split())


def _decimal(value: Optional[str]) -> Optional[Decimal]:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _amount_close(extracted: Decimal, system: Decimal) -> bool:
    tolerance = max(Decimal("1.00"), abs(system) * Decimal("0.01"))
    return abs(extracted - system) <= tolerance

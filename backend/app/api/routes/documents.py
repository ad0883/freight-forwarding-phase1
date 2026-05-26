from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.document import Document
from app.models.shipment import Shipment
from app.schemas.document import DocumentRead, DocumentUpdate
from app.services.audit_service import changed_fields, record_audit_log
from app.services.event_service import OperationalEventType, diff_state, record_operational_event


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/shipment/{shipment_id}", response_model=list[DocumentRead])
def list_documents_for_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[Document]:
    shipment = db.query(Shipment.id).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return (
        db.query(Document)
        .filter(Document.shipment_id == shipment_id)
        .order_by(Document.created_at.asc(), Document.id.asc())
        .all()
    )


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int,
    document_in: DocumentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    data = document_in.model_dump(exclude_unset=True)
    before = {field: getattr(document, field, None) for field in data}
    for field, value in data.items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    record_audit_log(
        db,
        current_user,
        "document.updated",
        "document",
        entity_id=document.id,
        entity_label=document.doc_type,
        description="Document updated.",
        metadata={
            "shipment_id": document.shipment_id,
            "fields_changed": changed_fields(before, {field: getattr(document, field, None) for field in data}),
        },
        request=request,
    )
    after_state = {field: getattr(document, field, None) for field in data}
    record_operational_event(
        db,
        OperationalEventType.DOCUMENT_UPDATED.value,
        "document",
        entity_id=document.id,
        entity_label=document.doc_type,
        shipment_id=document.shipment_id,
        actor_user=current_user,
        source="user",
        previous_state=before,
        new_state={
            "doc_type": document.doc_type,
            "status": document.status,
            "file_url": getattr(document, "file_url", None),
            **after_state,
        },
        metadata={"fields_changed": diff_state(before, after_state)},
        request=request,
    )
    return document

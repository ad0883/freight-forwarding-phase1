from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_write_access
from app.models.document import Document
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentUpdate


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/shipment/{shipment_id}", response_model=list[DocumentRead])
def list_documents_for_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
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
    db: Session = Depends(get_db),
    _: User = Depends(require_write_access),
) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    for field, value in document_in.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document

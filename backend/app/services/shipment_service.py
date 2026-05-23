from datetime import datetime

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.shipment import Shipment
from app.models.task import Task
from app.schemas.shipment import ShipmentCreate


EXPORT_DOCUMENTS = [
    "BOOKING_CONFIRMATION",
    "SI",
    "VGM",
    "BL_DRAFT",
    "FINAL_BL",
    "INVOICE",
    "PACKING_LIST",
    "COO",
    "AWB",
]

IMPORT_DOCUMENTS = [
    "PRE_ALERT",
    "ARRIVAL_NOTICE",
    "MBL",
    "HBL",
    "FREIGHT_INVOICE",
    "DO",
    "BOE",
    "TELEX_RELEASE",
]


def generate_shipment_code(db: Session, shipment_type: str) -> str:
    year = datetime.utcnow().year
    type_code = "EXP" if shipment_type == "export" else "IMP"
    prefix = f"FF-{type_code}-{year}-"
    existing_count = (
        db.query(Shipment)
        .filter(Shipment.shipment_code.like(f"{prefix}%"))
        .count()
    )
    return f"{prefix}{existing_count + 1:03d}"


def create_default_documents(db: Session, shipment: Shipment) -> None:
    doc_types = EXPORT_DOCUMENTS if shipment.type == "export" else IMPORT_DOCUMENTS
    for doc_type in doc_types:
        db.add(
            Document(
                shipment_id=shipment.id,
                doc_type=doc_type,
                status="pending",
                is_required=True,
            )
        )


def create_initial_task(db: Session, shipment: Shipment) -> None:
    title = (
        "Book container with shipping line"
        if shipment.type == "export"
        else "Track ETA updates from line"
    )
    db.add(
        Task(
            shipment_id=shipment.id,
            title=title,
            description="Auto-generated Phase 1 starter task.",
            priority="info",
            status="open",
            auto_generated=True,
        )
    )


def create_shipment_with_defaults(
    db: Session, shipment_in: ShipmentCreate, created_by: int
) -> Shipment:
    shipment = Shipment(
        **shipment_in.model_dump(),
        shipment_code=generate_shipment_code(db, shipment_in.type),
        status="active",
        created_by=created_by,
    )
    db.add(shipment)
    db.flush()
    create_default_documents(db, shipment)
    create_initial_task(db, shipment)
    db.commit()
    db.refresh(shipment)
    return shipment

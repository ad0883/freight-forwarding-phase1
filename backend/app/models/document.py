from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    doc_type = Column(String(80), nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    date_received = Column(Date, nullable=True)
    date_sent = Column(Date, nullable=True)
    file_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_required = Column(Boolean, nullable=False, default=True)
    current_version_id = Column(Integer, nullable=True, index=True)
    uploaded_file_count = Column(Integer, nullable=False, default=0)
    latest_uploaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="documents")
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        foreign_keys="DocumentVersion.document_id",
        cascade="all, delete-orphan",
    )
    current_version = relationship(
        "DocumentVersion",
        primaryjoin="foreign(Document.current_version_id) == DocumentVersion.id",
        viewonly=True,
        uselist=False,
    )

    @property
    def current_version_no(self) -> Optional[int]:
        return self.current_version.version_no if self.current_version else None

    @property
    def current_review_status(self) -> Optional[str]:
        return self.current_version.review_status if self.current_version else None

    @property
    def latest_file_name(self) -> Optional[str]:
        if not self.current_version or not self.current_version.file:
            return None
        return self.current_version.file.sanitized_filename

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class DocumentFile(Base):
    __tablename__ = "document_files"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    original_filename = Column(String(255), nullable=False)
    sanitized_filename = Column(String(255), nullable=False)
    content_type = Column(String(120), nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    storage_backend = Column(String(30), nullable=False, default="database")
    storage_key = Column(String(500), nullable=True)
    status = Column(String(30), nullable=False, default="active", index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    uploaded_by_name = Column(String(150), nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    metadata_json = Column(JSON, nullable=True)

    blob = relationship(
        "DocumentFileBlob",
        back_populates="file",
        cascade="all, delete-orphan",
        uselist=False,
    )
    versions = relationship("DocumentVersion", back_populates="file")


class DocumentFileBlob(Base):
    __tablename__ = "document_file_blobs"
    __table_args__ = (
        UniqueConstraint("document_file_id", name="uq_document_file_blobs_file_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    document_file_id = Column(Integer, ForeignKey("document_files.id"), nullable=False, index=True)
    content = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    file = relationship("DocumentFile", back_populates="blob")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "shipment_id",
            "document_id",
            "document_type",
            "version_no",
            name="uq_document_versions_version_no",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    document_type = Column(String(80), nullable=False, index=True)
    document_file_id = Column(Integer, ForeignKey("document_files.id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    version_label = Column(String(120), nullable=True)
    status = Column(String(30), nullable=False, default="active", index=True)
    review_status = Column(String(30), nullable=False, default="pending_review", index=True)
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    replaces_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(150), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    archived_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    archived_by_name = Column(String(150), nullable=True)
    archived_at = Column(DateTime, nullable=True)
    archive_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    shipment = relationship("Shipment")
    document = relationship(
        "Document",
        back_populates="versions",
        foreign_keys=[document_id],
    )
    file = relationship("DocumentFile", back_populates="versions")
    replaces_version = relationship("DocumentVersion", remote_side=[id])
    events = relationship(
        "DocumentVersionEvent",
        back_populates="version",
        cascade="all, delete-orphan",
    )

    @property
    def shipment_code(self) -> Optional[str]:
        return self.shipment.shipment_code if self.shipment else None


class DocumentVersionEvent(Base):
    __tablename__ = "document_version_events"

    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    version = relationship("DocumentVersion", back_populates="events")


class DocumentAccessLog(Base):
    __tablename__ = "document_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_file_id = Column(Integer, ForeignKey("document_files.id"), nullable=False, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(150), nullable=True)
    action = Column(String(40), nullable=False, default="download", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

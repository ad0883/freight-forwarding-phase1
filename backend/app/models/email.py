from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class EmailConnection(Base):
    __tablename__ = "email_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(30), nullable=False, default="gmail", index=True)
    email_address = Column(String(255), nullable=True)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    scopes = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("EmailMessageCache", back_populates="connection")


class EmailMessageCache(Base):
    __tablename__ = "email_message_cache"
    __table_args__ = (
        UniqueConstraint("connection_id", "gmail_message_id", name="uq_email_message_connection_gmail_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("email_connections.id"), nullable=False, index=True)
    gmail_message_id = Column(String(255), nullable=False, index=True)
    thread_id = Column(String(255), nullable=True, index=True)
    subject = Column(Text, nullable=True)
    sender = Column(Text, nullable=True)
    recipients = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    body_preview = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=True, index=True)
    has_attachments = Column(Boolean, nullable=False, default=False)
    classification = Column(String(60), nullable=False, default="unknown", index=True)
    matched_shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    processed_status = Column(String(30), nullable=False, default="new", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    connection = relationship("EmailConnection", back_populates="messages")
    matched_shipment = relationship("Shipment")
    suggestions = relationship(
        "EmailSuggestion", back_populates="email_message", cascade="all, delete-orphan"
    )


class EmailSuggestion(Base):
    __tablename__ = "email_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    email_message_id = Column(Integer, ForeignKey("email_message_cache.id"), nullable=False, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    suggestion_type = Column(String(60), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=0.3)
    extracted_data_json = Column(JSON, nullable=False, default=dict)
    status = Column(String(30), nullable=False, default="pending", index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    email_message = relationship("EmailMessageCache", back_populates="suggestions")
    shipment = relationship("Shipment")
    reviewer = relationship("User")

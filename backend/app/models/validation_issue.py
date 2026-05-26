from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("operational_events.id"), nullable=True, index=True)
    rule_key = Column(String(120), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    entity_label = Column(String(255), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    severity = Column(String(20), nullable=False, default="warning", index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    message = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

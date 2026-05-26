from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class OperationalEvent(Base):
    __tablename__ = "operational_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(120), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    entity_label = Column(String(255), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_name = Column(String(150), nullable=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(30), nullable=True)
    source = Column(String(40), nullable=False, default="user", index=True)
    correlation_id = Column(String(120), nullable=True, index=True)
    request_id = Column(String(120), nullable=True)
    previous_state_json = Column(JSON, nullable=True)
    new_state_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    validation_status = Column(String(40), nullable=False, default="not_checked", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

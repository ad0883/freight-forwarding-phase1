from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.db.session import Base


class RuleDefinition(Base):
    __tablename__ = "rule_definitions"

    id = Column(Integer, primary_key=True, index=True)
    rule_key = Column(String(120), nullable=False, unique=True, index=True)
    name = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(String(80), nullable=True, index=True)
    event_type = Column(String(120), nullable=True, index=True)
    severity = Column(String(20), nullable=False, default="warning")
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    is_blocking = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(40), nullable=False, index=True)
    priority = Column(String(30), nullable=False, default="info", index=True)
    target_role = Column(String(30), nullable=True, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    entity_type = Column(String(80), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    entity_label = Column(String(255), nullable=True)
    action_url = Column(Text, nullable=True)
    dedupe_key = Column(String(255), nullable=True, unique=True, index=True)
    source = Column(String(40), nullable=False, default="system", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)

    target_user = relationship("User")
    user_states = relationship(
        "NotificationUserState", back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationUserState(Base):
    __tablename__ = "notification_user_states"
    __table_args__ = (
        UniqueConstraint("notification_id", "user_id", name="uq_notification_user_state"),
    )

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    notification = relationship("Notification", back_populates="user_states")
    user = relationship("User")


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_key = Column(String(120), nullable=False, unique=True, index=True)
    name = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(40), nullable=False, index=True)
    priority = Column(String(30), nullable=False, default="info")
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    threshold_days = Column(Integer, nullable=True)
    target_role = Column(String(30), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

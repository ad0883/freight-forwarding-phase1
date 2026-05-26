from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="STAFF")
    is_active = Column(Boolean, nullable=False, default=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    created_shipments = relationship(
        "Shipment", back_populates="creator", foreign_keys="Shipment.created_by"
    )
    assigned_tasks = relationship("Task", back_populates="assignee")
    followups = relationship("FollowUpLog", back_populates="logger")

    @property
    def organization_name(self) -> Optional[str]:
        return self.organization.name if self.organization else None

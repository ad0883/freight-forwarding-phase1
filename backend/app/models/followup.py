from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class FollowUpLog(Base):
    __tablename__ = "follow_up_logs"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    channel = Column(String(30), nullable=False)
    summary = Column(Text, nullable=False)
    next_action = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="open")
    logged_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)

    shipment = relationship("Shipment", back_populates="followups")
    party = relationship("Party", back_populates="followups")
    logger = relationship("User", back_populates="followups")

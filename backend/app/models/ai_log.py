from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.db.session import Base


class AIInteractionLog(Base):
    __tablename__ = "ai_interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    used_llm = Column(Boolean, nullable=False, default=False)
    provider = Column(String(50), nullable=False, default="fallback")
    model = Column(String(120), nullable=True)
    fallback_used = Column(Boolean, nullable=False, default=True)
    priority = Column(String(20), nullable=False, default="none")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

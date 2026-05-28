"""Phase 22 Control Tower Dashboard models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class ControlTowerSavedView(Base):
    __tablename__ = "control_tower_saved_views"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    visibility = Column(String(20), nullable=False, default="private")
    filters_json = Column(JSON, nullable=True)
    layout_json = Column(JSON, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class ControlTowerSnapshot(Base):
    __tablename__ = "control_tower_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    snapshot_key = Column(String(60), nullable=False, index=True)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    scope = Column(String(30), nullable=False, default="global")
    summary_json = Column(JSON, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class ControlTowerWidgetPreference(Base):
    __tablename__ = "control_tower_widget_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    widget_key = Column(String(60), nullable=False)
    is_visible = Column(Boolean, nullable=False, default=True)
    position_index = Column(Integer, nullable=True)
    settings_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class ControlTowerActivityLog(Base):
    __tablename__ = "control_tower_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activity_type = Column(String(60), nullable=False)
    safe_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

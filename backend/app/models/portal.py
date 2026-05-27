"""Phase 18 exporter/importer portal models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.db.session import Base


class PortalAccount(Base):
    __tablename__ = "portal_accounts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    account_type = Column(String(30), nullable=False, default="exporter", index=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    company_name = Column(String(255), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PortalPartyLink(Base):
    __tablename__ = "portal_party_links"

    id = Column(Integer, primary_key=True, index=True)
    portal_account_id = Column(Integer, ForeignKey("portal_accounts.id"), nullable=False, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False, index=True)
    relationship_type = Column(String(40), nullable=False, default="customer")
    is_primary = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PortalShipmentAccess(Base):
    __tablename__ = "portal_shipment_access"

    id = Column(Integer, primary_key=True, index=True)
    portal_account_id = Column(Integer, ForeignKey("portal_accounts.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    access_level = Column(String(30), nullable=False, default="view_only")
    can_view_documents = Column(Boolean, nullable=False, default=True)
    can_upload_documents = Column(Boolean, nullable=False, default=False)
    can_view_finance = Column(Boolean, nullable=False, default=False)
    can_raise_requests = Column(Boolean, nullable=False, default=True)
    can_comment = Column(Boolean, nullable=False, default=True)
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class PortalDocumentAccess(Base):
    __tablename__ = "portal_document_access"

    id = Column(Integer, primary_key=True, index=True)
    portal_account_id = Column(Integer, ForeignKey("portal_accounts.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)
    document_type = Column(String(80), nullable=True)
    access_type = Column(String(20), nullable=False, default="view")
    can_download = Column(Boolean, nullable=False, default=True)
    can_upload_new_version = Column(Boolean, nullable=False, default=False)
    visible_to_customer = Column(Boolean, nullable=False, default=True)
    granted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_by_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)


class PortalRequest(Base):
    __tablename__ = "portal_requests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    request_number = Column(String(60), nullable=False, unique=True, index=True)
    portal_account_id = Column(Integer, ForeignKey("portal_accounts.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True, index=True)
    request_type = Column(String(40), nullable=False, default="other", index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="open", index=True)
    priority = Column(String(10), nullable=False, default="p3")
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to_name = Column(String(150), nullable=True)
    linked_exception_case_id = Column(Integer, ForeignKey("exception_cases.id"), nullable=True)
    linked_approval_request_id = Column(Integer, ForeignKey("approval_requests.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_by_name = Column(String(150), nullable=True)
    metadata_json = Column(JSON, nullable=True)


class PortalRequestComment(Base):
    __tablename__ = "portal_request_comments"

    id = Column(Integer, primary_key=True, index=True)
    portal_request_id = Column(Integer, ForeignKey("portal_requests.id"), nullable=False, index=True)
    author_type = Column(String(20), nullable=False, default="portal_user")
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_name = Column(String(150), nullable=True)
    comment_text = Column(Text, nullable=False)
    visible_to_customer = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PortalNotification(Base):
    __tablename__ = "portal_notifications"

    id = Column(Integer, primary_key=True, index=True)
    portal_account_id = Column(Integer, ForeignKey("portal_accounts.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    notification_type = Column(String(40), nullable=False, default="system")
    status = Column(String(20), nullable=False, default="unread", index=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PortalActivityLog(Base):
    __tablename__ = "portal_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    portal_account_id = Column(Integer, ForeignKey("portal_accounts.id"), nullable=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    activity_type = Column(String(60), nullable=False)
    safe_summary = Column(Text, nullable=False)
    ip_address_hash = Column(String(64), nullable=True)
    user_agent_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)


class PortalPreference(Base):
    __tablename__ = "portal_preferences"

    id = Column(Integer, primary_key=True, index=True)
    portal_account_id = Column(Integer, ForeignKey("portal_accounts.id"), nullable=False, index=True)
    preference_key = Column(String(120), nullable=False)
    preference_value_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

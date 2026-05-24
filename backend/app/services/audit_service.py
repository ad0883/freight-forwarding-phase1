import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.audit import AuditLog


logger = logging.getLogger(__name__)

SENSITIVE_KEY_FRAGMENTS = {
    "access_token",
    "api_key",
    "authorization",
    "auth_code",
    "client_secret",
    "code_verifier",
    "cookie",
    "database_url",
    "env",
    "gmail_token",
    "hashed_password",
    "jwt",
    "oauth_code",
    "password",
    "refresh_token",
    "secret",
    "token",
}


def record_audit_log(
    db: Session,
    actor_user: Optional[AuthenticatedUser],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    entity_label: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> None:
    """Record a best-effort audit entry using sanitized, allowlisted metadata."""
    try:
        audit_log = AuditLog(
            actor_user_id=actor_user.id if actor_user else None,
            actor_name=actor_user.name if actor_user else None,
            actor_email=actor_user.email if actor_user else None,
            actor_role=actor_user.role if actor_user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=entity_label,
            description=description,
            metadata_json=sanitize_audit_metadata(metadata or {}),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
        db.add(audit_log)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Unable to record audit log action=%s entity_type=%s", action, entity_type)


def sanitize_audit_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        safe_key = str(key)
        if _is_sensitive_key(safe_key):
            sanitized[safe_key] = "[redacted]"
            continue
        sanitized[safe_key] = _safe_json_value(value)
    return sanitized


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(
        field
        for field, value in after.items()
        if field in before and _safe_json_value(before[field]) != _safe_json_value(value)
    )


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _safe_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return sanitize_audit_metadata(value)
    if isinstance(value, list):
        return [_safe_json_value(item) for item in value[:50]]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > 500:
            return f"{value[:500]}..."
        return value
    return str(value)


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return None


def _user_agent(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    value = request.headers.get("user-agent")
    if value and len(value) > 1000:
        return f"{value[:1000]}..."
    return value

from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Query, Session

from app.models.organization import Organization


DEFAULT_ORGANIZATION_NAME = "Default Freight Organization"
DEFAULT_ORGANIZATION_SLUG = "default-freight-organization"
DEFAULT_ORGANIZATION_TYPE = "freight_forwarder"


def get_or_create_default_organization(db: Session) -> Organization:
    organization = (
        db.query(Organization)
        .filter(Organization.slug == DEFAULT_ORGANIZATION_SLUG)
        .first()
    )
    if organization:
        return organization

    organization = Organization(
        name=DEFAULT_ORGANIZATION_NAME,
        slug=DEFAULT_ORGANIZATION_SLUG,
        org_type=DEFAULT_ORGANIZATION_TYPE,
        is_active=True,
    )
    db.add(organization)
    db.flush()
    return organization


def assign_default_organization(user, db: Session) -> None:
    if getattr(user, "organization_id", None):
        return
    organization = get_or_create_default_organization(db)
    user.organization_id = organization.id


def get_user_organization_id(user: Any) -> Optional[int]:
    return getattr(user, "organization_id", None)


def require_user_organization(user: Any) -> int:
    organization_id = get_user_organization_id(user)
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not linked to an organization",
        )
    return organization_id


def apply_organization_scope_if_supported(query: Query, model, user: Any) -> Query:
    organization_id = get_user_organization_id(user)
    if organization_id and hasattr(model, "organization_id"):
        return query.filter(model.organization_id == organization_id)
    return query

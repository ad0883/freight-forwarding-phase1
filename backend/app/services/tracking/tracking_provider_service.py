"""Tracking provider management service."""
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser
from app.models.tracking import TrackingAdapterConfig, TrackingProvider

logger = logging.getLogger(__name__)

DEFAULT_PROVIDERS = [
    {
        "provider_key": "manual_tracking",
        "name": "Manual Tracking",
        "provider_type": "manual",
        "is_manual": True,
        "is_mock": False,
        "supports_container_tracking": True,
        "supports_vessel_tracking": True,
        "supports_transport_tracking": True,
        "supports_terminal_tracking": True,
        "requires_credentials": False,
    },
    {
        "provider_key": "mock_shipping_line",
        "name": "Mock Shipping Line",
        "provider_type": "shipping_line",
        "is_manual": False,
        "is_mock": True,
        "supports_container_tracking": True,
        "supports_vessel_tracking": True,
        "supports_transport_tracking": False,
        "supports_terminal_tracking": False,
        "requires_credentials": False,
    },
    {
        "provider_key": "mock_vessel_schedule",
        "name": "Mock Vessel Schedule",
        "provider_type": "vessel_schedule",
        "is_manual": False,
        "is_mock": True,
        "supports_container_tracking": False,
        "supports_vessel_tracking": True,
        "supports_transport_tracking": False,
        "supports_terminal_tracking": False,
        "requires_credentials": False,
    },
    {
        "provider_key": "mock_terminal",
        "name": "Mock Terminal/CFS",
        "provider_type": "terminal",
        "is_manual": False,
        "is_mock": True,
        "supports_container_tracking": True,
        "supports_vessel_tracking": False,
        "supports_transport_tracking": False,
        "supports_terminal_tracking": True,
        "requires_credentials": False,
    },
    {
        "provider_key": "mock_transport_gps",
        "name": "Mock Transport GPS",
        "provider_type": "transport_gps",
        "is_manual": False,
        "is_mock": True,
        "supports_container_tracking": False,
        "supports_vessel_tracking": False,
        "supports_transport_tracking": True,
        "supports_terminal_tracking": False,
        "requires_credentials": False,
    },
]


def seed_default_tracking_providers(db: Session) -> None:
    """Seed default manual/mock tracking providers."""
    for prov_data in DEFAULT_PROVIDERS:
        existing = db.query(TrackingProvider).filter(
            TrackingProvider.provider_key == prov_data["provider_key"]
        ).first()
        if not existing:
            db.add(TrackingProvider(
                provider_key=prov_data["provider_key"],
                name=prov_data["name"],
                provider_type=prov_data["provider_type"],
                status="active",
                is_manual=prov_data["is_manual"],
                is_mock=prov_data["is_mock"],
                supports_container_tracking=prov_data["supports_container_tracking"],
                supports_vessel_tracking=prov_data["supports_vessel_tracking"],
                supports_transport_tracking=prov_data["supports_transport_tracking"],
                supports_terminal_tracking=prov_data["supports_terminal_tracking"],
                requires_credentials=prov_data["requires_credentials"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ))
    db.commit()


def list_tracking_providers(db: Session, *, status_filter: Optional[str] = None) -> list[TrackingProvider]:
    q = db.query(TrackingProvider)
    if status_filter:
        q = q.filter(TrackingProvider.status == status_filter)
    return q.order_by(TrackingProvider.created_at).all()


def get_tracking_provider(db: Session, provider_id: int) -> Optional[TrackingProvider]:
    return db.query(TrackingProvider).filter(TrackingProvider.id == provider_id).first()


def get_provider_by_key(db: Session, provider_key: str) -> Optional[TrackingProvider]:
    return db.query(TrackingProvider).filter(TrackingProvider.provider_key == provider_key).first()


def create_tracking_provider(db: Session, data: dict[str, Any], user: AuthenticatedUser) -> TrackingProvider:
    now = datetime.utcnow()
    provider = TrackingProvider(
        provider_key=data["provider_key"],
        name=data["name"],
        provider_type=data.get("provider_type", "other"),
        status=data.get("status", "active"),
        base_url=data.get("base_url"),
        supports_container_tracking=data.get("supports_container_tracking", False),
        supports_vessel_tracking=data.get("supports_vessel_tracking", False),
        supports_transport_tracking=data.get("supports_transport_tracking", False),
        supports_terminal_tracking=data.get("supports_terminal_tracking", False),
        requires_credentials=data.get("requires_credentials", False),
        is_manual=data.get("is_manual", False),
        is_mock=data.get("is_mock", False),
        created_at=now,
        updated_at=now,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def update_tracking_provider(db: Session, provider_id: int, data: dict[str, Any], user: AuthenticatedUser) -> TrackingProvider:
    provider = get_tracking_provider(db, provider_id)
    if not provider:
        raise ValueError("Tracking provider not found")
    updatable = ["name", "status", "base_url", "supports_container_tracking",
                 "supports_vessel_tracking", "supports_transport_tracking",
                 "supports_terminal_tracking", "requires_credentials"]
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(provider, field, data[field])
    provider.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(provider)
    return provider


def create_adapter_config(db: Session, provider_id: int, data: dict[str, Any], user: AuthenticatedUser) -> TrackingAdapterConfig:
    now = datetime.utcnow()
    config = TrackingAdapterConfig(
        tracking_provider_id=provider_id,
        config_name=data.get("config_name", "default"),
        status=data.get("status", "active"),
        auth_type=data.get("auth_type", "none"),
        safe_config_json=data.get("safe_config_json"),
        secret_ref=data.get("secret_ref"),
        created_by_user_id=user.id,
        created_by_name=user.name,
        created_at=now,
        updated_at=now,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

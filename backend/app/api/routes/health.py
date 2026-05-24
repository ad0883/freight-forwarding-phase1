from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.core.config import settings


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/details")
def health_details(
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> dict[str, object]:
    database_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_ok = False
    return {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "error",
        "gmail_enabled": settings.GMAIL_ENABLED,
        "ai_enabled": settings.AI_ENABLED,
        "ai_provider": settings.AI_PROVIDER,
        "environment": settings.ENVIRONMENT,
        "project": settings.PROJECT_NAME,
        "version": "phase-6",
    }

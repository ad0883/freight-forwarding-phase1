import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import (
    ai,
    alerts,
    admin,
    audit,
    auth,
    bl_management,
    demurrage,
    documents,
    email,
    exports,
    followups,
    health,
    notifications,
    parties,
    charges,
    reports,
    shipments,
    tasks,
    users,
)
from app.api.deps import AuthenticatedUser
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.indexes import ensure_performance_indexes
from app.db.schema import ensure_phase2_columns, ensure_phase35_columns
from app.db.session import Base, SessionLocal, engine
from app.models import User
from app.services.alert_service import create_overdue_task_alerts
from app.services.daily_summary_service import build_daily_summary
from app.services.dashboard_service import warm_dashboard_cache
from app.services.notification_service import seed_default_notification_rules
from app.services.workflow_notification_service import run_notification_checks


scheduler = BackgroundScheduler()


class OAuthCallbackAccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.args, tuple) or len(record.args) < 3:
            return True
        path = record.args[2]
        if not isinstance(path, str) or not path.startswith("/api/email/oauth/callback?"):
            return True
        args = list(record.args)
        args[2] = "/api/email/oauth/callback?[redacted]"
        record.args = tuple(args)
        return True


def install_access_log_filters() -> None:
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(log_filter, OAuthCallbackAccessLogFilter) for log_filter in access_logger.filters):
        access_logger.addFilter(OAuthCallbackAccessLogFilter())


install_access_log_filters()


def create_default_admin(db: Session) -> None:
    admin = db.query(User).filter(User.role == "ADMIN").first()
    if admin:
        return
    existing = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
    if existing:
        existing.name = settings.ADMIN_NAME
        existing.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
        existing.role = "ADMIN"
        existing.is_active = True
        db.commit()
        return
    db.add(
        User(
            name=settings.ADMIN_NAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            role="ADMIN",
            is_active=True,
        )
    )
    db.commit()


def run_alert_job() -> None:
    db = SessionLocal()
    try:
        create_overdue_task_alerts(db)
    finally:
        db.close()


def run_notification_checks_job() -> None:
    db = SessionLocal()
    try:
        run_notification_checks(db, source="scheduler")
    finally:
        db.close()


def run_daily_summary_job() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "ADMIN", User.is_active.is_(True)).first()
        if not admin:
            return
        build_daily_summary(
            db,
            AuthenticatedUser(
                id=admin.id,
                name=admin.name,
                email=admin.email,
                role=admin.role,
                is_active=admin.is_active,
                created_at=admin.created_at,
            ),
        )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
        ensure_phase2_columns(engine)
        ensure_phase35_columns(engine)
        ensure_performance_indexes(engine)
    db = SessionLocal()
    try:
        create_default_admin(db)
        seed_default_notification_rules(db)
        warm_dashboard_cache(db)
    finally:
        db.close()
    scheduler.add_job(run_alert_job, "cron", hour=7, minute=0, id="daily-overdue-alerts", replace_existing=True)
    scheduler.add_job(
        run_notification_checks_job,
        "interval",
        hours=1,
        id="hourly-notification-checks",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_summary_job,
        "cron",
        hour=9,
        minute=0,
        id="daily-operations-summary",
        replace_existing=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(parties.router, prefix="/api")
app.include_router(shipments.router, prefix="/api")
app.include_router(bl_management.router, prefix="/api")
app.include_router(demurrage.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(email.router, prefix="/api")
app.include_router(charges.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(followups.router, prefix="/api")


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "project": settings.PROJECT_NAME}

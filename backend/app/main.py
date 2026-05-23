from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.routes import ai, alerts, auth, documents, parties, shipments, tasks, users
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.indexes import ensure_performance_indexes
from app.db.session import Base, SessionLocal, engine
from app.models import User
from app.services.alert_service import create_overdue_task_alerts
from app.services.dashboard_service import warm_dashboard_cache


scheduler = BackgroundScheduler()


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
        ensure_performance_indexes(engine)
    db = SessionLocal()
    try:
        create_default_admin(db)
        warm_dashboard_cache(db)
    finally:
        db.close()
    scheduler.add_job(run_alert_job, "cron", hour=7, minute=0, id="daily-overdue-alerts", replace_existing=True)
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
app.include_router(users.router, prefix="/api")
app.include_router(parties.router, prefix="/api")
app.include_router(shipments.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "project": settings.PROJECT_NAME}

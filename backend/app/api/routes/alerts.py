from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertRead


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[Alert]:
    return db.query(Alert).order_by(Alert.is_read.asc(), Alert.created_at.desc()).all()

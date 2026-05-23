from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db
from app.models.alert import Alert
from app.schemas.alert import AlertRead


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(
    db: Session = Depends(get_db), _: AuthenticatedUser = Depends(get_current_user)
) -> list[Alert]:
    return db.query(Alert).order_by(Alert.is_read.asc(), Alert.created_at.desc()).all()

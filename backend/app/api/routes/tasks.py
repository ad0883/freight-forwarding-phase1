from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.alert import Alert
from app.models.shipment import Shipment
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.dashboard_service import invalidate_dashboard_cache


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(
    shipment_id: Optional[int] = None,
    include_cancelled: bool = False,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(get_current_user),
) -> list[Task]:
    query = db.query(Task)
    if shipment_id is not None:
        query = query.filter(Task.shipment_id == shipment_id)
    if not include_cancelled:
        query = query.filter(Task.status != "cancelled")
    return query.order_by(Task.status.asc(), Task.due_date.asc().nullslast(), Task.created_at.desc()).all()


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> Task:
    shipment = db.query(Shipment.id).filter(Shipment.id == task_in.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=400, detail="Shipment does not exist")
    if task_in.assigned_to is not None:
        user = db.query(User.id).filter(User.id == task_in.assigned_to).first()
        if not user:
            raise HTTPException(status_code=400, detail="Assigned user does not exist")
    task = Task(**task_in.model_dump(), auto_generated=False)
    db.add(task)
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache()
    return task


@router.patch("/{task_id}/cancel", response_model=TaskRead)
def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache()
    return task


@router.patch("/{task_id}/restore", response_model=TaskRead)
def restore_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "open"
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> None:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.auto_generated:
        raise HTTPException(
            status_code=400,
            detail="Auto-generated workflow tasks should be cancelled instead of deleted.",
        )
    if db.query(Alert.id).filter(Alert.task_id == task.id).first():
        raise HTTPException(
            status_code=400,
            detail="Task is referenced by alerts. Cancel it instead of deleting.",
        )
    db.delete(task)
    db.commit()
    invalidate_dashboard_cache()


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    _: AuthenticatedUser = Depends(require_write_access),
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = task_in.model_dump(exclude_unset=True)
    if data.get("assigned_to") is not None:
        user = db.query(User.id).filter(User.id == data["assigned_to"]).first()
        if not user:
            raise HTTPException(status_code=400, detail="Assigned user does not exist")
    for field, value in data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache()
    return task

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_current_user, get_db, require_write_access
from app.models.alert import Alert
from app.models.shipment import Shipment
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.audit_service import changed_fields, record_audit_log
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
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
    record_audit_log(
        db,
        current_user,
        "task.created",
        "task",
        entity_id=task.id,
        entity_label=task.title,
        description="Task created.",
        metadata={"shipment_id": task.shipment_id, "priority": task.priority, "status": task.status},
        request=request,
    )
    return task


@router.patch("/{task_id}/cancel", response_model=TaskRead)
def cancel_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "task.cancelled",
        "task",
        entity_id=task.id,
        entity_label=task.title,
        description="Task cancelled.",
        metadata={"shipment_id": task.shipment_id},
        request=request,
    )
    return task


@router.patch("/{task_id}/restore", response_model=TaskRead)
def restore_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "open"
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "task.restored",
        "task",
        entity_id=task.id,
        entity_label=task.title,
        description="Task restored.",
        metadata={"shipment_id": task.shipment_id, "status": task.status},
        request=request,
    )
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
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
    entity_label = task.title
    shipment_id = task.shipment_id
    db.delete(task)
    db.commit()
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "task.deleted",
        "task",
        entity_id=task_id,
        entity_label=entity_label,
        description="Task deleted.",
        metadata={"shipment_id": shipment_id},
        request=request,
    )


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_write_access),
) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = task_in.model_dump(exclude_unset=True)
    if data.get("assigned_to") is not None:
        user = db.query(User.id).filter(User.id == data["assigned_to"]).first()
        if not user:
            raise HTTPException(status_code=400, detail="Assigned user does not exist")
    before = {field: getattr(task, field, None) for field in data}
    for field, value in data.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    invalidate_dashboard_cache()
    record_audit_log(
        db,
        current_user,
        "task.updated",
        "task",
        entity_id=task.id,
        entity_label=task.title,
        description="Task updated.",
        metadata={"fields_changed": changed_fields(before, {field: getattr(task, field, None) for field in data})},
        request=request,
    )
    return task

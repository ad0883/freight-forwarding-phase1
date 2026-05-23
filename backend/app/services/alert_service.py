from datetime import date

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.task import Task


def create_overdue_task_alerts(db: Session) -> int:
    today = date.today()
    overdue_tasks = (
        db.query(Task)
        .filter(Task.status == "open", Task.due_date.isnot(None), Task.due_date < today)
        .all()
    )
    created = 0
    for task in overdue_tasks:
        existing = db.query(Alert).filter(Alert.task_id == task.id).first()
        if existing:
            continue
        db.add(
            Alert(
                shipment_id=task.shipment_id,
                task_id=task.id,
                title="Overdue task",
                message=f"Task '{task.title}' is overdue.",
                priority="warning",
            )
        )
        created += 1
    if created:
        db.commit()
    return created

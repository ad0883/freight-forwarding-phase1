from enum import Enum


class OperationalEventType(str, Enum):
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_UPDATED = "shipment.updated"
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    CHARGE_CREATED = "charge.created"
    DOCUMENT_UPDATED = "document.updated"


def record_operational_event(*args, **kwargs):
    return None

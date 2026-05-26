"""Phase 10 best-effort state inference for legacy shipments."""
from typing import Optional

from app.models.shipment import Shipment


COMPLETED_STATUSES = {"completed", "Completed", "Closed", "closed"}


def infer_workflow_state_for_shipment(shipment: Shipment) -> Optional[str]:
    if shipment is None:
        return None
    flow = (shipment.type or "").lower()
    status_value = shipment.status or ""
    if flow == "export":
        return _infer_export(shipment, status_value)
    if flow == "import":
        return _infer_import(shipment, status_value)
    return None


def _infer_export(shipment: Shipment, status_value: str) -> str:
    bl = getattr(shipment, "bl_management", None)
    if status_value in COMPLETED_STATUSES or status_value == "Completed":
        return "EXPORT_COMPLETED"
    if bl is not None and getattr(bl, "final_received", None):
        return "FINAL_BL_RECEIVED"
    if bl is not None and getattr(bl, "approval_date", None):
        return "BL_APPROVED"
    if bl is not None and getattr(bl, "draft_received", None):
        return "BL_DRAFT_RECEIVED"
    if status_value in {"Loaded on Vessel", "Vessel Sailed"}:
        return "LOADED_ON_VESSEL"
    if shipment.booking_ref or status_value in {"Booking Received", "Container Booked"}:
        return "EXPORT_BOOKING_CONFIRMED"
    return "EXPORT_SHIPMENT_CREATED"


def _infer_import(shipment: Shipment, status_value: str) -> str:
    if status_value in COMPLETED_STATUSES:
        return "IMPORT_COMPLETED"
    if status_value in {"Container Delivered", "Freight Collected"}:
        return "CONTAINER_DELIVERED"
    if status_value in {"OOC Received"}:
        return "OOC_RECEIVED"
    if shipment.do_received_date or status_value == "DO Received":
        return "DO_RECEIVED"
    if shipment.eta or status_value == "ETA Tracking Active":
        return "ETA_TRACKING_ACTIVE"
    if shipment.shipment_code or status_value == "Pre-Alert Received":
        return "IMPORT_SHIPMENT_CREATED"
    return "IMPORT_PRE_ALERT_PENDING"

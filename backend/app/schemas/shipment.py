from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ContainerType, ShipmentStatus, ShipmentType
from app.schemas.alert import AlertRead
from app.schemas.party import PartyRead


class ShipmentBase(BaseModel):
    type: ShipmentType
    exporter_id: Optional[int] = None
    importer_id: Optional[int] = None
    shipping_line: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_no: Optional[str] = None
    origin_port: Optional[str] = None
    dest_port: Optional[str] = None
    container_no: Optional[str] = None
    container_type: Optional[ContainerType] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    vgm_cutoff_date: Optional[date] = None
    bl_cutoff_date: Optional[date] = None
    si_cutoff_date: Optional[date] = None
    do_received_date: Optional[date] = None
    container_delivered_date: Optional[date] = None
    bl_number: Optional[str] = None
    booking_ref: Optional[str] = None
    commodity: Optional[str] = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentUpdate(BaseModel):
    status: Optional[ShipmentStatus] = None
    exporter_id: Optional[int] = None
    importer_id: Optional[int] = None
    shipping_line: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_no: Optional[str] = None
    origin_port: Optional[str] = None
    dest_port: Optional[str] = None
    container_no: Optional[str] = None
    container_type: Optional[ContainerType] = None
    etd: Optional[date] = None
    eta: Optional[date] = None
    vgm_cutoff_date: Optional[date] = None
    bl_cutoff_date: Optional[date] = None
    si_cutoff_date: Optional[date] = None
    do_received_date: Optional[date] = None
    container_delivered_date: Optional[date] = None
    bl_number: Optional[str] = None
    booking_ref: Optional[str] = None
    commodity: Optional[str] = None


class ShipmentRead(ShipmentBase):
    id: int
    shipment_code: str
    status: ShipmentStatus
    created_at: datetime
    created_by: int
    exporter: Optional[PartyRead] = None
    importer: Optional[PartyRead] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardSummary(BaseModel):
    live_shipments: int
    pending_tasks: int
    future_bookings: int
    alerts_today: int
    completed_this_month: int
    shipments: list[ShipmentRead]
    recent_alerts: list[AlertRead]
    urgent_tasks: list["TaskRead"] = Field(default_factory=list)


class WorkflowStatusUpdate(BaseModel):
    status: str


from app.schemas.task import TaskRead

DashboardSummary.model_rebuild()

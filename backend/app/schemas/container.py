from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ContainerStatus = str  # one of the canonical statuses; validated server-side
ContainerEventSource = Literal[
    "user",
    "system",
    "gmail",
    "workflow",
    "tracking",
    "transport",
    "line",
    "cha",
]
RiskLevel = Literal["none", "info", "warning", "critical", "running"]
ExposureRecordStatus = Literal["estimated", "running", "finalized", "waived", "not_applicable"]


class ContainerBase(BaseModel):
    container_number: str = Field(min_length=4, max_length=20)
    container_size: Optional[str] = Field(default=None, max_length=10)
    container_type: Optional[str] = Field(default=None, max_length=20)
    soc_coc: Optional[str] = Field(default=None, max_length=10)
    seal_number: Optional[str] = Field(default=None, max_length=40)
    gross_weight: Optional[Decimal] = None
    tare_weight: Optional[Decimal] = None
    package_count: Optional[int] = None
    current_status: Optional[str] = Field(default=None, max_length=60)
    current_location: Optional[str] = Field(default=None, max_length=150)

    planned_date: Optional[date] = None
    empty_release_date: Optional[date] = None
    empty_pickup_date: Optional[date] = None
    factory_arrival_date: Optional[date] = None
    stuffing_start_date: Optional[date] = None
    stuffing_completed_date: Optional[date] = None
    sealed_date: Optional[date] = None
    gate_in_date: Optional[date] = None
    loaded_on_vessel_date: Optional[date] = None
    departed_date: Optional[date] = None

    expected_arrival_date: Optional[date] = None
    discharge_date: Optional[date] = None
    do_received_date: Optional[date] = None
    gate_out_date: Optional[date] = None
    delivery_date: Optional[date] = None
    empty_return_deadline: Optional[date] = None
    empty_return_date: Optional[date] = None

    demurrage_free_days: Optional[int] = Field(default=None, ge=0, le=365)
    detention_free_days: Optional[int] = Field(default=None, ge=0, le=365)
    demurrage_start_date: Optional[date] = None
    demurrage_end_date: Optional[date] = None
    detention_start_date: Optional[date] = None
    detention_end_date: Optional[date] = None
    metadata_json: Optional[dict[str, Any]] = None


class ContainerCreate(ContainerBase):
    pass


class ContainerUpdate(BaseModel):
    container_number: Optional[str] = Field(default=None, min_length=4, max_length=20)
    container_size: Optional[str] = Field(default=None, max_length=10)
    container_type: Optional[str] = Field(default=None, max_length=20)
    soc_coc: Optional[str] = Field(default=None, max_length=10)
    seal_number: Optional[str] = Field(default=None, max_length=40)
    gross_weight: Optional[Decimal] = None
    tare_weight: Optional[Decimal] = None
    package_count: Optional[int] = None
    current_status: Optional[str] = Field(default=None, max_length=60)
    current_location: Optional[str] = Field(default=None, max_length=150)
    is_active: Optional[bool] = None

    planned_date: Optional[date] = None
    empty_release_date: Optional[date] = None
    empty_pickup_date: Optional[date] = None
    factory_arrival_date: Optional[date] = None
    stuffing_start_date: Optional[date] = None
    stuffing_completed_date: Optional[date] = None
    sealed_date: Optional[date] = None
    gate_in_date: Optional[date] = None
    loaded_on_vessel_date: Optional[date] = None
    departed_date: Optional[date] = None

    expected_arrival_date: Optional[date] = None
    discharge_date: Optional[date] = None
    do_received_date: Optional[date] = None
    gate_out_date: Optional[date] = None
    delivery_date: Optional[date] = None
    empty_return_deadline: Optional[date] = None
    empty_return_date: Optional[date] = None
    closed_at: Optional[datetime] = None

    demurrage_free_days: Optional[int] = Field(default=None, ge=0, le=365)
    detention_free_days: Optional[int] = Field(default=None, ge=0, le=365)
    demurrage_start_date: Optional[date] = None
    demurrage_end_date: Optional[date] = None
    detention_start_date: Optional[date] = None
    detention_end_date: Optional[date] = None
    metadata_json: Optional[dict[str, Any]] = None


class ContainerExposureRead(BaseModel):
    container_id: int
    shipment_id: int
    currency: str = "INR"
    demurrage_days_used: int = 0
    demurrage_chargeable_days: int = 0
    demurrage_estimated_amount: Decimal = Decimal("0")
    demurrage_status: ExposureRecordStatus = "not_applicable"
    demurrage_start_date: Optional[date] = None
    demurrage_end_date: Optional[date] = None
    detention_days_used: int = 0
    detention_chargeable_days: int = 0
    detention_estimated_amount: Decimal = Decimal("0")
    detention_status: ExposureRecordStatus = "not_applicable"
    detention_start_date: Optional[date] = None
    detention_end_date: Optional[date] = None
    risk_level: RiskLevel = "none"


class ContainerRead(ContainerBase):
    id: int
    shipment_id: int
    shipment_code: Optional[str] = None
    is_active: bool = True
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    exposure: Optional[ContainerExposureRead] = None

    model_config = ConfigDict(from_attributes=True)


class ContainerEventRead(BaseModel):
    id: int
    container_id: int
    shipment_id: int
    event_type: str
    event_date: Optional[date] = None
    location: Optional[str] = None
    source: ContainerEventSource
    description: Optional[str] = None
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContainerEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=60)
    event_date: Optional[date] = None
    location: Optional[str] = Field(default=None, max_length=150)
    description: Optional[str] = Field(default=None, max_length=500)
    source: ContainerEventSource = "user"
    metadata_json: Optional[dict[str, Any]] = None


class ContainerTransitionRequest(BaseModel):
    new_status: str = Field(min_length=2, max_length=60)
    reason: Optional[str] = Field(default=None, max_length=500)
    event_date: Optional[date] = None


class ContainerBackfillRequest(BaseModel):
    dry_run: bool = True


class ContainerBackfillCandidate(BaseModel):
    shipment_id: int
    shipment_code: str
    container_numbers: list[str]
    container_size: Optional[str] = None
    container_type: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class ContainerBackfillResponse(BaseModel):
    dry_run: bool
    candidates: list[ContainerBackfillCandidate]
    created_count: int = 0


class ShipmentExposureSummary(BaseModel):
    shipment_id: int
    container_count: int
    currency: str = "INR"
    demurrage_estimated_amount: Decimal = Decimal("0")
    detention_estimated_amount: Decimal = Decimal("0")
    demurrage_running: int = 0
    detention_running: int = 0
    empty_return_overdue: int = 0
    risk_level: RiskLevel = "none"
    containers: list[ContainerExposureRead] = Field(default_factory=list)


class ContainerRiskRow(BaseModel):
    shipment_id: int
    shipment_code: str
    container_id: int
    container_number: str
    current_status: str
    demurrage_status: ExposureRecordStatus
    demurrage_estimated_amount: Decimal
    detention_status: ExposureRecordStatus
    detention_estimated_amount: Decimal
    empty_return_deadline: Optional[date] = None
    risk_level: RiskLevel

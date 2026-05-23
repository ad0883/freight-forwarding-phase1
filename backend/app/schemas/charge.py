from datetime import date as Date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import ChargeDirection, ChargeStatus, ChargeType, ShipmentType


VALID_STATUS_BY_DIRECTION = {
    "payable": {"pending", "paid", "cancelled"},
    "receivable": {"pending", "received", "cancelled"},
}


def is_valid_charge_status(direction: str, status: str) -> bool:
    return status in VALID_STATUS_BY_DIRECTION.get(direction, set())


class ChargeBase(BaseModel):
    charge_type: ChargeType
    direction: ChargeDirection
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="INR", min_length=1, max_length=10)
    party_id: Optional[int] = None
    status: ChargeStatus = "pending"
    invoice_no: Optional[str] = None
    date: Optional[Date] = None
    notes: Optional[str] = None


class ChargeCreate(ChargeBase):
    shipment_id: Optional[int] = None


class ChargeUpdate(BaseModel):
    charge_type: Optional[ChargeType] = None
    direction: Optional[ChargeDirection] = None
    amount: Optional[Decimal] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=1, max_length=10)
    party_id: Optional[int] = None
    status: Optional[ChargeStatus] = None
    invoice_no: Optional[str] = None
    date: Optional[Date] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def normalize_currency(self):
        if self.currency:
            self.currency = self.currency.upper()
        return self


class ChargeRead(ChargeBase):
    id: int
    shipment_id: int
    shipment_code: Optional[str] = None
    party_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShipmentPLSummary(BaseModel):
    shipment_id: int
    shipment_code: str
    currency: str
    total_payable: Decimal
    total_receivable: Decimal
    total_paid: Decimal
    total_received: Decimal
    pending_payable: Decimal
    pending_receivable: Decimal
    net_profit: Decimal
    charge_count: int
    multiple_currencies: bool


class DashboardFinancialSummary(BaseModel):
    pending_receivables: Decimal
    pending_payables: Decimal
    this_month_receivables: Decimal
    this_month_payables: Decimal
    this_month_profit: Decimal
    currency: str
    multiple_currencies: bool


class MonthlyReportSummary(BaseModel):
    month: int
    year: int
    shipment_count: int
    completed_shipments: int
    total_receivable: Decimal
    total_payable: Decimal
    net_profit: Decimal
    pending_receivable: Decimal
    pending_payable: Decimal
    currency: str
    multiple_currencies: bool


class PendingChargeReportRow(BaseModel):
    charge_id: int
    shipment_id: int
    shipment_code: str
    party_name: Optional[str] = None
    amount: Decimal
    currency: str
    invoice_no: Optional[str] = None
    date: Optional[Date] = None
    notes: Optional[str] = None


class ShipmentPLReportRow(BaseModel):
    shipment_id: int
    shipment_code: str
    type: ShipmentType
    status: str
    total_receivable: Decimal
    total_payable: Decimal
    net_profit: Decimal
    pending_receivable: Decimal
    pending_payable: Decimal
    currency: str
    multiple_currencies: bool

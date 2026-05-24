from typing import Literal


Role = Literal["ADMIN", "STAFF", "VIEW_ONLY"]
PartyType = Literal[
    "exporter",
    "importer",
    "cha",
    "overseas_ff",
    "line",
    "courier",
    "buyer",
    "other",
]
ShipmentType = Literal["export", "import"]
ExportWorkflowStatus = Literal[
    "Booking Received",
    "Container Booked",
    "SI Submitted",
    "VGM Filed",
    "BL Draft Received",
    "BL Approved",
    "Final BL Received",
    "Docs Collected",
    "Docs Dispatched",
    "Overseas Coordinated",
    "Freight Invoiced",
    "Vessel Sailed",
    "Completed",
]
ImportWorkflowStatus = Literal[
    "Pre-Alert Received",
    "ETA Tracking Active",
    "IGM Filed",
    "Freight Invoice Received",
    "BL Surrender Confirmed",
    "DO Received",
    "DO Handed to CHA",
    "Clearance In Progress",
    "Container Delivered",
    "Freight Collected",
    "Completed",
]
ShipmentStatus = str
ContainerType = Literal["20GP", "40GP", "40HC", "LCL"]
DocumentStatus = Literal["pending", "received", "sent", "approved", "not_required"]
Priority = Literal["critical", "warning", "info"]
TaskStatus = Literal["open", "done", "cancelled"]
FollowUpChannel = Literal["email", "call", "whatsapp", "meeting"]
FollowUpStatus = Literal["open", "closed"]
BLType = Literal["OBL", "HBL", "Surrender", "Telex", "Seaway", "Ocean"]
DemurrageStatus = Literal["within_free_days", "expiring_soon", "running", "not_started"]
ChargeType = Literal[
    "ocean_freight",
    "do_charges",
    "bl_charges",
    "hbl_charges",
    "liner_charges",
    "clearance_charges",
    "courier_charges",
    "agent_charges",
    "demurrage",
    "documentation",
    "handling",
    "transport",
    "other",
]
ChargeDirection = Literal["payable", "receivable"]
ChargeStatus = Literal["pending", "paid", "received", "cancelled"]
EmailClassification = Literal[
    "booking_confirmation",
    "bl_draft",
    "arrival_notice",
    "freight_invoice",
    "delivery_order",
    "pre_alert",
    "general_followup",
    "unknown",
]
EmailProcessedStatus = Literal["new", "suggested", "approved", "rejected", "ignored"]
EmailSuggestionType = Literal[
    "update_shipment",
    "update_document",
    "update_bl",
    "update_demurrage",
    "create_charge",
    "create_followup",
    "create_task",
    "unknown",
]
EmailSuggestionStatus = Literal["pending", "approved", "rejected", "applied", "ignored"]

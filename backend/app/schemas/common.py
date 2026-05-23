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
ShipmentStatus = Literal["active", "completed", "cancelled"]
ContainerType = Literal["20GP", "40GP", "40HC", "LCL"]
DocumentStatus = Literal["pending", "received", "sent", "approved", "not_required"]
Priority = Literal["critical", "warning", "info"]
TaskStatus = Literal["open", "done"]
FollowUpChannel = Literal["email", "call", "whatsapp", "meeting"]
FollowUpStatus = Literal["open", "closed"]

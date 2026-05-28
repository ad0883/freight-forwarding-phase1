"""Tracking normalization service — maps raw external statuses to internal canonical statuses."""
from typing import Optional

# Raw status → normalized internal status mapping
STATUS_NORMALIZATION_MAP: dict[str, str] = {
    # Gate events
    "gate in": "gate_in",
    "gate_in": "gate_in",
    "in_gate": "gate_in",
    "gated in": "gate_in",
    "gate out": "gate_out",
    "gate_out": "gate_out",
    "out_gate": "gate_out",
    "gated out": "gate_out",
    # Loading
    "loaded": "loaded_on_vessel",
    "loaded on vessel": "loaded_on_vessel",
    "on board": "loaded_on_vessel",
    "onboard": "loaded_on_vessel",
    # Discharge
    "discharged": "discharged",
    "discharge": "discharged",
    "unloaded": "discharged",
    # Departure
    "departed": "departed",
    "vessel departed": "departed",
    "sailed": "departed",
    # Arrival
    "arrived": "arrived",
    "vessel arrived": "arrived",
    "berthed": "arrived",
    # Delivery
    "delivered": "delivered",
    "delivery": "delivered",
    "cargo delivered": "delivered",
    # Empty return
    "empty returned": "empty_returned",
    "empty return": "empty_returned",
    "returned empty": "empty_returned",
    # Transit
    "in transit": "in_transit",
    "in_transit": "in_transit",
    "on rail": "in_transit",
    "on road": "in_transit",
    # Stuffing
    "stuffed": "stuffing_completed",
    "stuffing completed": "stuffing_completed",
    # Customs
    "customs cleared": "customs_cleared",
    "ooc": "customs_cleared",
    "leo": "customs_cleared",
    # Other
    "unknown": "unknown",
}


def normalize_tracking_status(raw_status: str, provider_type: str = "other") -> str:
    """Normalize a raw tracking status to internal canonical form."""
    if not raw_status:
        return "unknown"
    key = raw_status.strip().lower()
    return STATUS_NORMALIZATION_MAP.get(key, key.replace(" ", "_").replace("-", "_"))


def normalize_location(raw_location: "Optional[str]") -> "Optional[str]":
    """Normalize location text (trim, title-case)."""
    if not raw_location:
        return None
    return raw_location.strip().title()


def map_observation_to_event_key(normalized_status: str) -> str:
    """Map a normalized status to an event key for the tracking events table."""
    return normalized_status

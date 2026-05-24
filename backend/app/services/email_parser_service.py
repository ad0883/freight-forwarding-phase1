import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional


CLASSIFICATION_KEYWORDS = {
    "booking_confirmation": [
        "booking confirmation",
        "booking ref",
        "booking reference",
        "vessel",
        "voyage",
        "etd",
    ],
    "bl_draft": ["bl draft", "bill of lading draft", "draft bl", "hbl", "mbl"],
    "arrival_notice": ["arrival notice", "eta", "igm", "destination arrival"],
    "freight_invoice": [
        "freight invoice",
        "invoice amount",
        "payable",
        "due amount",
        "total amount",
    ],
    "delivery_order": ["delivery order", "do release", "do ready", "delivery order ready"],
    "pre_alert": ["pre-alert", "pre alert", "prealert", "documents attached"],
}


def parse_email(subject: Optional[str], snippet: Optional[str], body_preview: Optional[str]) -> dict[str, Any]:
    text = "\n".join(part for part in [subject, snippet, body_preview] if part)
    classification = classify_email(text)
    extracted = extract_fields(text)
    extracted["classification"] = classification
    if classification == "freight_invoice" and "direction" not in extracted:
        extracted["direction"] = "payable"
    if classification == "freight_invoice" and "charge_type" not in extracted:
        extracted["charge_type"] = "ocean_freight"
    if classification in {"bl_draft", "arrival_notice", "delivery_order", "pre_alert"}:
        extracted.setdefault("document_status", "received")
    return {"classification": classification, "extracted_data": extracted}


def classify_email(text: str) -> str:
    normalized = text.lower()
    scores = {
        classification: sum(1 for keyword in keywords if keyword in normalized)
        for classification, keywords in CLASSIFICATION_KEYWORDS.items()
    }
    best_classification, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score:
        return best_classification
    if any(keyword in normalized for keyword in ["shipment", "container", "cargo", "consignment"]):
        return "general_followup"
    return "unknown"


def extract_fields(text: str) -> dict[str, Any]:
    extracted: dict[str, Any] = {}
    patterns = {
        "shipment_code": r"\bFF-(?:EXP|IMP)-\d{4}-\d{3,}\b",
        "container_no": r"\b[A-Z]{4}\d{7}\b",
    }
    for field, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            extracted[field] = match.group(0).upper()
    labeled_patterns = {
        "booking_ref": r"(?:booking\s*(?:ref|reference|no|number)\s*[:#-]?\s*)([A-Z0-9][A-Z0-9/-]{3,})",
        "bl_number": r"(?:(?:hbl|mbl|bl|bill of lading)\s*(?:no|number)?\s*[:#-]?\s*)([A-Z0-9][A-Z0-9/-]{3,})",
        "vessel_name": r"(?:vessel\s*[:#-]?\s*)([A-Z][A-Z0-9 .'-]{2,})",
        "voyage_no": r"(?:voyage\s*(?:no|number)?\s*[:#-]?\s*)([A-Z0-9/-]{2,})",
        "origin_port": r"(?:(?:origin|pol|load port)\s*[:#-]?\s*)([A-Z][A-Z .'-]{2,})",
        "dest_port": r"(?:(?:destination|pod|discharge port)\s*[:#-]?\s*)([A-Z][A-Z .'-]{2,})",
    }
    for field, pattern in labeled_patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            extracted[field] = _clean_value(match.group(1))
    invoice_no = _extract_invoice_no(text)
    if invoice_no:
        extracted["invoice_no"] = invoice_no
    for field in ["etd", "eta"]:
        value = _extract_labeled_date(text, field.upper())
        if value:
            extracted[field] = value.isoformat()
    amount = _extract_amount(text)
    if amount:
        extracted.update(amount)
    bl_type = _extract_bl_type(text)
    if bl_type:
        extracted["bl_type"] = bl_type
    return extracted


def _extract_invoice_no(text: str) -> Optional[str]:
    patterns = [
        r"\b(?:invoice|inv)\s*(?:no\.?|number|#)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/-]{2,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        invoice_no = _clean_value(match.group(1)).upper()
        if invoice_no.lower() not in {"for", "the", "and", "with", "from"}:
            return invoice_no
    return None


def build_suggestions_for_classification(
    classification: str,
    extracted_data: dict[str, Any],
    received_at: Optional[datetime],
) -> list[dict[str, Any]]:
    today = (received_at.date() if received_at else date.today()).isoformat()
    suggestions: list[dict[str, Any]] = []
    if classification == "booking_confirmation":
        fields = _subset(
            extracted_data,
            [
                "booking_ref",
                "vessel_name",
                "voyage_no",
                "origin_port",
                "dest_port",
                "etd",
                "shipping_line",
            ],
        )
        if fields:
            suggestions.append({"suggestion_type": "update_shipment", "data": fields})
    elif classification == "bl_draft":
        suggestions.append(
            {
                "suggestion_type": "update_document",
                "data": {"doc_type": "BL_DRAFT", "status": "received", "date_received": today},
            }
        )
        bl_data = {"draft_received": today}
        if extracted_data.get("bl_type"):
            bl_data["bl_type"] = extracted_data["bl_type"]
        suggestions.append({"suggestion_type": "update_bl", "data": bl_data})
    elif classification == "arrival_notice":
        update_data = _subset(extracted_data, ["eta"])
        if update_data:
            update_data["status"] = "ETA Tracking Active"
            suggestions.append({"suggestion_type": "update_shipment", "data": update_data})
        suggestions.append(
            {
                "suggestion_type": "update_document",
                "data": {"doc_type": "ARRIVAL_NOTICE", "status": "received", "date_received": today},
            }
        )
        suggestions.append(
            {
                "suggestion_type": "create_task",
                "data": {
                    "title": "Follow up for DO / clearance",
                    "description": "Suggested from arrival notice email.",
                    "priority": "warning",
                    "status": "open",
                },
            }
        )
    elif classification == "freight_invoice":
        data = _subset(extracted_data, ["amount", "currency", "invoice_no", "direction", "charge_type"])
        if "amount" in data:
            data.setdefault("currency", "INR")
            data.setdefault("direction", "payable")
            data.setdefault("charge_type", "ocean_freight")
            data["status"] = "pending"
            data["date"] = today
            data["notes"] = "Suggested from freight invoice email."
            suggestions.append({"suggestion_type": "create_charge", "data": data})
        suggestions.append(
            {
                "suggestion_type": "update_document",
                "data": {"doc_type": "FREIGHT_INVOICE", "status": "received", "date_received": today},
            }
        )
    elif classification == "delivery_order":
        suggestions.append(
            {
                "suggestion_type": "update_document",
                "data": {"doc_type": "DO", "status": "received", "date_received": today},
            }
        )
        suggestions.append(
            {
                "suggestion_type": "update_shipment",
                "data": {"status": "DO Received", "do_received_date": today},
            }
        )
        suggestions.append({"suggestion_type": "update_demurrage", "data": {"start_date": today}})
    elif classification == "pre_alert":
        suggestions.append(
            {
                "suggestion_type": "update_document",
                "data": {"doc_type": "PRE_ALERT", "status": "received", "date_received": today},
            }
        )
        suggestions.append(
            {
                "suggestion_type": "create_followup",
                "data": {
                    "channel": "email",
                    "summary": "Pre-alert email received.",
                    "next_action": extracted_data.get("next_action"),
                    "status": "open",
                    "date": today,
                },
            }
        )
    elif classification == "general_followup":
        suggestions.append(
            {
                "suggestion_type": "create_followup",
                "data": {
                    "channel": "email",
                    "summary": "Freight-related email received.",
                    "status": "open",
                    "date": today,
                },
            }
        )
    return suggestions


def _extract_amount(text: str) -> Optional[dict[str, Any]]:
    amount_patterns = [
        r"\b(INR|USD|EUR|GBP|AED)\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        r"([₹$€£])\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        r"(?:amount|total|due amount|invoice amount)\s*[:#-]?\s*(?:INR|Rs\.?|₹)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
    ]
    symbol_currency = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}
    for pattern in amount_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        if len(match.groups()) == 2:
            currency_or_symbol, raw_amount = match.groups()
            currency = symbol_currency.get(currency_or_symbol, currency_or_symbol.upper())
        else:
            raw_amount = match.group(1)
            currency = "INR"
        amount = Decimal(raw_amount.replace(",", ""))
        return {"amount": str(amount), "currency": currency}
    return None


def _extract_labeled_date(text: str, label: str) -> Optional[date]:
    match = re.search(rf"{label}\s*[:#-]?\s*([0-9]{{1,2}}[/-][0-9]{{1,2}}[/-][0-9]{{2,4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})", text, re.IGNORECASE)
    if not match:
        return None
    return _parse_date(match.group(1))


def _parse_date(value: str) -> Optional[date]:
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _extract_bl_type(text: str) -> Optional[str]:
    normalized = text.lower()
    if "telex" in normalized:
        return "Telex"
    if "surrender" in normalized:
        return "Surrender"
    if "seaway" in normalized or "sea way" in normalized:
        return "Seaway"
    if "hbl" in normalized:
        return "HBL"
    if "obl" in normalized or "original bl" in normalized:
        return "OBL"
    return None


def _subset(data: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: data[key] for key in keys if data.get(key) not in (None, "")}


def _clean_value(value: str) -> str:
    return value.strip().splitlines()[0].strip(" .,:;-")

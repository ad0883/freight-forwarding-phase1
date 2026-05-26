"""Deterministic email parser used by Phase 5/9.1.

Phase 9.1 hardens classification and field extraction so non-freight emails
(IRCTC, Shopify, newsletters, promos) do not show up as freight suggestions
and so token-like strings cannot be saved as BL numbers.
"""
import math
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional


CLASSIFICATION_KEYWORDS = {
    "booking_confirmation": [
        "freight booking confirmation",
        "shipping booking",
        "vessel booking",
        "container booking",
        "ocean booking",
        "sea booking",
        "booking ref",
        "booking reference",
        "vessel",
        "voyage",
        "etd",
    ],
    "bl_draft": [
        "bl draft",
        "bill of lading draft",
        "draft bl",
        "hbl draft",
        "mbl draft",
    ],
    "arrival_notice": [
        "arrival notice",
        "notice of arrival",
        "vessel arrival",
        "igm filed",
        "destination arrival",
    ],
    "freight_invoice": [
        "freight invoice",
        "ocean freight invoice",
        "shipping invoice",
        "carrier invoice",
        "do invoice",
    ],
    "delivery_order": [
        "delivery order",
        "do release",
        "do ready",
        "delivery order ready",
    ],
    "pre_alert": [
        "pre-alert",
        "pre alert",
        "prealert",
        "pre-shipment alert",
    ],
}

# Senders/keywords that should never become freight actions on their own.
NON_FREIGHT_SENDER_DOMAINS = {
    "irctc.co.in",
    "easemytrip.com",
    "makemytrip.com",
    "yatra.com",
    "amazon.in",
    "amazon.com",
    "myntra.com",
    "flipkart.com",
    "shopify.com",
    "ajio.com",
    "swiggy.in",
    "zomato.com",
    "noreply.youtube.com",
    "elfsight.com",
    "mailchimp.com",
    "substack.com",
    "newsletter.medium.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "google.com",
    "github.com",
}

NON_FREIGHT_KEYWORDS = [
    "irctc",
    "train ticket",
    "train booking",
    "flight booking",
    "hotel booking",
    "your order",
    "order shipped",
    "delivery update",
    "delivery confirmation",
    "track your package",
    "track your order",
    "your package",
    "newsletter",
    "promotion",
    "promo code",
    "discount",
    "% off",
    "deal of the day",
    "verify your account",
    "password reset",
    "otp ",
    "one time password",
    "subscribe",
    "unsubscribe",
    "social",
    "stories",
    "feed",
]

FREIGHT_HARD_TERMS = [
    "shipment",
    "shipper",
    "consignee",
    "consignor",
    "consignment",
    "container",
    "containerised",
    "containerized",
    "vessel",
    "voyage",
    "manifest",
    "freight",
    "ocean freight",
    "air freight",
    "cargo",
    "bill of lading",
    "bl no",
    "bl number",
    "house bl",
    "master bl",
    "demurrage",
    "detention",
    "shipping line",
    "incoterm",
    "fob",
    "cif",
    "ddp",
    "exw",
    "customs",
    "stuffing",
    "loading port",
    "discharge port",
    "pol",
    "pod",
    "letter of credit",
    "lc number",
    "freight forwarder",
    "ff-exp",
    "ff-imp",
]

CONFIDENCE_NO_SHIPMENT_THRESHOLD = 0.7


def parse_email(
    subject: Optional[str],
    snippet: Optional[str],
    body_preview: Optional[str],
    *,
    sender: Optional[str] = None,
) -> dict[str, Any]:
    text = "\n".join(part for part in [subject, snippet, body_preview] if part)
    classification = classify_email(text, sender=sender)
    extracted = extract_fields(text)
    extracted["classification"] = classification
    if classification == "freight_invoice" and "direction" not in extracted:
        extracted["direction"] = "payable"
    if classification == "freight_invoice" and "charge_type" not in extracted:
        extracted["charge_type"] = "ocean_freight"
    if classification in {"bl_draft", "arrival_notice", "delivery_order", "pre_alert"}:
        extracted.setdefault("document_status", "received")
    return {"classification": classification, "extracted_data": extracted}


def is_non_freight_sender(sender: Optional[str], text: str) -> bool:
    if sender:
        sender_normalized = sender.lower()
        for domain in NON_FREIGHT_SENDER_DOMAINS:
            if domain in sender_normalized:
                return True
    text_normalized = text.lower()
    return any(keyword in text_normalized for keyword in NON_FREIGHT_KEYWORDS)


def has_freight_signal(text: str) -> bool:
    normalized = text.lower()
    if any(term in normalized for term in FREIGHT_HARD_TERMS):
        return True
    if re.search(r"\bFF-(?:EXP|IMP)-\d{4}-\d{3,}\b", text, re.IGNORECASE):
        return True
    if re.search(r"\b[A-Z]{4}\d{7}\b", text):
        return True
    return False


def classify_email(text: str, *, sender: Optional[str] = None) -> str:
    normalized = text.lower()
    non_freight = is_non_freight_sender(sender, text)
    freight_signal = has_freight_signal(text)
    if non_freight and not freight_signal:
        return "unknown"

    scores = {
        classification: sum(1 for keyword in keywords if keyword in normalized)
        for classification, keywords in CLASSIFICATION_KEYWORDS.items()
    }
    best_classification, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score and (freight_signal or _classification_has_freight_anchor(best_classification, normalized)):
        return best_classification
    if freight_signal:
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
        "vessel_name": r"(?:vessel\s*[:#-]?\s*)([A-Z][A-Z0-9 .'-]{2,40})",
        "voyage_no": r"(?:voyage\s*(?:no|number)?\s*[:#-]?\s*)([A-Z0-9/-]{2,12})",
        "origin_port": r"(?:(?:origin|pol|load port)\s*[:#-]?\s*)([A-Z][A-Z .'-]{2,40})",
        "dest_port": r"(?:(?:destination|pod|discharge port)\s*[:#-]?\s*)([A-Z][A-Z .'-]{2,40})",
    }
    for field, pattern in labeled_patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = _clean_value(match.group(1))
            if field == "bl_number":
                if not is_valid_bl_number(value):
                    continue
                value = value.upper()
            elif field == "booking_ref":
                if not is_valid_booking_ref(value):
                    continue
                value = value.upper()
            elif field in {"origin_port", "dest_port"}:
                if not is_valid_port(value):
                    continue
            elif field in {"vessel_name", "voyage_no"}:
                if not is_valid_vessel_or_voyage(value):
                    continue
            extracted[field] = value
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


# ---------------------------------------------------------------------------
# Field-level validation helpers
# ---------------------------------------------------------------------------


_BL_BASE_RE = re.compile(r"^[A-Z0-9][A-Z0-9/_\-]{3,24}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9+/=_\-]{30,}$")


def is_valid_bl_number(value: str) -> bool:
    if not value:
        return False
    candidate = value.strip().upper()
    if len(candidate) < 4 or len(candidate) > 25:
        return False
    if not _BL_BASE_RE.match(candidate):
        return False
    if _looks_token_like(candidate):
        return False
    if _shannon_entropy(candidate) > 4.5:
        return False
    return True


def is_valid_booking_ref(value: str) -> bool:
    if not value:
        return False
    candidate = value.strip().upper()
    if len(candidate) < 4 or len(candidate) > 30:
        return False
    if not _BL_BASE_RE.match(candidate):
        return False
    if _looks_token_like(candidate):
        return False
    return True


def is_valid_port(value: str) -> bool:
    if not value:
        return False
    candidate = value.strip()
    if len(candidate) < 3 or len(candidate) > 60:
        return False
    if not re.match(r"^[A-Za-z][A-Za-z .'-]{2,}$", candidate):
        return False
    return True


def is_valid_vessel_or_voyage(value: str) -> bool:
    if not value:
        return False
    candidate = value.strip()
    if len(candidate) < 2 or len(candidate) > 60:
        return False
    return bool(re.match(r"^[A-Za-z0-9 .'/_-]{2,60}$", candidate))


def is_valid_amount(value: Any) -> bool:
    if value in (None, ""):
        return False
    try:
        amount = Decimal(str(value).replace(",", ""))
    except Exception:
        return False
    if amount <= 0 or amount > Decimal("100000000"):
        return False
    return True


def is_valid_shipment_code(value: Optional[str]) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.match(r"^FF-(?:EXP|IMP)-\d{4}-\d{3,}$", value, re.IGNORECASE))


def _looks_token_like(value: str) -> bool:
    if not _TOKEN_RE.match(value):
        return False
    return _shannon_entropy(value) > 4.0


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _classification_has_freight_anchor(classification: str, normalized: str) -> bool:
    """Treat purely keyword-based hits as freight only if they overlap freight terms."""
    return any(term in normalized for term in FREIGHT_HARD_TERMS)


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
    *,
    has_matched_shipment: bool = False,
    confidence: float = 0.0,
) -> list[dict[str, Any]]:
    today = (received_at.date() if received_at else date.today()).isoformat()
    suggestions: list[dict[str, Any]] = []
    has_strong_anchor = has_matched_shipment or is_valid_shipment_code(extracted_data.get("shipment_code"))
    if not has_strong_anchor and confidence < CONFIDENCE_NO_SHIPMENT_THRESHOLD:
        return []
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
        if "amount" in data and is_valid_amount(data["amount"]):
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
        if not is_valid_amount(amount):
            continue
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

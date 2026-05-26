import math
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


@dataclass
class ExtractedFieldCandidate:
    field_key: str
    field_value: str
    normalized_value: Optional[str] = None
    confidence: float = 0.70
    source_text: Optional[str] = None
    page_number: Optional[int] = None
    status: str = "candidate"
    metadata: Optional[dict] = None


SHIPMENT_CODE_RE = re.compile(r"\bFF-(EXP|IMP)-\d{4}-\d{3,}\b", re.IGNORECASE)
CONTAINER_RE = re.compile(r"\b[A-Z]{4}\d{7}\b", re.IGNORECASE)
CURRENCY_RE = re.compile(r"\b(INR|USD|EUR|GBP|AED)\b", re.IGNORECASE)
AMOUNT_RE = re.compile(
    r"(?:(INR|USD|EUR|GBP|AED)\s*)?([0-9]{1,3}(?:[, ][0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)
DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})\b"
)


def extract_fields(document_type: str, text: str) -> list[ExtractedFieldCandidate]:
    normalized_text = _clean_text(text)
    candidates: list[ExtractedFieldCandidate] = []
    _add_unique(candidates, _shipment_codes(normalized_text))
    _add_unique(candidates, _container_numbers(normalized_text))
    _add_unique(candidates, _labeled_value(normalized_text, "invoice_number", r"(?:invoice|inv)\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,40})", 0.82))
    _add_unique(candidates, _labeled_value(normalized_text, "bl_number", r"(?:bill of lading|b\/l|bl|mbl|hbl)\s*(?:no|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,40})", 0.78))
    _add_unique(candidates, _labeled_value(normalized_text, "do_number", r"(?:delivery order|do)\s*(?:no|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,40})", 0.78))
    _add_unique(candidates, _labeled_value(normalized_text, "voyage_number", r"(?:voyage|voy)\s*(?:no|number)?\s*[:\-]?\s*([A-Z0-9\-\/]{2,20})", 0.72))
    _add_unique(candidates, _labeled_value(normalized_text, "vessel_name", r"(?:vessel|vessel name)\s*[:\-]?\s*([A-Z][A-Z0-9 .'-]{2,60})", 0.70))
    _add_unique(candidates, _labeled_value(normalized_text, "origin_port", r"(?:origin|pol|port of loading)\s*[:\-]?\s*([A-Z][A-Z .'-]{2,50})", 0.68))
    _add_unique(candidates, _labeled_value(normalized_text, "destination_port", r"(?:destination|pod|port of discharge)\s*[:\-]?\s*([A-Z][A-Z .'-]{2,50})", 0.68))
    _add_unique(candidates, _labeled_value(normalized_text, "shipper", r"shipper\s*[:\-]?\s*([A-Z][A-Z0-9 &.,'-]{3,80})", 0.62))
    _add_unique(candidates, _labeled_value(normalized_text, "consignee", r"consignee\s*[:\-]?\s*([A-Z][A-Z0-9 &.,'-]{3,80})", 0.62))
    _add_unique(candidates, _numeric_labeled(normalized_text, "gross_weight", r"gross\s+weight\s*[:\-]?\s*([0-9,.]+)", 0.70))
    _add_unique(candidates, _numeric_labeled(normalized_text, "package_count", r"(?:packages|package count|pkgs)\s*[:\-]?\s*([0-9,]+)", 0.68))
    _add_unique(candidates, _numeric_labeled(normalized_text, "free_days", r"(?:free days|detention free|demurrage free)\s*[:\-]?\s*([0-9]{1,3})", 0.76))
    _add_unique(candidates, _date_labeled(normalized_text, "invoice_date", r"(?:invoice date|inv date)\s*[:\-]?\s*(" + DATE_RE.pattern.strip("\\b") + r")", 0.76))
    _add_unique(candidates, _date_labeled(normalized_text, "arrival_date", r"(?:arrival date|eta)\s*[:\-]?\s*(" + DATE_RE.pattern.strip("\\b") + r")", 0.72))
    _add_unique(candidates, _amounts(normalized_text, document_type))
    return candidates


def normalize_extracted_field(field_key: str, field_value: str) -> Optional[str]:
    value = (field_value or "").strip()
    if not value:
        return None
    if field_key in {"shipment_code", "container_number", "currency", "bl_number", "invoice_number", "do_number"}:
        return re.sub(r"\s+", "", value).upper()
    if field_key in {"origin_port", "destination_port", "shipper", "consignee", "vessel_name"}:
        return re.sub(r"\s+", " ", value).strip().upper()
    if field_key in {"amount", "gross_weight"}:
        numeric = re.sub(r"[^0-9.]", "", value)
        try:
            amount = Decimal(numeric)
        except InvalidOperation:
            return None
        if amount <= 0 or amount > Decimal("1000000000"):
            return None
        return str(amount.quantize(Decimal("0.01")))
    if field_key in {"package_count", "free_days"}:
        numeric = re.sub(r"[^0-9]", "", value)
        return numeric or None
    if field_key.endswith("_date") or field_key == "arrival_date":
        return _normalize_date(value)
    return value


def calculate_field_confidence(field_key: str, field_value: str, context: Optional[dict] = None) -> float:
    normalized = normalize_extracted_field(field_key, field_value)
    if not normalized:
        return 0.20
    if _looks_token_like(field_value):
        return 0.30
    if field_key == "container_number":
        return 0.85 if _valid_container_number(normalized) else 0.45
    if field_key in {"origin_port", "destination_port"} and not re.fullmatch(r"[A-Z .'-]{3,50}", normalized):
        return 0.40
    return 0.72


def _shipment_codes(text: str) -> list[ExtractedFieldCandidate]:
    return [
        ExtractedFieldCandidate("shipment_code", match.group(0), match.group(0).upper(), 0.94, _source(text, match))
        for match in SHIPMENT_CODE_RE.finditer(text)
    ]


def _container_numbers(text: str) -> list[ExtractedFieldCandidate]:
    candidates = []
    for match in CONTAINER_RE.finditer(text.upper()):
        value = match.group(0).upper()
        confidence = 0.88 if _valid_container_number(value) else 0.46
        candidates.append(
            ExtractedFieldCandidate(
                "container_number",
                value,
                value,
                confidence,
                _source(text, match),
                status="candidate" if confidence >= 0.50 else "low_confidence",
            )
        )
    return candidates


def _labeled_value(text: str, field_key: str, pattern: str, confidence: float) -> list[ExtractedFieldCandidate]:
    values = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        raw = _trim_value(match.group(1))
        if not raw or _looks_token_like(raw):
            continue
        normalized = normalize_extracted_field(field_key, raw)
        if not normalized:
            continue
        values.append(ExtractedFieldCandidate(field_key, raw, normalized, confidence, _source(text, match)))
    return values


def _numeric_labeled(text: str, field_key: str, pattern: str, confidence: float) -> list[ExtractedFieldCandidate]:
    values = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        raw = _trim_value(match.group(1))
        normalized = normalize_extracted_field(field_key, raw)
        if normalized:
            values.append(ExtractedFieldCandidate(field_key, raw, normalized, confidence, _source(text, match)))
    return values


def _date_labeled(text: str, field_key: str, pattern: str, confidence: float) -> list[ExtractedFieldCandidate]:
    values = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        raw = _trim_value(match.group(1))
        normalized = normalize_extracted_field(field_key, raw)
        if normalized:
            values.append(ExtractedFieldCandidate(field_key, raw, normalized, confidence, _source(text, match)))
    return values


def _amounts(text: str, document_type: str) -> list[ExtractedFieldCandidate]:
    if document_type not in {"COMMERCIAL_INVOICE", "FREIGHT_INVOICE", "INVOICE"} and "invoice" not in text.lower():
        return []
    values = []
    for match in AMOUNT_RE.finditer(text):
        currency, amount = match.groups()
        normalized_amount = normalize_extracted_field("amount", amount)
        if not normalized_amount:
            continue
        if Decimal(normalized_amount) < Decimal("1"):
            continue
        confidence = 0.64
        values.append(ExtractedFieldCandidate("amount", amount, normalized_amount, confidence, _source(text, match)))
        if currency:
            values.append(ExtractedFieldCandidate("currency", currency, currency.upper(), 0.82, _source(text, match)))
        elif CURRENCY_RE.search(_source(text, match) or ""):
            code = CURRENCY_RE.search(_source(text, match) or "").group(1).upper()
            values.append(ExtractedFieldCandidate("currency", code, code, 0.78, _source(text, match)))
    return values[:4]


def _add_unique(target: list[ExtractedFieldCandidate], candidates: list[ExtractedFieldCandidate]) -> None:
    existing = {(item.field_key, item.normalized_value or item.field_value) for item in target}
    for candidate in candidates:
        key = (candidate.field_key, candidate.normalized_value or candidate.field_value)
        if key not in existing:
            candidate.confidence = min(candidate.confidence, calculate_field_confidence(candidate.field_key, candidate.field_value)) if candidate.confidence < 0.60 else candidate.confidence
            if candidate.confidence < 0.50:
                candidate.status = "low_confidence"
            target.append(candidate)
            existing.add(key)


def _clean_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text or "")


def _trim_value(value: str) -> str:
    return re.split(r"\s{2,}|\n|(?:\s+[A-Z][A-Z ]{2,}:)", value.strip(), 1)[0].strip(" :-")


def _source(text: str, match) -> str:
    start = max(match.start() - 40, 0)
    end = min(match.end() + 60, len(text))
    return re.sub(r"\s+", " ", text[start:end]).strip()[:240]


def _looks_token_like(value: str) -> bool:
    compact = re.sub(r"[^A-Za-z0-9]", "", value or "")
    if len(compact) < 24:
        return False
    unique_ratio = len(set(compact)) / max(len(compact), 1)
    has_mixed = bool(re.search(r"[a-z]", compact) and re.search(r"[A-Z]", compact) and re.search(r"\d", compact))
    entropy_like = unique_ratio > 0.45 and has_mixed
    base64ish = bool(re.fullmatch(r"[A-Za-z0-9+/=]{28,}", compact))
    return entropy_like or base64ish


def _normalize_date(value: str) -> Optional[str]:
    raw = value.strip()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d %b %Y", "%d %B %Y")
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt).date()
            if parsed.year < 1990 or parsed.year > 2100:
                return None
            return parsed.isoformat()
        except ValueError:
            continue
    return None


def _valid_container_number(value: str) -> bool:
    value = value.upper()
    if not re.fullmatch(r"[A-Z]{4}\d{7}", value):
        return False
    weights = {letter: number for letter, number in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", [10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38])}
    total = 0
    for index, char in enumerate(value[:10]):
        number = int(char) if char.isdigit() else weights.get(char, 0)
        total += number * int(math.pow(2, index))
    check_digit = (total % 11) % 10
    return check_digit == int(value[-1])

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ClassificationResult:
    detected_document_type: str
    confidence: float
    engine: str = "deterministic-keywords-v1"
    matched_keywords: Optional[list[str]] = None


DOCUMENT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "BL_DRAFT": ("bill of lading", "draft bl", "shipper", "consignee", "notify party", "vessel", "voyage"),
    "FINAL_BL": ("final bill of lading", "original bill of lading", "final bl", "surrendered", "telex release"),
    "COMMERCIAL_INVOICE": ("commercial invoice", "invoice no", "invoice number", "buyer", "seller", "amount"),
    "PACKING_LIST": ("packing list", "gross weight", "net weight", "packages", "cartons"),
    "SHIPPING_BILL": ("shipping bill", "leo", "drawback", "let export order"),
    "BOE": ("bill of entry", "boe", "customs", "duty", "assessment"),
    "DO": ("delivery order", "do no", "free days", "validity", "do validity"),
    "ARRIVAL_NOTICE": ("arrival notice", "eta", "igm", "vessel arrival"),
    "PRE_ALERT": ("pre-alert", "pre alert", "hbl", "mbl", "eta", "etd"),
    "FREIGHT_INVOICE": ("freight invoice", "freight charges", "ocean freight", "freight amount"),
    "INSURANCE": ("insurance certificate", "policy number", "insured value"),
    "COO": ("certificate of origin", "country of origin"),
    "PHYTO_CERTIFICATE": ("phytosanitary", "phyto certificate"),
    "FUMIGATION_CERTIFICATE": ("fumigation certificate", "fumigation"),
}

DECLARED_TYPE_ALIASES = {
    "INVOICE": "COMMERCIAL_INVOICE",
    "FREIGHT_INVOICE": "FREIGHT_INVOICE",
    "PACKING_LIST": "PACKING_LIST",
    "BL_DRAFT": "BL_DRAFT",
    "FINAL_BL": "FINAL_BL",
    "DO": "DO",
    "BOE": "BOE",
    "PRE_ALERT": "PRE_ALERT",
    "ARRIVAL_NOTICE": "ARRIVAL_NOTICE",
    "COO": "COO",
}


def classify_document_text(
    text: str,
    filename: Optional[str] = None,
    declared_document_type: Optional[str] = None,
) -> ClassificationResult:
    haystack = " ".join(
        part.lower()
        for part in (text[:20000], Path(filename or "").stem.replace("_", " "), declared_document_type or "")
        if part
    )
    declared = _normalize_declared(declared_document_type)
    scores: dict[str, list[str]] = {}
    for document_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        matched = [keyword for keyword in keywords if re.search(rf"\b{re.escape(keyword)}\b", haystack)]
        if matched:
            scores[document_type] = matched

    if not scores and declared:
        return ClassificationResult(declared, 0.68, matched_keywords=["declared_type_hint"])
    if not scores:
        return ClassificationResult("UNKNOWN", 0.20, matched_keywords=[])

    detected, matched_keywords = max(scores.items(), key=lambda item: (len(item[1]), _declared_bonus(item[0], declared)))
    keyword_score = min(0.30 + (len(matched_keywords) * 0.12), 0.88)
    if declared and detected == declared:
        keyword_score = min(keyword_score + 0.10, 0.98)
    elif declared and detected != declared:
        keyword_score = min(keyword_score, 0.76)
    return ClassificationResult(detected, round(keyword_score, 2), matched_keywords=matched_keywords)


def _normalize_declared(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return DECLARED_TYPE_ALIASES.get(value.strip().upper(), value.strip().upper())


def _declared_bonus(document_type: str, declared: Optional[str]) -> int:
    return 1 if declared and document_type == declared else 0

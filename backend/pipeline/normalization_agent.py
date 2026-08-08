"""
Agent 3 -- Normalization

Resolves each RawAttribute produced by Extraction into a canonical,
commerce-ready attribute using the industrial taxonomy (taxonomy.py).
This is the step that turns "Rated Volt.", "Supply Voltage(V)", and
"Operating Voltage" -- three different manufacturers' phrasing -- into
one canonical field: voltage, unit V.

Attributes that can't be confidently matched to the active category's
taxonomy are kept as "custom" attributes (still shown, still traceable,
just outside the standardized schema and always routed to human review).
"""
import uuid

from pipeline.extraction_agent import parse_value
from taxonomy import match_attribute, normalize_unit, get_attribute_def


def normalize(raw_attributes, category: str, source_name: str):
    normalized = []
    for raw in raw_attributes:
        attr_def, match_score = match_attribute(raw.raw_key, category)
        num, raw_unit, value_text = parse_value(raw.raw_value)
        unit = normalize_unit(raw_unit) if raw_unit else None

        if attr_def:
            canonical = attr_def["canonical"]
            attr_type = attr_def["type"]
            expected_unit = attr_def.get("unit")
            match_confidence = min(1.0, match_score / 100.0)
        else:
            canonical = raw.raw_key.strip().lower().replace(" ", "_")[:40]
            attr_type = "number" if num is not None else "text"
            expected_unit = unit
            match_confidence = 0.5  # unmatched -> capped, will need review

        value = num if (attr_type == "number" and num is not None) else value_text

        normalized.append(
            {
                "attr_id": str(uuid.uuid4())[:8],
                "canonical": canonical,
                "display_name": canonical.replace("_", " ").title(),
                "value": value,
                "unit": expected_unit or unit,
                "type": attr_type,
                "is_taxonomy_match": attr_def is not None,
                "taxonomy_match_score": round(match_confidence, 2),
                "extraction_method": raw.extraction_method,
                "extraction_base_confidence": raw.base_confidence,
                "source": {
                    "document": source_name,
                    "page": raw.page,
                    "line_no": raw.line_no,
                    "snippet": raw.source_snippet,
                },
                "status": "auto",
                "audit_trail": [],
            }
        )
    return normalized

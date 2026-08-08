"""
Agent 4 -- Validation & Confidence Scoring

Combines (a) how the value was extracted, (b) how well its label matched
the taxonomy, and (c) whether the value itself is sane (in-range numeric,
recognized enum option) into ONE final confidence score per attribute.

This is what powers confidence-based human-in-the-loop routing: instead
of a generic "review everything" queue, only attributes that are actually
uncertain or risky get a human's attention. Everything else auto-publishes.

Conflict handling: if the same canonical attribute was extracted twice
with different values (e.g. appears in a summary table AND a detailed
spec table), we keep the higher-confidence one and record the conflict
in the audit trail rather than silently dropping data.
"""
from taxonomy import get_attribute_def, validate_numeric, validate_enum
from config import CONFIDENCE_THRESHOLD


def _score_attribute(attr: dict, category: str):
    score = attr["extraction_base_confidence"] * 0.5 + attr["taxonomy_match_score"] * 0.5
    notes = []

    attr_def = get_attribute_def(category, attr["canonical"]) if attr["is_taxonomy_match"] else None
    if attr_def:
        if attr_def["type"] == "number" and isinstance(attr["value"], (int, float)):
            ok, reason = validate_numeric(attr_def, attr["value"])
            if ok:
                score += 0.12
            else:
                score -= 0.45
                notes.append(f"range check failed: {reason}")
        elif attr_def["type"] == "enum" and isinstance(attr["value"], str):
            ok, reason = validate_enum(attr_def, attr["value"])
            if ok:
                score += 0.08
            else:
                score -= 0.25
                notes.append(f"enum check failed: {reason}")
        if attr_def.get("unit") and not attr.get("unit"):
            score -= 0.1
            notes.append("expected a unit but none was found")
    else:
        notes.append("label did not match the standardized taxonomy for this category")

    return max(0.0, min(1.0, round(score, 3))), notes


def validate(normalized_attributes: list, category: str):
    """Scores attributes, resolves same-attribute conflicts, and returns
    (final_attributes, needs_review_flags)."""
    by_canonical = {}
    for attr in normalized_attributes:
        score, notes = _score_attribute(attr, category)
        attr["confidence"] = score
        attr["validation_notes"] = notes

        existing = by_canonical.get(attr["canonical"])
        if existing is None:
            by_canonical[attr["canonical"]] = attr
        else:
            if attr["confidence"] > existing["confidence"]:
                winner, loser = attr, existing
            else:
                winner, loser = existing, attr
            winner.setdefault("audit_trail", []).append(
                {
                    "event": "conflict_resolved",
                    "kept_value": winner["value"],
                    "discarded_value": loser["value"],
                    "discarded_source": loser["source"],
                }
            )
            by_canonical[attr["canonical"]] = winner

    final_attrs = list(by_canonical.values())
    needs_review = []
    for attr in final_attrs:
        if attr["confidence"] < CONFIDENCE_THRESHOLD or attr["validation_notes"]:
            attr["status"] = "needs_review"
            needs_review.append(attr)
        else:
            attr["status"] = "verified_auto"

    return final_attrs, needs_review

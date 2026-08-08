"""
Agent 5 -- Enrichment

After extraction + validation, a product record may still be missing
attributes the taxonomy marks as mandatory for its category (e.g. every
electric motor needs an ip_rating for a commerce listing to be usable).

Rather than leaving these blank, the Enrichment agent looks at OTHER
products already in the same category (the knowledge graph built so
far) and proposes a value from the closest match on shared attributes
-- e.g. "similar 5.5kW / 415V / 1440RPM motors from this catalog are
IP55, so this one probably is too."

Inferred values are never auto-published: they are always tagged
status="inferred" with a capped confidence and pushed to the human
review queue, clearly labeled as an inference rather than an extraction,
with the specific sibling product cited as the reasoning source. This
keeps the enrichment fully explainable instead of a black-box guess.
"""
import uuid

from taxonomy import required_attributes


def _numeric_attrs(product):
    return {
        a["canonical"]: a["value"]
        for a in product["attributes"]
        if a["type"] == "number" and isinstance(a["value"], (int, float))
    }


def _similarity(a_vals: dict, b_vals: dict):
    shared = set(a_vals) & set(b_vals)
    if not shared:
        return 0.0
    diffs = []
    for k in shared:
        a, b = a_vals[k], b_vals[k]
        denom = max(abs(a), abs(b), 1e-6)
        diffs.append(1 - min(1.0, abs(a - b) / denom))
    return sum(diffs) / len(diffs)


def enrich(product: dict, category: str, catalog: list):
    """catalog: list of other existing product dicts (same store) to learn
    from. Mutates and returns product['attributes'] with inferred additions,
    plus a list of the newly-added attributes (for review-queue registration).
    """
    have = {a["canonical"] for a in product["attributes"]}
    missing_required = [a for a in required_attributes(category) if a["canonical"] not in have]
    if not missing_required:
        return []

    siblings = [p for p in catalog if p.get("category") == category and p["id"] != product["id"]]
    if not siblings:
        return []

    this_vals = _numeric_attrs(product)
    scored_siblings = []
    for sib in siblings:
        sim = _similarity(this_vals, _numeric_attrs(sib))
        scored_siblings.append((sim, sib))
    scored_siblings.sort(key=lambda x: x[0], reverse=True)

    best_sim, best_sib = (scored_siblings[0] if scored_siblings else (0.0, None))
    if not best_sib or best_sim <= 0:
        return []

    newly_added = []
    for attr_def in missing_required:
        sib_attr = next((a for a in best_sib["attributes"] if a["canonical"] == attr_def["canonical"]), None)
        if not sib_attr:
            continue
        inferred = {
            "attr_id": str(uuid.uuid4())[:8],
            "canonical": attr_def["canonical"],
            "display_name": attr_def["canonical"].replace("_", " ").title(),
            "value": sib_attr["value"],
            "unit": attr_def.get("unit"),
            "type": attr_def["type"],
            "is_taxonomy_match": True,
            "taxonomy_match_score": 1.0,
            "extraction_method": "graph_inference",
            "extraction_base_confidence": round(0.35 + 0.3 * best_sim, 2),
            "confidence": round(0.35 + 0.3 * best_sim, 2),
            "source": {
                "document": f"inferred from {best_sib['title']} ({best_sib['id']})",
                "page": None,
                "line_no": None,
                "snippet": f"{round(best_sim * 100)}% attribute similarity to sibling product",
            },
            "status": "inferred",
            "validation_notes": [
                f"missing mandatory attribute; inferred from similar product {best_sib['id']} "
                f"({round(best_sim * 100)}% similarity) -- not extracted from a source document"
            ],
            "audit_trail": [],
        }
        product["attributes"].append(inferred)
        newly_added.append(inferred)

    return newly_added

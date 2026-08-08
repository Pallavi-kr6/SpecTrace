"""
Industrial taxonomy engine.

Loads the canonical category/attribute schema (taxonomy.json) and provides:
  - category detection from free text (title / raw document text)
  - fuzzy synonym -> canonical attribute matching (handles "Volt" vs "Voltage"
    vs "Rated Voltage" vs "Supply Voltage(V)")
  - unit-aware numeric range validation (sanity checks)
  - simple unit conversion helpers

This is what stops SpecTrace AI from being "just an LLM that reads a PDF":
every raw label coming out of a datasheet is resolved to ONE canonical,
commerce-ready attribute name, with a known unit and a known valid range,
regardless of which manufacturer wrote the sheet or how they phrased it.
"""
import json
import re
from functools import lru_cache
from rapidfuzz import process, fuzz

from config import TAXONOMY_PATH


@lru_cache(maxsize=1)
def load_taxonomy():
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def list_categories():
    tax = load_taxonomy()
    return [
        {"id": cid, "label": c["label"]}
        for cid, c in tax["categories"].items()
    ]


def detect_category(text: str) -> str:
    """Very lightweight keyword-based category classifier.

    A production system would swap this for an embedding classifier; for the
    prototype, keyword scoring over the taxonomy's own vocabulary is fast,
    fully explainable (we can literally say *why* a category was chosen),
    and needs zero training data.
    """
    tax = load_taxonomy()
    text_l = text.lower()
    best_cat, best_score = "generic_industrial", 0
    for cid, cat in tax["categories"].items():
        if cid == "generic_industrial":
            continue
        score = sum(1 for kw in cat["keywords"] if kw in text_l)
        if score > best_score:
            best_cat, best_score = cid, score
    return best_cat


def _attr_synonym_index(category: str):
    tax = load_taxonomy()
    cat = tax["categories"][category]
    index = {}
    for attr in cat["attributes"]:
        for syn in attr["synonyms"] + [attr["canonical"].replace("_", " ")]:
            index[syn.lower()] = attr
    return index


def match_attribute(raw_key: str, category: str, score_cutoff: int = 78):
    """Fuzzy-match a raw label (e.g. 'Rated Volt.') to a canonical attribute
    definition in the given category's taxonomy. Returns (attr_def, score)
    or (None, 0) if nothing matched well enough.
    """
    raw_key_clean = re.sub(r"[^a-z0-9 /%]", " ", raw_key.lower()).strip()
    raw_key_clean = re.sub(r"\s+", " ", raw_key_clean)
    if not raw_key_clean:
        return None, 0

    index = _attr_synonym_index(category)
    if not index:
        return None, 0

    match = process.extractOne(
        raw_key_clean, index.keys(), scorer=fuzz.WRatio, score_cutoff=score_cutoff
    )
    if not match:
        return None, 0
    matched_syn, score, _ = match
    return index[matched_syn], score


def required_attributes(category: str):
    tax = load_taxonomy()
    return [a for a in tax["categories"][category]["attributes"] if a.get("required")]


def get_attribute_def(category: str, canonical: str):
    tax = load_taxonomy()
    for a in tax["categories"][category]["attributes"]:
        if a["canonical"] == canonical:
            return a
    return None


def validate_numeric(attr_def: dict, value: float):
    """Returns (is_valid, reason)."""
    if attr_def.get("type") != "number":
        return True, None
    lo, hi = attr_def.get("min"), attr_def.get("max")
    if lo is not None and value < lo:
        return False, f"value {value} below expected minimum {lo} {attr_def.get('unit') or ''}".strip()
    if hi is not None and value > hi:
        return False, f"value {value} above expected maximum {hi} {attr_def.get('unit') or ''}".strip()
    return True, None


def validate_enum(attr_def: dict, value: str):
    if attr_def.get("type") != "enum":
        return True, None
    options = [o.lower() for o in attr_def.get("options", [])]
    if value.lower() in options:
        return True, None
    # try loose containment, e.g. "IP-65" vs "IP65"
    normalized = re.sub(r"[^a-z0-9]", "", value.lower())
    for opt in attr_def.get("options", []):
        if re.sub(r"[^a-z0-9]", "", opt.lower()) == normalized:
            return True, None
    return False, f"'{value}' is not a recognized option ({', '.join(attr_def.get('options', []))})"


UNIT_ALIASES = {
    "kw": "kW", "kilowatt": "kW", "kilowatts": "kW",
    "hp": "HP", "horsepower": "HP",
    "v": "V", "volt": "V", "volts": "V", "vac": "V", "vdc": "V",
    "a": "A", "amp": "A", "amps": "A", "ampere": "A", "amperes": "A",
    "hz": "Hz",
    "rpm": "RPM",
    "mm": "mm", "millimeter": "mm", "millimetre": "mm",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g",
    "bar": "bar",
    "psi": "psi",
    "c": "C", "\u00b0c": "C", "celsius": "C",
    "m3/hr": "m3/hr", "m3/h": "m3/hr", "cum/hr": "m3/hr",
    "m": "m", "meter": "m", "metre": "m",
    "kn": "kN",
    "count": "count", "nos": "count", "no": "count",
}


def normalize_unit(raw_unit: str):
    if not raw_unit:
        return None
    key = raw_unit.strip().lower().rstrip(".")
    return UNIT_ALIASES.get(key, raw_unit.strip())


# ------------------------------------------------------------------------
# Industrial classification standards (ETIM / UNSPSC) + DPP readiness
# ------------------------------------------------------------------------
# Every distributor catalog, procurement portal, and marketplace expects a
# controlled classification code alongside the free-form spec data -- ETIM
# for technical/electrical trade data exchange, UNSPSC for procurement and
# spend analysis. Unlike attribute extraction, this is a deterministic
# lookup against a controlled vocabulary (a real classification code isn't
# "guessed" -- it's assigned from a fixed list), so it doesn't go through
# the confidence-scoring pipeline the way extracted specs do.

def get_classification(category: str):
    tax = load_taxonomy()
    return tax.get("classification_codes", {}).get(category)


def get_dpp_fields(category: str):
    """Attributes tagged dpp=true for this category -- the fields tracked
    ahead of the EU ESPR Digital Product Passport phase-in (2026-2030)."""
    tax = load_taxonomy()
    return [a for a in tax["categories"][category]["attributes"] if a.get("dpp")]


def get_dpp_context():
    tax = load_taxonomy()
    return tax.get("dpp_context", {})


def dpp_readiness(category: str, attributes: list):
    """Returns {score, present: [canonical...], missing: [{canonical, display_name}...]}"""
    dpp_defs = get_dpp_fields(category)
    have = {a["canonical"] for a in attributes if a.get("canonical") in {d["canonical"] for d in dpp_defs}}
    missing = [
        {"canonical": d["canonical"], "display_name": d["canonical"].replace("_", " ").title()}
        for d in dpp_defs if d["canonical"] not in have
    ]
    total = len(dpp_defs) or 1
    return {
        "score": round(len(have) / total, 2),
        "present": sorted(have),
        "missing": missing,
        "total_fields": len(dpp_defs),
    }

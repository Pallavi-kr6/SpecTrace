"""
Agent 2 -- Extraction (Document Intelligence)

Pulls candidate (raw_key, raw_value, raw_unit) triples out of the text
blocks produced by the Ingestion agent, using layered pattern matching
tuned for how industrial datasheets actually write specs:

    "Rated Voltage : 415 V"
    "Rated Voltage - 415V"
    "Rated Voltage    415 V"      (whitespace/table-column separated)
    "IP Rating: IP55"
    "Flow Rate: 45 m3/hr"

Every candidate keeps the exact source line + page it was pulled from,
and a base confidence describing HOW it was extracted (structured
separators score higher than loose whitespace splitting). This agent
deliberately does NOT try to be clever about which attribute a label
maps to -- that's the Normalization agent's job. Separation of concerns
keeps each stage explainable on its own.
"""
import re
from dataclasses import dataclass, field


@dataclass
class RawAttribute:
    raw_key: str
    raw_value: str
    page: int
    line_no: int
    source_snippet: str
    extraction_method: str
    base_confidence: float


SEPARATOR_PATTERNS = [
    # "Key : Value"  or  "Key - Value"
    (re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9 /().%\-]{1,40}?)\s*[:\-]\s*(?P<value>.+)$"), "structured_separator", 0.9),
    # "Key   Value" (2+ spaces / tab acting as a column break, common when a
    # PDF table collapses into plain text)
    (re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9 /().%\-]{1,40}?)\s{2,}(?P<value>[\d\-+].+|[A-Z]{2,}.*)$"), "whitespace_column", 0.75),
]

NUMBER_UNIT_RE = re.compile(
    r"^\s*(?P<num>-?\d+(?:[.,]\d+)?)\s*(?P<unit>[A-Za-z%°/³0-9]*)\s*(?:to\s*(?P<num2>-?\d+(?:[.,]\d+)?)\s*(?P<unit2>[A-Za-z%°/³0-9]*))?"
)

NOISE_KEYS = {
    "note", "notes", "page", "warning", "disclaimer", "www", "http", "https",
    "product datasheet", "datasheet", "product data sheet",
}


def _looks_like_noise(key: str) -> bool:
    k = key.strip().lower()
    return (not k) or any(n in k for n in NOISE_KEYS) or len(k) > 45


def parse_value(raw_value: str):
    """Best-effort split of '415 V' -> (415.0, 'V'). Returns (None, None, raw)
    if it doesn't look numeric, so callers can keep the raw text value."""
    raw_value = raw_value.strip().strip(".")
    m = NUMBER_UNIT_RE.match(raw_value)
    if not m:
        return None, None, raw_value
    num_str = m.group("num").replace(",", "")
    try:
        num = float(num_str)
    except ValueError:
        return None, None, raw_value
    unit = (m.group("unit") or "").strip()
    return num, unit, raw_value


def extract(blocks):
    """blocks: list of ingestion_agent.TextBlock
    returns: list[RawAttribute]
    """
    found = []
    for block in blocks:
        line = block.text
        if len(line) < 3 or len(line) > 160:
            continue

        matched = False
        for pattern, method, confidence in SEPARATOR_PATTERNS:
            m = pattern.match(line)
            if not m:
                continue
            key = m.group("key").strip()
            value = m.group("value").strip()
            if _looks_like_noise(key) or not value:
                continue
            found.append(
                RawAttribute(
                    raw_key=key,
                    raw_value=value,
                    page=block.page,
                    line_no=block.line_no,
                    source_snippet=line[:200],
                    extraction_method=method,
                    base_confidence=confidence,
                )
            )
            matched = True
            break
        if matched:
            continue

    return found

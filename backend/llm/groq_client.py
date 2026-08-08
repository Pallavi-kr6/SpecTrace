"""
Optional LLM boost layer -- powered by Groq.

SpecTrace AI's core pipeline (Ingestion -> Extraction -> Normalization ->
Validation -> Enrichment -> Graph) runs fully offline with deterministic,
explainable rule-based agents -- this matters for a hackathon demo (no
API key dependency) and for regulated/air-gapped industrial environments.

When a GROQ_API_KEY *is* configured (a free key from
https://console.groq.com/keys is enough -- Groq's LPU inference is fast
and generously rate-limited on the free tier), this module boosts two
specific steps where a language model genuinely helps:

  1. extract_from_unstructured_text() -- for paragraph-style spec text
     that has no "Key: Value" structure at all (regex can't help here).
  2. generate_marketing_description() -- turning a validated attribute
     table into clean, commerce-ready copy.

Every LLM output still flows back through the same Validation agent as
regex output, so it gets the same range checks, the same confidence
scoring, and the same human-review routing -- the LLM is a source, not
an authority. Groq's API is OpenAI-compatible, so swapping in a
different OpenAI-compatible provider later only means changing the
client construction below.
"""
import json

from config import GROQ_API_KEY, GROQ_MODEL, LLM_ENABLED

_client = None
if LLM_ENABLED:
    try:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
    except Exception:
        _client = None


def is_available():
    return _client is not None


def _chat(prompt: str, max_tokens: int):
    resp = _client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=max_tokens,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return (resp.choices[0].message.content or "").strip()


def extract_from_unstructured_text(text: str, category_label: str):
    """Ask the LLM to pull candidate attribute key/value pairs out of
    free-flowing prose the regex layer can't parse. Returns a list of
    {raw_key, raw_value} dicts (NOT yet scored/validated -- that still
    happens downstream, same as every other extraction source)."""
    if not _client:
        return []

    prompt = f"""You are a document intelligence agent for an industrial product
catalog. Read the following free-form product description text for a
{category_label} and extract every discrete technical specification you can
find as short key/value pairs (e.g. "Voltage" -> "415V").

Return ONLY a JSON array, no prose, no markdown code fences, like:
[{{"raw_key": "Voltage", "raw_value": "415V"}}, ...]

Text:
\"\"\"{text[:6000]}\"\"\"
"""
    try:
        raw = _chat(prompt, max_tokens=1000)
        raw = raw.strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        data = json.loads(raw)
        return [d for d in data if isinstance(d, dict) and "raw_key" in d and "raw_value" in d]
    except Exception:
        return []


def generate_marketing_description(product_title: str, attributes: list):
    if not _client:
        return None
    attr_lines = "\n".join(
        f"- {a['display_name']}: {a['value']}{a.get('unit') or ''}" for a in attributes[:20]
    )
    prompt = f"""Write a concise, factual, 2-3 sentence B2B commerce product
description for the following industrial product. Use ONLY the specs given
below -- do not invent any values. No marketing fluff or superlatives.

Product: {product_title}
Specifications:
{attr_lines}
"""
    try:
        return _chat(prompt, max_tokens=300) or None
    except Exception:
        return None

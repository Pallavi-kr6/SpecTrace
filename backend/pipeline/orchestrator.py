"""
Orchestrator -- runs the full multi-agent pipeline:

  Ingestion -> Extraction -> (optional LLM boost) -> Normalization
  -> Validation -> Enrichment -> Graph linking -> Persistence

and returns the finished product record plus a step-by-step trace of
what each agent did, so the frontend can show its work in real time.
"""
import uuid

from pipeline import ingestion_agent, extraction_agent, normalization_agent, validation_agent, enrichment_agent, classification_agent
from taxonomy import detect_category, load_taxonomy
from llm import groq_client
import storage


def run_pipeline(title: str, raw_text: str = None, pdf_bytes: bytes = None,
                  source_name: str = None, category_override: str = None):
    trace = []

    # 1. Ingestion
    blocks, doc_name = ingestion_agent.ingest(raw_text=raw_text, pdf_bytes=pdf_bytes, source_name=source_name)
    trace.append({"agent": "Ingestion", "detail": f"parsed {len(blocks)} text block(s) from '{doc_name}'"})

    full_text = " ".join(b.text for b in blocks)
    category = category_override or detect_category(f"{title} {full_text}")
    tax = load_taxonomy()
    category_label = tax["categories"][category]["label"]
    trace.append({"agent": "Normalization", "detail": f"classified product as category '{category_label}'"})

    # 2. Extraction (rule-based)
    raw_attrs = extraction_agent.extract(blocks)
    trace.append({"agent": "Extraction", "detail": f"regex/table extraction found {len(raw_attrs)} candidate attribute(s)"})

    # 2b. Optional LLM boost for unstructured leftover text
    if groq_client.is_available():
        llm_pairs = groq_client.extract_from_unstructured_text(full_text, category_label)
        for pair in llm_pairs:
            raw_attrs.append(
                extraction_agent.RawAttribute(
                    raw_key=pair["raw_key"],
                    raw_value=str(pair["raw_value"]),
                    page=1,
                    line_no=0,
                    source_snippet=f"{pair['raw_key']}: {pair['raw_value']} (LLM-extracted)",
                    extraction_method="llm",
                    base_confidence=0.7,
                )
            )
        if llm_pairs:
            trace.append({"agent": "LLM Extraction (Groq)", "detail": f"boosted extraction with {len(llm_pairs)} additional attribute(s) from unstructured text"})

    # 3. Normalization
    normalized = normalization_agent.normalize(raw_attrs, category, doc_name)
    trace.append({"agent": "Normalization", "detail": f"mapped raw labels to {len(normalized)} candidate canonical attribute(s)"})

    # 4. Validation + confidence scoring
    final_attrs, needs_review = validation_agent.validate(normalized, category)
    trace.append({"agent": "Validation", "detail": f"scored attributes; {len(needs_review)} flagged for human review"})

    product_id = storage.new_product_id()
    product = {
        "id": product_id,
        "title": title,
        "category": category,
        "category_label": category_label,
        "attributes": final_attrs,
        "source_documents": list({a["source"]["document"] for a in final_attrs}),
        "needs_review_count": len(needs_review),
        "pipeline_trace": trace,
    }

    # 5. Enrichment (needs the rest of the catalog to compare against)
    catalog = storage.list_products()
    inferred = enrichment_agent.enrich(product, category, catalog)
    if inferred:
        product["needs_review_count"] += len(inferred)
        trace.append({"agent": "Enrichment", "detail": f"inferred {len(inferred)} missing mandatory attribute(s) from similar catalog products"})
    else:
        trace.append({"agent": "Enrichment", "detail": "no missing mandatory attributes could be confidently inferred"})

    # optional LLM description
    if groq_client.is_available():
        desc = groq_client.generate_marketing_description(title, product["attributes"])
        if desc:
            product["description"] = desc
            trace.append({"agent": "LLM Description (Groq)", "detail": "generated a commerce-ready product description from verified attributes"})

    # 7. Industrial classification (ETIM / UNSPSC) + DPP readiness
    classification = classification_agent.classify(category)
    product["classification"] = classification
    if classification and classification.get("etim_class"):
        trace.append({"agent": "Classification", "detail": f"assigned ETIM {classification['etim_class']} / UNSPSC {classification['unspsc_code']}"})
    else:
        trace.append({"agent": "Classification", "detail": "no ETIM class mapped for this category yet -- UNSPSC fallback assigned"})

    dpp = classification_agent.assess_dpp_readiness(category, product["attributes"])
    product["dpp_readiness"] = dpp
    trace.append({"agent": "Compliance Readiness", "detail": f"Digital Product Passport readiness: {round(dpp['score']*100)}% ({len(dpp['present'])}/{dpp['total_fields']} ESPR-tracked fields present)"})

    product["pipeline_trace"] = trace
    storage.save_product(product)

    # 6. Register review queue items
    review_items = []
    for attr in [a for a in product["attributes"] if a["status"] in ("needs_review", "inferred")]:
        review_items.append({
            "review_id": str(uuid.uuid4())[:10],
            "product_id": product_id,
            "product_title": title,
            "attr_id": attr["attr_id"],
            "canonical": attr["canonical"],
            "display_name": attr["display_name"],
            "value": attr["value"],
            "unit": attr.get("unit"),
            "confidence": attr["confidence"],
            "status": attr["status"],
            "reason": "; ".join(attr.get("validation_notes", [])) or "inferred value, not extracted from a source document",
            "source": attr["source"],
        })
    if review_items:
        storage.add_review_items(review_items)

    return product

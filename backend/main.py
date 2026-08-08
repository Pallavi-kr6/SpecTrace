import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request, UploadFile, Form, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import storage
from taxonomy import list_categories
from pipeline.orchestrator import run_pipeline
from pipeline.graph_builder import graph_to_vis_json, compatible_products
from llm.groq_client import is_available as llm_available
from config import CONFIDENCE_THRESHOLD

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="SpecTrace AI", version="1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _summary(product: dict):
    attrs = product["attributes"]
    verified = [a for a in attrs if a["status"] == "verified_auto" or a["status"] == "verified"]
    avg_conf = round(sum(a["confidence"] for a in attrs) / len(attrs), 2) if attrs else 0.0
    dpp = product.get("dpp_readiness") or {}
    classification = product.get("classification") or {}
    return {
        "id": product["id"],
        "title": product["title"],
        "category": product["category"],
        "category_label": product["category_label"],
        "attribute_count": len(attrs),
        "verified_count": len(verified),
        "needs_review_count": product.get("needs_review_count", 0),
        "avg_confidence": avg_conf,
        "dpp_score": dpp.get("score", 0.0),
        "etim_class": classification.get("etim_class"),
        "unspsc_code": classification.get("unspsc_code"),
        "updated_at": product.get("updated_at"),
        "created_at": product.get("created_at"),
    }


# ---------------------------------------------------------------- pages ----

@app.get("/")
def page_home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "categories": list_categories(),
        "llm_available": llm_available(),
    })


@app.get("/products/{product_id}")
def page_product(request: Request, product_id: str):
    product = storage.get_product(product_id)
    if not product:
        raise HTTPException(404, "product not found")
    return templates.TemplateResponse("product_detail.html", {"request": request, "product": product})


@app.get("/review")
def page_review(request: Request):
    return templates.TemplateResponse("review_queue.html", {"request": request})


@app.get("/dashboard")
def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# --------------------------------------------------------------- api -------

@app.get("/api/meta")
def api_meta():
    return {
        "llm_available": llm_available(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "categories": list_categories(),
    }


@app.post("/api/products")
async def api_create_product(
    title: str = Form(...),
    text: str = Form(""),
    category_override: str = Form(""),
    file: UploadFile = File(None),
):
    pdf_bytes = None
    source_name = None
    if file is not None and file.filename:
        content = await file.read()
        if file.filename.lower().endswith(".pdf"):
            pdf_bytes = content
            source_name = file.filename
        else:
            text = (text + "\n" + content.decode("utf-8", errors="ignore")).strip()
            source_name = file.filename

    if not text and not pdf_bytes:
        raise HTTPException(400, "provide pasted text and/or upload a file")

    product = run_pipeline(
        title=title,
        raw_text=text,
        pdf_bytes=pdf_bytes,
        source_name=source_name,
        category_override=category_override or None,
    )
    return product


@app.get("/api/bulk-template.csv")
def api_bulk_template():
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["title", "category_override", "text"])
    writer.writerow([
        "IEC 3kW 3-Phase Induction Motor",
        "electric_motor",
        "Rated Power: 3 kW | Rated Voltage: 415 V | Rated Speed: 1440 RPM | IP Rating: IP55 | Standard: IEC 60034",
    ])
    writer.writerow([
        "DN40 Gate Valve",
        "",
        "Nominal Size: 40 mm | Pressure Rating: 16 bar | Body Material: Cast Iron | Standard: IS 780",
    ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=spectrace_bulk_import_template.csv"},
    )


@app.post("/api/products/bulk")
async def api_bulk_create(file: UploadFile = File(...)):
    """Bulk catalog ingestion: one row per product. Expected columns:
    title (required), text (spec text -- use '|' or newlines to separate
    lines), category_override (optional). Every row runs through the
    exact same 6-agent pipeline as a single upload -- this is what makes
    it scale across large catalogs without a separate 'bulk mode' code
    path to trust less than the single-product path."""
    content = await file.read()
    text = content.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames or "title" not in [f.strip().lower() for f in reader.fieldnames]:
        raise HTTPException(400, "CSV must include at least a 'title' column (see /api/bulk-template.csv)")

    results = []
    row_num = 1
    for row in reader:
        row_num += 1
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        title = row.get("title", "")
        if not title:
            results.append({"row": row_num, "status": "error", "detail": "missing title"})
            continue
        raw_text = row.get("text", "").replace("|", "\n")
        category_override = row.get("category_override") or None
        try:
            product = run_pipeline(
                title=title,
                raw_text=raw_text,
                source_name=f"{file.filename} (row {row_num})",
                category_override=category_override,
            )
            results.append({
                "row": row_num, "status": "ok", "id": product["id"], "title": title,
                "attribute_count": len(product["attributes"]),
                "needs_review_count": product["needs_review_count"],
            })
        except Exception as e:
            results.append({"row": row_num, "status": "error", "detail": str(e), "title": title})

    ok = [r for r in results if r["status"] == "ok"]
    return {
        "processed": len(results),
        "created": len(ok),
        "failed": len(results) - len(ok),
        "total_needs_review": sum(r.get("needs_review_count", 0) for r in ok),
        "results": results,
    }


@app.get("/api/dashboard")
def api_dashboard():
    products = storage.list_products()
    if not products:
        return {
            "total_products": 0, "avg_confidence": 0, "total_needs_review": 0,
            "avg_dpp_readiness": 0, "categories": [], "classification_coverage": 0,
        }

    summaries = [_summary(p) for p in products]
    total = len(products)
    avg_conf = round(sum(s["avg_confidence"] for s in summaries) / total, 2)
    avg_dpp = round(sum(s["dpp_score"] for s in summaries) / total, 2)
    total_review = sum(s["needs_review_count"] for s in summaries)
    classified = sum(1 for s in summaries if s["etim_class"])

    by_cat = {}
    for p, s in zip(products, summaries):
        c = by_cat.setdefault(p["category"], {
            "category": p["category"], "category_label": p["category_label"],
            "count": 0, "avg_confidence_sum": 0.0, "needs_review": 0,
        })
        c["count"] += 1
        c["avg_confidence_sum"] += s["avg_confidence"]
        c["needs_review"] += s["needs_review_count"]

    categories = []
    for c in by_cat.values():
        categories.append({
            "category": c["category"], "category_label": c["category_label"],
            "count": c["count"],
            "avg_confidence": round(c["avg_confidence_sum"] / c["count"], 2),
            "needs_review": c["needs_review"],
        })
    categories.sort(key=lambda c: c["count"], reverse=True)

    return {
        "total_products": total,
        "avg_confidence": avg_conf,
        "total_needs_review": total_review,
        "avg_dpp_readiness": avg_dpp,
        "classification_coverage": round(classified / total, 2),
        "categories": categories,
    }


@app.get("/api/products")
def api_list_products(q: str = "", category: str = "", status: str = ""):
    products = storage.list_products()
    products.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    summaries = [_summary(p) for p in products]

    if q:
        q_lower = q.lower()
        summaries = [s for s in summaries if q_lower in s["title"].lower()]
    if category:
        summaries = [s for s in summaries if s["category"] == category]
    if status == "needs_review":
        summaries = [s for s in summaries if s["needs_review_count"] > 0]
    elif status == "clear":
        summaries = [s for s in summaries if s["needs_review_count"] == 0]

    return summaries


@app.get("/api/products/{product_id}")
def api_get_product(product_id: str):
    product = storage.get_product(product_id)
    if not product:
        raise HTTPException(404, "product not found")
    product = dict(product)
    product["compatible_products"] = compatible_products(product_id, storage.list_products())
    return product


@app.delete("/api/products/{product_id}")
def api_delete_product(product_id: str):
    storage.delete_product(product_id)
    return {"ok": True}


@app.get("/api/products/{product_id}/graph")
def api_product_graph(product_id: str):
    products = storage.list_products()
    return graph_to_vis_json(products, focus_id=product_id)


@app.get("/api/graph")
def api_full_graph():
    return graph_to_vis_json(storage.list_products())


@app.get("/api/products/{product_id}/export")
def api_export_product(product_id: str):
    product = storage.get_product(product_id)
    if not product:
        raise HTTPException(404, "product not found")
    return {
        "id": product["id"],
        "title": product["title"],
        "category": product["category"],
        "description": product.get("description"),
        "classification": product.get("classification"),
        "dpp_readiness": product.get("dpp_readiness"),
        "attributes": [
            {
                "name": a["display_name"],
                "canonical": a["canonical"],
                "value": a["value"],
                "unit": a.get("unit"),
                "confidence": a["confidence"],
                "status": a["status"],
                "source": a["source"],
            }
            for a in product["attributes"]
        ],
        "compatible_products": compatible_products(product_id, storage.list_products()),
        "traceability_note": "Every attribute's `source` field cites the exact document, page, and line it was "
                              "extracted from, or is explicitly marked as a graph-based inference.",
    }


@app.get("/api/export/catalog.csv")
def api_export_catalog_csv():
    products = storage.list_products()
    canonical_fields = []
    for p in products:
        for a in p["attributes"]:
            if a["canonical"] not in canonical_fields:
                canonical_fields.append(a["canonical"])

    fieldnames = ["id", "title", "category", "etim_class", "unspsc_code", "avg_confidence",
                  "needs_review_count", "dpp_readiness_pct"] + canonical_fields
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for p in products:
        s = _summary(p)
        row = {
            "id": p["id"], "title": p["title"], "category": p["category"],
            "etim_class": s.get("etim_class") or "", "unspsc_code": s.get("unspsc_code") or "",
            "avg_confidence": s["avg_confidence"],
            "needs_review_count": p.get("needs_review_count", 0),
            "dpp_readiness_pct": round(s.get("dpp_score", 0) * 100),
        }
        for a in p["attributes"]:
            val = a["value"]
            if a.get("unit"):
                val = f"{val} {a['unit']}"
            row[a["canonical"]] = val
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=spectrace_catalog_export.csv"},
    )


@app.get("/api/review-queue")
def api_review_queue():
    items = storage.list_review_queue()
    items.sort(key=lambda r: r["confidence"])
    return items


@app.post("/api/review/{review_id}/resolve")
def api_resolve_review(review_id: str, action: str = Form(...), new_value: str = Form(None)):
    if action not in ("approve", "edit", "reject"):
        raise HTTPException(400, "action must be approve, edit, or reject")
    value = new_value
    if value is not None:
        try:
            value = float(value)
        except ValueError:
            pass
    product = storage.resolve_review_item(review_id, action, new_value=value)
    if not product:
        raise HTTPException(404, "review item not found")
    return {"ok": True, "product_id": product["id"]}


@app.post("/api/seed")
def api_seed():
    from seed import run_seed
    created = run_seed()
    return {"ok": True, "created": created}


@app.post("/api/reset")
def api_reset():
    storage.reset()
    return {"ok": True}

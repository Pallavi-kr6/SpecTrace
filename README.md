# SpecTrace AI
### Explainable Product Intelligence for Industrial Commerce

> "Every attribute in the catalog either points to the exact line it came from,
> or is honestly labeled as a guess. Nothing in between."

A working prototype built for the **AI-Powered Product Intelligence for
Industrial Commerce** challenge — a 7-agent pipeline that turns a pasted
spec paragraph, a messy supplier PDF, or a whole CSV catalog into
structured, validated, classified, and traceable commerce-ready product
records.

---

## 1. Problem Statement

Industrial manufacturers and distributors manage product information
scattered across websites, PDF catalogs, supplier datasheets, nameplates,
and digital assets. Turning this fragmented, inconsistent data into
accurate, structured, commerce-ready product intelligence is slow, manual,
and error-prone — and gets *harder*, not easier, as catalogs scale into
the thousands of SKUs across dozens of suppliers, each with its own
spec-sheet format and vocabulary.

The challenge: build an AI-powered solution that automates the
**creation, enrichment, and validation** of product intelligence from
limited product information — improving data quality, scaling across
large catalogs, and staying explainable enough to actually be trusted.

---

## 2. Market Research

**The market is large and growing fast, but immature outside retail.**
The global Product Information Management (PIM) software market is
commonly sized at roughly **$11.5–20B in 2024–26**, forecast at a
**9–17% CAGR** toward $30–37B+ by the early 2030s. Analyst-named vendors
are consistent across reports: **Akeneo, Salsify, Syndigo, inRiver,
Pimcore, Plytix, Stibo Systems, SAP, Oracle, IBM, Informatica,
Contentserv, Riversand.**

**Adoption is accelerating and bad data has a measurable cost.** PIM
adoption among B2B firms is estimated at **68%, up from 59% in 2023**,
with 70% of non-adopters planning to invest. On the buyer side, **43% of
B2B buyers abandon an online order and call a sales rep instead** when
product information is incomplete.

**AI is already inside every major PIM — pointed at retail content, not
industrial specs.** Akeneo's *Ask Ziggy*, Salsify's *Angie* copilot,
inRiver's AI-powered enrichment, Pimcore's *AI Copilot* — every major
platform shipped an AI layer in the last year, and every one of them is
aimed at generating marketing copy, translating descriptions, and
optimizing "digital shelf" content for grocery, apparel, and electronics.
Pricing reflects that audience: mid-market PIM commonly runs
**€25K–60K/year**, enterprise deployments reach **€150K–500K+/year**,
plus 50–200% implementation overhead.

**A narrower wave of industrial-specific point tools has emerged.**
**Verdantis** extracts spare-parts data from PDFs and CAD files;
**Partium** powers OEM cross-reference search for field technicians. Real
demand, real traction — but each solves one slice of the problem, not the
full loop from messy document to governed, structured catalog record.

**Classification is the labor-intensive problem nobody's really solved.**
Every distributor catalog, e-procurement portal, and B2B marketplace
expects a controlled classification code alongside the free-form
specs — **ETIM** for European electrical/technical trade data exchange,
**eCl@ss** for cross-industry engineering catalogs, **UNSPSC** for
procurement and spend analysis. Industry sources note that manufacturers
routinely need two or three of these simultaneously, and that "the class
code is the easy half — the property set is where the labor is." Roughly
98% of manufacturers report product-data issues, and a growing set of
AI-powered classifiers (WisePIM, Claro, Catsy) have emerged specifically
to auto-assign these codes — confirming it's a real, current, and still
largely manual pain point.

**A new regulatory driver is arriving on a fixed timeline.** The EU's
**Ecodesign for Sustainable Products Regulation (ESPR)** introduces the
**Digital Product Passport (DPP)** — mandatory sustainability/compliance
data (material composition, country of origin, recyclability, substances
of concern) phased in by product category under the **ESPR Working Plan
2025–2030**: iron & steel from 2026, batteries/textiles/tyres/aluminium
from 2027, electronics/ICT 2028–2029. Once a delegated act is adopted for
a category, businesses get roughly 18 months before enforcement. Every
industry guide on this says the same thing: the data-collection
infrastructure takes far longer to build than the compliance deadline
allows, so preparing the data model *now* — before it's mandatory — is a
real competitive advantage, not premature effort.

**Sources:** Verified Market Research / Grand View Research / Mordor
Intelligence / Fortune Business Insights — PIM market sizing, 2024–2026 ·
Truvio — PIM adoption stats · Sana Commerce (via HumCommerce) — B2B buyer
abandonment data · inriver.com, netguru.com, akeneo.com — PIM/AI feature
and pricing comparisons, 2026 · Verdantis case studies; Partium product
pages · Catsy, Anglera, AtroPIM, WisePIM, Claro — ETIM/eCl@ss/UNSPSC
classification guides, 2026 · Circularise, ASUENE, inRiver, Certivo,
Fluxy, PassportCraft — EU ESPR/DPP timeline guides, 2026

---

## 3. The Gap

| # | Gap | Why it matters |
|---|-----|-----------------|
| **1** | **Retail bias** — AI enrichment optimizes marketing copy, not engineering attributes | Industrial buyers filter by voltage, IP rating, flow rate — not lifestyle copy |
| **2** | **Shallow document intelligence** on dense technical PDFs | Real spec data lives in supplier datasheets, not clean CSVs |
| **3** | **No explainability** — enriched values shown as fact, no citation | A wrong spec on a safety-rated valve is a liability |
| **4** | **Point solutions, not a full loop** (Verdantis = MDM, Partium = search) | Manufacturers stitch 3–4 tools together by hand |
| **5** | **Classification is still manual** — ETIM/UNSPSC/eCl@ss codes assigned by hand or in a separate tool | Products without valid codes don't appear in distributor catalogs or procurement searches |
| **6** | **No regulatory foresight** — nobody's tracking EU DPP/ESPR readiness at the catalog-record level | 18-month compliance windows are too short to start from zero |
| **7** | **Priced for enterprise** (€25K–500K+/yr) | Locks out the MSME long tail — most IndiaMART/TradeIndia sellers |

**The gap, in one line:** *no affordable, explainable, industrial-taxonomy-aware
product intelligence engine that classifies against real trade standards,
tracks emerging compliance data, shows its work end-to-end, and scales to
a whole catalog at once.*

---

## 4. Our Solution — SpecTrace AI

A **7-agent pipeline** that turns limited, messy product input — one
product at a time or a whole CSV catalog at once — into a structured,
validated, classified, and explainable knowledge graph:

```
Ingestion → Extraction → Normalization → Validation → Enrichment → Classification → Knowledge Graph + Review Routing
  (PDF/text    (regex/table    (fuzzy-match      (range/enum      (infer missing    (ETIM + UNSPSC      (compatibility
   → blocks     + optional      to industrial     checks,          mandatory         codes, deterministic  edges, DPP
   w/ page/     Groq LLM        taxonomy, unit     confidence       fields from       lookup, then DPP      readiness
   line refs)   boost)          normalization)     scoring)         similar SKUs)     readiness scoring)    score, queue)
```

- **Ingestion** parses pasted text or PDF (tables + raw text via
  `pdfplumber`), tagging every line with a page/line number.
- **Extraction** uses layered pattern matching tuned to industrial
  datasheet formats, with an *optional* Groq-powered agent (free tier)
  that boosts extraction on unstructured paragraph text. Runs **fully
  offline** with no API key.
- **Normalization** fuzzy-matches raw labels to ONE canonical taxonomy
  attribute per category, with unit normalization.
- **Validation** scores every attribute's confidence and resolves
  conflicting duplicate values with a full audit trail.
- **Enrichment** fills missing *mandatory* attributes by finding the
  closest-matching sibling product already in the catalog — always
  capped confidence, always routed to human review.
- **Classification** *(new)* deterministically assigns an **ETIM class**
  and **UNSPSC code** per product category — the two codes real
  distributor catalogs and procurement portals require. Unlike extracted
  specs, this is a controlled-vocabulary lookup, not a guess, so it
  doesn't need confidence scoring.
- **Knowledge Graph + Compliance Readiness** links Product → Category →
  Source Document, computes `COMPATIBLE_WITH` edges between similar
  products, and *(new)* scores each product's **Digital Product Passport
  readiness** — how many of the four EU ESPR-relevant fields (country of
  origin, recyclability %, hazardous-substance declaration, carbon
  footprint) are already present, ahead of each category's 2026–2030
  compliance deadline.

**Confidence-based human-in-the-loop:** only attributes below the
confidence threshold, failing a validation check, or filled by inference
are routed to the review queue. Everything else auto-publishes.

### New in this version

- **Bulk CSV catalog import** — upload a spreadsheet, one row per
  product; every row runs through the identical 7-agent pipeline as a
  single upload. This is what "scale efficiently across large product
  catalogs" looks like as a real, working feature rather than a claim.
- **ETIM / UNSPSC classification** on every product, surfaced in a
  dedicated panel.
- **Digital Product Passport readiness scoring**, with a plain-English
  note on the actual ESPR phase-in timeline — not a compliance claim,
  a readiness signal.
- **Catalog health dashboard** — total products, average confidence,
  pending review count, classification coverage, average DPP readiness,
  and a per-category breakdown.
- **Search and filter** the catalog by name, category, and review status.
- **Redesigned interface** — a warmer, lighter, more approachable UI
  (Plus Jakarta Sans / Inter, soft indigo-and-teal palette, real icons,
  toast notifications, a confirm dialog instead of a browser `confirm()`
  popup, drag-and-drop file upload) replacing the earlier dense
  dark "blueprint" theme.

### Our USP

> **We're the only product-intelligence tool that shows its work — and
> the only one built for the specific shape of industrial catalog data.**
> Every value is either traced to an exact document/page/line or
> transparently labeled as an inference. Every product gets the ETIM and
> UNSPSC codes real distributor and procurement systems require. Every
> catalog gets a live readiness score against the EU's incoming Digital
> Product Passport rules — years before the compliance deadline forces
> the issue. It runs on an industrial-specific taxonomy, scales to a
> whole CSV catalog in one pass, and deploys as a single lightweight
> service — no six-month PIM rollout, no per-seat enterprise pricing.

---

## 5. Target Users

| Segment | Why SpecTrace AI fits |
|---|---|
| **MSME industrial manufacturers & distributors** (electrical, automation, hardware, fasteners, HVAC, pumps & valves, bearings) selling via their own site, IndiaMART/TradeIndia, or Amazon Business | Can't justify €25K–500K/year enterprise PIM; need commerce-ready, classified specs fast |
| **Industrial B2B marketplaces & aggregators** | Want to standardize seller-submitted catalog quality *and* enforce valid classification codes |
| **Multi-brand distributors** | Ingest wildly inconsistent spec formats from dozens of manufacturers and need one canonical schema — at catalog scale via bulk import |
| **Exporters to the EU** | Need to start tracking DPP-relevant data now, ahead of category-by-category ESPR enforcement from 2026 |
| **PIM/catalog teams inside larger manufacturers** | Can run SpecTrace AI as an AI pre-processing layer that feeds clean, classified, cited data into an existing Akeneo/Salsify instance |

---

## 6. Competitors vs. Our Solution

| Dimension | Akeneo / Salsify / Syndigo | Verdantis / Partium | WisePIM / Claro (AI classifiers) | **SpecTrace AI** |
|---|---|---|---|---|
| Primary focus | Retail/CPG digital shelf content | Spare-parts MDM / search | ETIM/UNSPSC/eCl@ss auto-classification | End-to-end industrial product intelligence |
| Technical PDF/datasheet intelligence | Shallow — tuned for marketing assets | Strong (CAD/2D drawings) | Not their focus | Table + text extraction tuned for spec sheets, with page/line citation |
| Source traceability per attribute | ✗ | Partial | ✗ | **✔ every attribute cites doc + page + line, or is labeled "inferred"** |
| Confidence-based human review routing | ✗ generic workflows | Partial | ✗ | **✔ only low-confidence / risky attributes reach a human** |
| Industrial taxonomy (units, ranges, IP/compliance) | ✗ generic/retail | Domain-specific but narrow | ✗ | **✔ purpose-built, extensible** |
| ETIM / UNSPSC classification | ✗ | ✗ | ✔ (their core feature) | **✔ built into the same pipeline, deterministic + confidence-consistent** |
| EU Digital Product Passport readiness | ✗ | ✗ | ✗ | **✔ unique — no competitor tracks this today** |
| Bulk catalog import | Enterprise ETL/connectors | ✗ | ✔ | **✔ CSV → full pipeline per row, no separate "bulk mode" to trust less** |
| Cross-product compatibility graph | ✗ | ✔ (Partium's core feature) | ✗ | **✔ built into the same graph, not a bolt-on** |
| Deployment & pricing | €25K–500K+/yr, 50–200% implementation | Enterprise, custom pricing | SaaS, mid-market | **Lightweight, self-hostable, MSME-accessible** |

---

## 7. Tech Stack & Architecture

- **Backend:** FastAPI (Python), server-rendered pages + JSON API
- **Document parsing:** `pdfplumber` (tables + text, page-accurate)
- **Taxonomy matching:** `rapidfuzz` for synonym → canonical attribute resolution
- **Classification:** deterministic ETIM/UNSPSC lookup table (`taxonomy.json`)
- **Knowledge graph:** `networkx`, exported to a custom SVG "schematic" renderer (no external chart-lib dependency)
- **Optional LLM boost:** `groq` SDK (free tier, OpenAI-compatible, LPU-accelerated) for unstructured-text extraction and description generation — the pipeline is 100% functional without an API key
- **Storage:** JSON-file repository (swap-in-ready for Postgres/Mongo — see `storage.py`)
- **Frontend:** vanilla HTML/CSS/JS, no build step, warm light theme with hand-authored SVG icons, toast notifications, and a custom confirm-modal component

Everything is agent-separated (`backend/pipeline/*.py`) so any single stage
can be replaced without touching the rest of the pipeline — e.g. swapping
the rule-based Extraction agent for a vision-language model reading
nameplate photos once a stable vision model is available on the chosen
LLM provider.

---

## 8. Running It

```bash
# from the project root
./run.sh
# → creates a venv, installs deps, starts the server at http://localhost:8000
```

Open **http://localhost:8000**, click **"Load sample catalog"** for an
instant demo, or:

- Paste spec text / upload a PDF under the **Single product** tab
- Switch to the **Bulk import (CSV)** tab and upload
  `backend/data/seed_products/bulk_import_demo.csv` (bundled) to see five
  products created from one file in a single pass
- Visit **Dashboard** for the catalog-wide health view
- Visit **Review Queue** to approve/edit/reject flagged attributes

**Optional — enable the Groq LLM boost (free tier):**
```bash
cp .env.example .env
# get a free key at https://console.groq.com/keys, then set
# GROQ_API_KEY=gsk_... in .env
```

### Demo walkthrough for judges
1. Home page → **Load sample catalog** → six products appear, stat cards
   populate (products, avg confidence, pending review, avg DPP readiness).
2. Open the **compact motor** — its `ip_rating` is missing from its
   source sheet; the Enrichment agent inferred it from a sibling motor,
   cited why, and routed it to review.
3. Same page → **Classification & Standards** panel shows its ETIM class
   and UNSPSC code, assigned automatically. → **Compliance readiness**
   panel shows its Digital Product Passport score with the real ESPR
   timeline context.
4. Switch to the **Bulk import** tab, upload the bundled demo CSV → five
   more products appear in one pipeline run.
5. Visit **Dashboard** → category breakdown, classification coverage
   gauge, average DPP readiness gauge.
6. Visit **Review Queue** → approve / edit / reject a flagged attribute →
   toast confirmation, list updates live.
7. Back on a product page → **Compatible / interchangeable** panel and
   the knowledge graph panel show two similar motors linked at high
   attribute similarity.
8. **Export JSON** / **Export full catalog CSV** (now includes ETIM/UNSPSC
   codes and DPP readiness %) → commerce-ready output.

---

## 9. What's Next (Roadmap Beyond the Prototype)

- Vision-language agent for nameplate/label photo OCR — deferred in this
  version because the previously free-tier vision models on Groq
  (Llama 4 Scout/Maverick) were deprecated in Feb 2026 in favor of
  text-only reasoning models; revisit once a stable free-tier vision
  model is available.
- Expand taxonomy coverage (fasteners, cables, HVAC, safety equipment)
  and eCl@ss codes alongside ETIM/UNSPSC.
- Active learning: reviewer corrections retrain the fuzzy-matching
  synonym dictionary automatically.
- Direct connectors to push validated records into Akeneo/Salsify/
  Shopify/IndiaMART seller panels.
- Server-side pagination for catalogs beyond a few thousand SKUs.
- Multi-language extraction & normalization for cross-border supplier documents.

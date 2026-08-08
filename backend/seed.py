"""
Seeds the catalog with a handful of realistic (but synthetic) industrial
datasheets so the app is immediately demoable -- product list, knowledge
graph, compatible-parts, and the human review queue all have real data
without requiring a judge to upload their own file first.

Run standalone:  python seed.py
Or via API:       POST /api/seed
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import SEED_DIR
from pipeline.orchestrator import run_pipeline
import storage


def run_seed():
    created = []
    files = sorted(SEED_DIR.glob("*.txt"))
    for path in files:
        raw = path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        title_line = next((l for l in lines if l.upper().startswith("TITLE:")), None)
        title = title_line.split(":", 1)[1].strip() if title_line else path.stem
        body = "\n".join(l for l in lines if l is not title_line)
        product = run_pipeline(title=title, raw_text=body, source_name=path.name)
        created.append(product["id"])
        print(f"seeded {product['id']}: {title}  ({len(product['attributes'])} attrs, "
              f"{product['needs_review_count']} need review)")
    return created


if __name__ == "__main__":
    storage.reset()
    run_seed()

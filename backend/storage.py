"""
Minimal JSON-file "database" so the prototype runs with zero external
infra (no Postgres/Mongo to stand up during a hackathon judging window).

Everything goes through this module, so swapping to a real database later
means rewriting this one file -- nothing in the agents or API layer would
need to change (repository pattern).
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from config import STORE_PATH

_lock = threading.Lock()

_EMPTY_STATE = {"products": {}, "review_queue": [], "next_id": 1}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read():
    if not STORE_PATH.exists():
        return json.loads(json.dumps(_EMPTY_STATE))
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(state):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp.replace(STORE_PATH)


def reset():
    with _lock:
        _write(json.loads(json.dumps(_EMPTY_STATE)))


def new_product_id():
    with _lock:
        state = _read()
        pid = f"P{state['next_id']:05d}"
        state["next_id"] += 1
        _write(state)
        return pid


def save_product(product: dict):
    with _lock:
        state = _read()
        product["updated_at"] = _now()
        if "created_at" not in product:
            product["created_at"] = product["updated_at"]
        state["products"][product["id"]] = product
        _write(state)
        return product


def get_product(product_id: str):
    state = _read()
    return state["products"].get(product_id)


def list_products():
    state = _read()
    return list(state["products"].values())


def delete_product(product_id: str):
    with _lock:
        state = _read()
        state["products"].pop(product_id, None)
        state["review_queue"] = [
            r for r in state["review_queue"] if r["product_id"] != product_id
        ]
        _write(state)


def add_review_items(items: list):
    with _lock:
        state = _read()
        state["review_queue"].extend(items)
        _write(state)


def list_review_queue():
    state = _read()
    return state["review_queue"]


def resolve_review_item(review_id: str, action: str, new_value=None, reviewer: str = "human_reviewer"):
    """action: 'approve' | 'edit' | 'reject'"""
    with _lock:
        state = _read()
        queue = state["review_queue"]
        item = next((r for r in queue if r["review_id"] == review_id), None)
        if not item:
            return None
        product = state["products"].get(item["product_id"])
        if not product:
            return None

        attr = next((a for a in product["attributes"] if a["attr_id"] == item["attr_id"]), None)
        if attr:
            if action == "approve":
                attr["confidence"] = 1.0
                attr["status"] = "verified"
            elif action == "edit":
                attr["value"] = new_value
                attr["confidence"] = 1.0
                attr["status"] = "verified"
                attr.setdefault("audit_trail", []).append(
                    {"event": "human_edit", "by": reviewer, "at": _now(), "new_value": new_value}
                )
            elif action == "reject":
                product["attributes"] = [a for a in product["attributes"] if a["attr_id"] != item["attr_id"]]

            attr and attr.setdefault("audit_trail", []).append(
                {"event": f"human_{action}", "by": reviewer, "at": _now()}
            )

        product["needs_review_count"] = max(0, product.get("needs_review_count", 1) - 1)
        product["updated_at"] = _now()
        state["products"][product["id"]] = product
        state["review_queue"] = [r for r in queue if r["review_id"] != review_id]
        _write(state)
        return product

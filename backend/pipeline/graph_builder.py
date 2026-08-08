"""
Agent 6 -- Knowledge Graph Builder

Builds a traceable product knowledge graph across the WHOLE catalog (not
just one product at a time). Node types: Product, Category, Document.
Every attribute is stored on its Product node but edges make the
provenance and relationships explicit:

    Product --BELONGS_TO--> Category
    Product --SOURCED_FROM--> Document
    Product --COMPATIBLE_WITH--> Product   (shared category + close specs)

This graph is what lets a buyer (or a downstream commerce system) ask
"what else works like this part" and get an answer traced to real
attribute overlap, not a black-box recommendation.
"""
import networkx as nx

from pipeline.enrichment_agent import _numeric_attrs, _similarity

COMPATIBILITY_THRESHOLD = 0.85


def build_graph(products: list):
    g = nx.DiGraph()

    for p in products:
        g.add_node(p["id"], type="product", label=p["title"], category=p.get("category"))
        cat_node = f"cat::{p.get('category')}"
        g.add_node(cat_node, type="category", label=p.get("category_label", p.get("category")))
        g.add_edge(p["id"], cat_node, relation="BELONGS_TO")

        docs = {a["source"]["document"] for a in p["attributes"] if a["source"].get("document")}
        for doc in docs:
            doc_node = f"doc::{doc}"
            g.add_node(doc_node, type="document", label=doc)
            g.add_edge(p["id"], doc_node, relation="SOURCED_FROM")

    # compatibility edges: same category, high attribute similarity
    by_cat = {}
    for p in products:
        by_cat.setdefault(p.get("category"), []).append(p)

    for cat, items in by_cat.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                sim = _similarity(_numeric_attrs(a), _numeric_attrs(b))
                if sim >= COMPATIBILITY_THRESHOLD:
                    g.add_edge(a["id"], b["id"], relation="COMPATIBLE_WITH", similarity=round(sim, 2))
                    g.add_edge(b["id"], a["id"], relation="COMPATIBLE_WITH", similarity=round(sim, 2))

    return g


def compatible_products(product_id: str, products: list):
    g = build_graph(products)
    if product_id not in g:
        return []
    results = []
    for _, target, data in g.out_edges(product_id, data=True):
        if data.get("relation") == "COMPATIBLE_WITH":
            target_product = next((p for p in products if p["id"] == target), None)
            if target_product:
                results.append({
                    "id": target_product["id"],
                    "title": target_product["title"],
                    "similarity": data.get("similarity"),
                })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results


def graph_to_vis_json(products: list, focus_id: str = None):
    """Serialize the graph into {nodes, edges} for the frontend renderer.
    If focus_id is given, only include that product's ego-network so the
    per-product detail view isn't cluttered with the whole catalog.
    """
    g = build_graph(products)
    if focus_id and focus_id in g:
        neighbors = set(nx.all_neighbors(g, focus_id))
        keep = {focus_id} | neighbors
        g = g.subgraph(keep).copy()

    nodes = []
    for n, data in g.nodes(data=True):
        nodes.append({
            "id": n,
            "label": data.get("label", n),
            "type": data.get("type", "unknown"),
            "focus": n == focus_id,
        })
    edges = []
    seen = set()
    for u, v, data in g.edges(data=True):
        key = tuple(sorted([u, v])) + (data.get("relation"),)
        if key in seen:
            continue
        seen.add(key)
        edges.append({"from": u, "to": v, "relation": data.get("relation"), "similarity": data.get("similarity")})

    return {"nodes": nodes, "edges": edges}

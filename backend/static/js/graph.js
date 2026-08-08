// Deterministic radial "schematic" layout for the product knowledge graph.
// Deliberately orthogonal (right-angle) connector traces rather than an
// organic force-directed blob -- it reads as a circuit / engineering
// diagram, which fits an industrial product intelligence tool and avoids
// pulling in an external graph-viz dependency for a hackathon prototype.

function renderKnowledgeGraph(svgEl, data, focusId) {
  const W = 620, H = 420, CX = W / 2, CY = H / 2 + 6;
  svgEl.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svgEl.innerHTML = "";

  const byType = { category: [], document: [], product: [] };
  data.nodes.forEach(n => { (byType[n.type] || byType.product).push(n); });

  const focus = data.nodes.find(n => n.id === focusId) || data.nodes[0];
  const otherProducts = byType.product.filter(n => n.id !== (focus && focus.id));

  const positions = {};
  if (focus) positions[focus.id] = { x: CX, y: CY, node: focus };

  placeArc(byType.category, positions, CX, CY, 130, 200, 340); // top arc
  placeArc(byType.document, positions, CX, CY, 150, 20, 160);  // bottom-ish arc
  placeArc(otherProducts, positions, CX, CY, 190, -170, -10);  // side ring

  const ns = "http://www.w3.org/2000/svg";
  const edgeLayer = document.createElementNS(ns, "g");
  const nodeLayer = document.createElementNS(ns, "g");

  data.edges.forEach(e => {
    const a = positions[e.from], b = positions[e.to];
    if (!a || !b) return;
    const path = document.createElementNS(ns, "path");
    const midX = a.x + (b.x - a.x) * 0.5;
    const d = `M ${a.x} ${a.y} L ${midX} ${a.y} L ${midX} ${b.y} L ${b.x} ${b.y}`;
    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    const style = edgeStyle(e.relation);
    path.setAttribute("stroke", style.color);
    path.setAttribute("stroke-width", style.width);
    if (style.dash) path.setAttribute("stroke-dasharray", style.dash);
    path.setAttribute("opacity", "0.75");
    edgeLayer.appendChild(path);

    if (e.relation === "COMPATIBLE_WITH" && e.similarity) {
      const label = document.createElementNS(ns, "text");
      label.setAttribute("x", midX);
      label.setAttribute("y", (a.y + b.y) / 2 - 4);
      label.setAttribute("fill", "#4f46e5");
      label.setAttribute("font-size", "9");
      label.setAttribute("font-family", "IBM Plex Mono, monospace");
      label.setAttribute("text-anchor", "middle");
      label.textContent = Math.round(e.similarity * 100) + "%";
      edgeLayer.appendChild(label);
    }
  });

  Object.values(positions).forEach(p => nodeLayer.appendChild(drawNode(ns, p, p.node.id === (focus && focus.id))));

  svgEl.appendChild(edgeLayer);
  svgEl.appendChild(nodeLayer);
}

function placeArc(nodes, positions, cx, cy, radius, startDeg, endDeg) {
  if (!nodes.length) return;
  const step = nodes.length > 1 ? (endDeg - startDeg) / (nodes.length - 1) : 0;
  nodes.forEach((n, i) => {
    const deg = startDeg + step * i;
    const rad = (deg * Math.PI) / 180;
    positions[n.id] = { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) * 0.72, node: n };
  });
}

function edgeStyle(relation) {
  switch (relation) {
    case "COMPATIBLE_WITH": return { color: "#4f46e5", width: 1.8, dash: null };
    case "SOURCED_FROM": return { color: "#9ca3af", width: 1, dash: "3,3" };
    case "BELONGS_TO": return { color: "#d97706", width: 1.2, dash: null };
    default: return { color: "#c7c2b6", width: 1, dash: null };
  }
}

function nodeStyle(type) {
  switch (type) {
    case "product": return { fill: "#ffffff", stroke: "#4f46e5", shape: "rect", w: 96, h: 30 };
    case "category": return { fill: "#fdf1e0", stroke: "#d97706", shape: "rect", w: 84, h: 24 };
    case "document": return { fill: "#f3f1ec", stroke: "#9ca3af", shape: "circle", r: 5 };
    default: return { fill: "#ffffff", stroke: "#9ca3af", shape: "rect", w: 80, h: 24 };
  }
}

function drawNode(ns, pos, isFocus) {
  const g = document.createElementNS(ns, "g");
  const style = nodeStyle(pos.node.type);
  let shapeEl;
  if (style.shape === "circle") {
    shapeEl = document.createElementNS(ns, "circle");
    shapeEl.setAttribute("cx", pos.x);
    shapeEl.setAttribute("cy", pos.y);
    shapeEl.setAttribute("r", style.r);
  } else {
    shapeEl = document.createElementNS(ns, "rect");
    shapeEl.setAttribute("x", pos.x - style.w / 2);
    shapeEl.setAttribute("y", pos.y - style.h / 2);
    shapeEl.setAttribute("width", style.w);
    shapeEl.setAttribute("height", style.h);
    shapeEl.setAttribute("rx", 3);
  }
  shapeEl.setAttribute("fill", isFocus ? "#4f46e5" : style.fill);
  shapeEl.setAttribute("stroke", style.stroke);
  shapeEl.setAttribute("stroke-width", isFocus ? 2 : 1.2);
  g.appendChild(shapeEl);

  if (style.shape !== "circle") {
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", pos.x);
    text.setAttribute("y", pos.y + 4);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", "9.5");
    text.setAttribute("font-family", "IBM Plex Mono, monospace");
    text.setAttribute("fill", isFocus ? "#ffffff" : "#1f2430");
    text.textContent = truncate(pos.node.label, 16);
    g.appendChild(text);
  } else {
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", pos.x);
    text.setAttribute("y", pos.y - 9);
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", "8.5");
    text.setAttribute("font-family", "IBM Plex Mono, monospace");
    text.setAttribute("fill", "#6b7280");
    text.textContent = truncate(pos.node.label, 20);
    g.appendChild(text);
  }
  return g;
}

function truncate(s, n) {
  s = s || "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

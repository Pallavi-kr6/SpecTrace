const SpecTrace = (() => {

  async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    if (!res.ok) {
      let msg = res.statusText;
      try { const j = await res.json(); msg = j.detail || msg; } catch (e) {}
      throw new Error(msg);
    }
    return res.json();
  }

  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
  }

  function confidenceBadge(confidence, status) {
    let cls = "badge-green", label = `${Math.round(confidence * 100)}%`;
    if (status === "needs_review") { cls = "badge-amber"; }
    if (status === "inferred") { cls = "badge-amber"; label = `inferred · ${Math.round(confidence * 100)}%`; }
    if (confidence < 0.5) { cls = "badge-red"; }
    return `<span class="badge ${cls}">${label}</span>`;
  }

  function statCard(iconName, value, label, colorClass = "") {
    return `
      <div class="stat-card">
        <div class="stat-top">
          <div class="stat-icon ${colorClass}">${icon(iconName)}</div>
        </div>
        <div class="stat-value">${value}</div>
        <div class="stat-label">${label}</div>
      </div>`;
  }

  function gaugeRing(percent, color, size = 96) {
    const r = (size - 10) / 2;
    const c = 2 * Math.PI * r;
    const offset = c * (1 - percent);
    return `
      <div class="gauge-ring" style="width:${size}px;height:${size}px;">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
          <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="#f0eee8" stroke-width="8"/>
          <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="8"
            stroke-dasharray="${c}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
        </svg>
        <div class="gauge-ring-value">${Math.round(percent * 100)}%</div>
      </div>`;
  }

  async function loadMeta() {
    try {
      const meta = await fetchJSON("/api/meta");
      const badge = document.getElementById("llm-badge");
      if (badge) {
        if (meta.llm_available) {
          badge.innerHTML = `${icon("sparkles")} Groq LLM boost: on`;
          badge.className = "badge badge-indigo";
        } else {
          badge.innerHTML = "Offline rule-based engine";
          badge.className = "badge badge-muted";
        }
      }
    } catch (e) { /* non-fatal */ }
    try {
      const queue = await fetchJSON("/api/review-queue");
      const countEl = document.getElementById("nav-review-count");
      if (countEl) {
        if (queue.length > 0) { countEl.textContent = queue.length; countEl.hidden = false; }
        else { countEl.hidden = true; }
      }
    } catch (e) { /* non-fatal */ }
    return null;
  }

  function setupDropzone(zoneId, inputId, filenameId) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const filenameEl = document.getElementById(filenameId);
    if (!zone || !input) return;
    zone.addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
      filenameEl.textContent = input.files.length ? `Selected: ${input.files[0].name}` : "";
    });
    ["dragover", "dragenter"].forEach(evt => zone.addEventListener(evt, (e) => {
      e.preventDefault(); zone.classList.add("drag-over");
    }));
    ["dragleave", "drop"].forEach(evt => zone.addEventListener(evt, (e) => {
      e.preventDefault(); zone.classList.remove("drag-over");
    }));
    zone.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        filenameEl.textContent = `Selected: ${input.files[0].name}`;
      }
    });
  }

  // ---------------------------------------------------------------- home

  let currentProducts = [];
  let currentCategories = [];

  async function initHome() {
    loadMeta();
    loadStatRow();
    loadProductList();
    setupDropzone("dropzone-single", "file-input-single", "dz-filename-single");
    setupDropzone("dropzone-bulk", "file-input-bulk", "dz-filename-bulk");

    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
      });
    });

    document.getElementById("btn-seed").addEventListener("click", async () => {
      const btn = document.getElementById("btn-seed");
      btn.disabled = true; btn.textContent = "Loading sample catalog…";
      try {
        await fetchJSON("/api/seed", { method: "POST" });
        await Promise.all([loadProductList(), loadStatRow(), loadMeta()]);
        showToast("Sample catalog loaded.", "success");
      } catch (e) {
        showToast("Could not load sample catalog: " + e.message, "error");
      } finally {
        btn.disabled = false; btn.textContent = "Load sample catalog";
      }
    });

    document.getElementById("btn-reset").addEventListener("click", () => {
      showConfirmModal({
        title: "Reset all data?",
        message: "This clears every product and review item. This can't be undone.",
        confirmLabel: "Reset everything",
        danger: true,
        onConfirm: async () => {
          await fetchJSON("/api/reset", { method: "POST" });
          await Promise.all([loadProductList(), loadStatRow(), loadMeta()]);
          showToast("Catalog reset.", "info");
        },
      });
    });

    document.getElementById("ingest-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.target;
      const submitBtn = form.querySelector("button[type=submit]");
      const traceBox = document.getElementById("pipeline-trace");
      traceBox.hidden = false;
      traceBox.innerHTML = `<div class="trace-step" style="animation-delay:0s"><span class="trace-agent">Pipeline</span><span class="trace-detail">running…</span></div>`;
      submitBtn.disabled = true;

      try {
        const fd = new FormData(form);
        const product = await fetchJSON("/api/products", { method: "POST", body: fd });
        traceBox.innerHTML = "";
        (product.pipeline_trace || []).forEach((step, i) => {
          const div = document.createElement("div");
          div.className = "trace-step";
          div.style.animationDelay = `${i * 0.07}s`;
          div.innerHTML = `<span class="trace-agent">${escapeHtml(step.agent)}</span><span class="trace-detail">${escapeHtml(step.detail)}</span>`;
          traceBox.appendChild(div);
        });
        const goLine = document.createElement("div");
        goLine.className = "trace-step";
        goLine.style.animationDelay = `${(product.pipeline_trace || []).length * 0.07 + 0.1}s`;
        goLine.innerHTML = `<span class="trace-agent" style="color:#0d9488">Done</span><span class="trace-detail">Opening <a href="/products/${product.id}">${escapeHtml(product.title)}</a> →</span>`;
        traceBox.appendChild(goLine);
        showToast(`${escapeHtml(product.title)} created.`, "success");
        setTimeout(() => { window.location.href = `/products/${product.id}`; }, 900);
      } catch (err) {
        traceBox.innerHTML = `<div class="trace-step"><span class="trace-agent" style="color:#dc2626">Error</span><span class="trace-detail">${escapeHtml(err.message)}</span></div>`;
        showToast("Could not process that product: " + err.message, "error");
      } finally {
        submitBtn.disabled = false;
      }
    });

    document.getElementById("bulk-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = e.target;
      const submitBtn = form.querySelector("button[type=submit]");
      const resultBox = document.getElementById("bulk-result");
      submitBtn.disabled = true;
      resultBox.innerHTML = `<p class="empty-note">Running every row through the pipeline…</p>`;
      try {
        const fd = new FormData(form);
        const summary = await fetchJSON("/api/products/bulk", { method: "POST", body: fd });
        const rows = summary.results.map(r => {
          if (r.status === "ok") {
            return `<div class="trace-step"><span class="trace-agent" style="color:#0d9488">${icon("checkCircle")} Row ${r.row}</span><span class="trace-detail"><a href="/products/${r.id}">${escapeHtml(r.title)}</a> — ${r.attribute_count} attributes, ${r.needs_review_count} need review</span></div>`;
          }
          return `<div class="trace-step"><span class="trace-agent" style="color:#dc2626">${icon("alert")} Row ${r.row}</span><span class="trace-detail">${escapeHtml(r.detail)}</span></div>`;
        }).join("");
        resultBox.innerHTML = `
          <div class="pipeline-trace" style="border-top:none;padding-top:6px;">
            <p style="font-weight:700;margin:0 0 6px;">Imported ${summary.created}/${summary.processed} products
              (${summary.total_needs_review} attributes flagged for review)</p>
            ${rows}
          </div>`;
        showToast(`Bulk import complete: ${summary.created} products created.`, "success");
        await Promise.all([loadProductList(), loadStatRow(), loadMeta()]);
      } catch (err) {
        resultBox.innerHTML = `<p class="empty-note">Import failed: ${escapeHtml(err.message)}</p>`;
        showToast("Bulk import failed: " + err.message, "error");
      } finally {
        submitBtn.disabled = false;
      }
    });

    document.getElementById("search-input").addEventListener("input", debounce(applyFilters, 250));
    document.getElementById("filter-category").addEventListener("change", applyFilters);
    document.getElementById("filter-status").addEventListener("change", applyFilters);
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  async function loadStatRow() {
    const row = document.getElementById("stat-row");
    try {
      const dash = await fetchJSON("/api/dashboard");
      row.innerHTML =
        statCard("boxes", dash.total_products, "Products in catalog", "") +
        statCard("checkCircle", `${Math.round(dash.avg_confidence * 100)}%`, "Average confidence", "teal") +
        statCard("clock", dash.total_needs_review, "Attributes pending review", dash.total_needs_review > 0 ? "amber" : "teal") +
        statCard("leaf", `${Math.round(dash.avg_dpp_readiness * 100)}%`, "Avg. DPP readiness", "");
    } catch (e) { row.innerHTML = ""; }
  }

  async function applyFilters() {
    const q = document.getElementById("search-input").value.trim();
    const category = document.getElementById("filter-category").value;
    const status = document.getElementById("filter-status").value;
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    if (status) params.set("status", status);
    const products = await fetchJSON(`/api/products?${params.toString()}`);
    renderProductTable(products);
  }

  async function loadProductList() {
    const meta = await fetchJSON("/api/meta").catch(() => ({ categories: [] }));
    currentCategories = meta.categories || [];
    const catSelect = document.getElementById("filter-category");
    if (catSelect && catSelect.options.length <= 1) {
      currentCategories.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id; opt.textContent = c.label;
        catSelect.appendChild(opt);
      });
    }
    const products = await fetchJSON("/api/products");
    currentProducts = products;
    document.getElementById("filter-bar").hidden = products.length === 0;
    renderProductTable(products);
  }

  function renderProductTable(products) {
    const wrap = document.getElementById("product-list");
    if (!products.length) {
      wrap.innerHTML = `
        <div class="empty-state">
          ${icon("boxes")}
          <h3>No products match yet</h3>
          <p>Load the sample catalog, ingest a product above, or adjust your filters.</p>
        </div>`;
      return;
    }
    const rows = products.map(p => `
      <tr>
        <td>
          <a class="row-link" href="/products/${p.id}">${escapeHtml(p.title)}</a><br>
          <span class="badge badge-muted">${escapeHtml(p.category_label)}</span>
          ${p.etim_class ? `<span class="badge badge-indigo">${icon("tag")} ETIM</span>` : ""}
        </td>
        <td>${p.attribute_count}</td>
        <td>${confidenceBadge(p.avg_confidence, "")}</td>
        <td>${p.needs_review_count > 0 ? `<span class="badge badge-amber">${p.needs_review_count} pending</span>` : `<span class="badge badge-green">${icon("check")} clear</span>`}</td>
        <td>${icon("leaf")} ${Math.round((p.dpp_score || 0) * 100)}%</td>
        <td><a class="btn btn-small btn-ghost" href="/api/products/${p.id}/export">Export</a></td>
      </tr>
    `).join("");
    wrap.innerHTML = `
      <table class="product-table">
        <thead><tr><th>Product</th><th>Attributes</th><th>Confidence</th><th>Review status</th><th>DPP</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  // ------------------------------------------------------- product detail

  async function initProductDetail(productId) {
    loadMeta();
    const root = document.getElementById("product-detail-root");
    let product, reviewQueue;
    try {
      [product, reviewQueue] = await Promise.all([
        fetchJSON(`/api/products/${productId}`),
        fetchJSON("/api/review-queue"),
      ]);
    } catch (e) {
      root.innerHTML = `<div class="empty-state">${icon("alert")}<h3>Could not load product</h3><p>${escapeHtml(e.message)}</p></div>`;
      return;
    }
    renderProductDetail(root, product, reviewQueue);
  }

  function renderProductDetail(root, product, reviewQueue) {
    const reviewByAttr = {};
    reviewQueue.filter(r => r.product_id === product.id).forEach(r => { reviewByAttr[r.attr_id] = r; });

    const attrRows = product.attributes.map(a => {
      const review = reviewByAttr[a.attr_id];
      const valueStr = `${a.value}${a.unit ? " " + a.unit : ""}`;
      const sourceStr = a.source.page
        ? `p.${a.source.page}${a.source.line_no ? ":" + a.source.line_no : ""} · ${escapeHtml(a.source.document)}`
        : escapeHtml(a.source.snippet || a.source.document || "graph inference");
      let actions = "";
      if (review) {
        actions = `
          <div class="attr-actions">
            <input class="review-edit-input" placeholder="corrected value" data-edit-for="${review.review_id}" />
            <button class="btn btn-small btn-ghost" data-action="edit" data-review="${review.review_id}">${icon("edit")} Save</button>
            <button class="btn btn-small btn-ghost" data-action="approve" data-review="${review.review_id}">${icon("check")} Approve</button>
            <button class="btn btn-small btn-danger" data-action="reject" data-review="${review.review_id}">${icon("trash")} Reject</button>
          </div>`;
      }
      return `
        <div class="attr-row">
          <div class="attr-name">${escapeHtml(a.display_name)}<small>${escapeHtml(a.canonical)} · ${escapeHtml(a.extraction_method)}</small></div>
          <div class="attr-value">${escapeHtml(valueStr)}</div>
          <div class="attr-source">${confidenceBadge(a.confidence, a.status)}<br><span class="leader">↳</span> ${sourceStr}</div>
          ${actions}
        </div>`;
    }).join("");

    const compatItems = (product.compatible_products || []).map(c => `
      <div class="compat-item">
        <a href="/products/${c.id}">${escapeHtml(c.title)}</a>
        <span class="badge badge-indigo">${Math.round(c.similarity * 100)}% match</span>
      </div>`).join("") || `<p class="empty-note">No close matches yet — add more products in this category.</p>`;

    const cls = product.classification;
    const classificationHtml = cls ? `
      <div class="classif-row">
        <div><div style="font-weight:600;">ETIM class</div><div class="classif-label">${escapeHtml(cls.etim_label || "—")}</div></div>
        ${cls.etim_class ? `<span class="classif-code">${escapeHtml(cls.etim_class)}</span>` : `<span class="badge badge-muted">not mapped</span>`}
      </div>
      <div class="classif-row">
        <div><div style="font-weight:600;">UNSPSC code</div><div class="classif-label">${escapeHtml(cls.unspsc_label || "—")}</div></div>
        <span class="classif-code">${escapeHtml(cls.unspsc_code || "—")}</span>
      </div>` : `<p class="empty-note">No classification mapping for this category yet.</p>`;

    const dpp = product.dpp_readiness || { score: 0, present: [], missing: [], context: {} };
    const gaugeColor = dpp.score >= 0.75 ? "#0d9488" : dpp.score >= 0.4 ? "#d97706" : "#dc2626";
    const dppFieldRows = [
      ...dpp.present.map(canon => `<div class="dpp-field-row present">${icon("check", "present")} ${escapeHtml(canon.replace(/_/g, " "))}</div>`),
      ...dpp.missing.map(m => `<div class="dpp-field-row missing">${icon("x", "missing")} ${escapeHtml(m.display_name)}</div>`),
    ].join("");
    const dppHtml = `
      <div class="dpp-gauge-wrap">
        ${gaugeRing(dpp.score, gaugeColor, 72)}
        <div>
          <div class="dpp-gauge-value">${dpp.present.length}/${dpp.total_fields} fields</div>
          <div class="dpp-gauge-label">EU Digital Product Passport readiness</div>
        </div>
      </div>
      ${dppFieldRows}
      <div class="dpp-note">${escapeHtml((dpp.context && dpp.context.note) || "")}</div>`;

    root.innerHTML = `
      <div class="detail-head">
        <div>
          <h1>${escapeHtml(product.title)}</h1>
          <div class="detail-meta">
            <span class="badge badge-muted">${escapeHtml(product.category_label)}</span>
            <span class="badge badge-muted">${product.attributes.length} attributes</span>
            <span class="badge ${product.needs_review_count > 0 ? "badge-amber" : "badge-green"}">${product.needs_review_count > 0 ? product.needs_review_count + " need review" : icon("check") + " fully verified"}</span>
          </div>
          ${product.description ? `<p class="detail-desc">${escapeHtml(product.description)}</p>` : ""}
        </div>
        <div class="panel-actions">
          <a class="btn btn-ghost" href="/api/products/${product.id}/export">${icon("file")} Export JSON</a>
          <a class="btn btn-ghost" href="/">← Catalog</a>
        </div>
      </div>

      <div class="detail-grid">
        <div>
          <div class="panel" style="margin-bottom:0">
            <div class="panel-head"><h2>${icon("layers")} Attributes &amp; provenance</h2></div>
            <div id="attr-list">${attrRows}</div>
          </div>
        </div>
        <div>
          <div class="side-panel">
            <h3>${icon("tag")} Classification &amp; standards</h3>
            ${classificationHtml}
          </div>
          <div class="side-panel">
            <h3>${icon("leaf")} Compliance readiness</h3>
            ${dppHtml}
          </div>
          <div class="side-panel">
            <h3>${icon("link")} Compatible / interchangeable</h3>
            ${compatItems}
          </div>
          <div class="side-panel">
            <h3>${icon("grid")} Knowledge graph</h3>
            <div class="graph-wrap"><svg id="graph-svg" width="100%" height="260"></svg></div>
            <div class="graph-legend">
              <span><span class="legend-dot" style="background:#4f46e5"></span>this product</span>
              <span><span class="legend-dot" style="background:#d97706"></span>category</span>
              <span><span class="legend-dot" style="background:#9ca3af"></span>source document</span>
            </div>
          </div>
          <div class="side-panel">
            <h3>${icon("clock")} Pipeline trace</h3>
            ${(product.pipeline_trace || []).map(s => `<div class="trace-step" style="animation:none;opacity:1"><span class="trace-agent">${escapeHtml(s.agent)}</span><span class="trace-detail">${escapeHtml(s.detail)}</span></div>`).join("")}
          </div>
        </div>
      </div>
    `;

    root.querySelectorAll("[data-action]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const action = btn.dataset.action;
        const reviewId = btn.dataset.review;
        const fd = new FormData();
        fd.append("action", action);
        if (action === "edit") {
          const input = root.querySelector(`[data-edit-for="${reviewId}"]`);
          fd.append("new_value", input ? input.value : "");
        }
        btn.disabled = true;
        try {
          await fetchJSON(`/api/review/${reviewId}/resolve`, { method: "POST", body: fd });
          const [freshProduct, freshQueue] = await Promise.all([
            fetchJSON(`/api/products/${product.id}`),
            fetchJSON("/api/review-queue"),
          ]);
          renderProductDetail(root, freshProduct, freshQueue);
          loadMeta();
          showToast(action === "approve" ? "Attribute approved." : action === "reject" ? "Attribute removed." : "Attribute updated.", "success");
        } catch (e) {
          showToast("Could not resolve review item: " + e.message, "error");
          btn.disabled = false;
        }
      });
    });

    fetchJSON(`/api/products/${product.id}/graph`).then(graphData => {
      const svg = document.getElementById("graph-svg");
      if (svg && window.renderKnowledgeGraph) renderKnowledgeGraph(svg, graphData, product.id);
    }).catch(() => {});
  }

  // -------------------------------------------------------- review queue

  async function initReviewQueue() {
    loadMeta();
    const wrap = document.getElementById("review-list");
    const items = await fetchJSON("/api/review-queue");
    renderReviewList(wrap, items);
  }

  function renderReviewList(wrap, items) {
    if (!items.length) {
      wrap.innerHTML = `
        <div class="empty-state">
          ${icon("checkCircle")}
          <h3>All caught up</h3>
          <p>Every attribute in the catalog is verified or auto-published above the confidence threshold.</p>
        </div>`;
      return;
    }
    wrap.innerHTML = items.map(r => `
      <div class="review-item" data-review-id="${r.review_id}">
        <div>
          <div class="review-title"><a href="/products/${r.product_id}">${escapeHtml(r.product_title)}</a></div>
          <div class="review-attr">${escapeHtml(r.display_name)}: <span class="val">${escapeHtml(String(r.value))}${r.unit ? " " + escapeHtml(r.unit) : ""}</span> ${confidenceBadge(r.confidence, r.status)}</div>
          <div class="review-reason">${escapeHtml(r.reason)}</div>
        </div>
        <div class="review-actions">
          <input class="review-edit-input" placeholder="corrected value" />
          <button class="btn btn-small btn-ghost" data-action="edit">${icon("edit")} Save</button>
          <button class="btn btn-small btn-ghost" data-action="approve">${icon("check")} Approve</button>
          <button class="btn btn-small btn-danger" data-action="reject">${icon("trash")} Reject</button>
        </div>
      </div>
    `).join("");

    wrap.querySelectorAll(".review-item").forEach(row => {
      const reviewId = row.dataset.reviewId;
      row.querySelectorAll("[data-action]").forEach(btn => {
        btn.addEventListener("click", async () => {
          const action = btn.dataset.action;
          const fd = new FormData();
          fd.append("action", action);
          if (action === "edit") {
            fd.append("new_value", row.querySelector(".review-edit-input").value);
          }
          row.querySelectorAll("button").forEach(b => b.disabled = true);
          try {
            await fetchJSON(`/api/review/${reviewId}/resolve`, { method: "POST", body: fd });
            const items = await fetchJSON("/api/review-queue");
            renderReviewList(wrap, items);
            loadMeta();
            showToast(action === "approve" ? "Attribute approved." : action === "reject" ? "Attribute removed." : "Attribute updated.", "success");
          } catch (e) {
            showToast("Could not resolve review item: " + e.message, "error");
            row.querySelectorAll("button").forEach(b => b.disabled = false);
          }
        });
      });
    });
  }

  // ------------------------------------------------------------ dashboard

  async function initDashboard() {
    loadMeta();
    const statRow = document.getElementById("dash-stat-row");
    const catBox = document.getElementById("dash-categories");
    const compBox = document.getElementById("dash-compliance");
    let dash;
    try {
      dash = await fetchJSON("/api/dashboard");
    } catch (e) {
      statRow.innerHTML = `<div class="empty-state">${icon("alert")}<h3>Could not load dashboard</h3><p>${escapeHtml(e.message)}</p></div>`;
      return;
    }

    if (!dash.total_products) {
      statRow.innerHTML = "";
      catBox.innerHTML = `<div class="empty-state">${icon("boxes")}<h3>No data yet</h3><p>Load the sample catalog or ingest a product from the Catalog page.</p></div>`;
      compBox.innerHTML = "";
      return;
    }

    statRow.innerHTML =
      statCard("boxes", dash.total_products, "Products in catalog", "") +
      statCard("checkCircle", `${Math.round(dash.avg_confidence * 100)}%`, "Average confidence", "teal") +
      statCard("clock", dash.total_needs_review, "Attributes pending review", dash.total_needs_review > 0 ? "amber" : "teal") +
      statCard("tag", `${Math.round(dash.classification_coverage * 100)}%`, "ETIM/UNSPSC classified", "");

    const maxCount = Math.max(...dash.categories.map(c => c.count));
    catBox.innerHTML = dash.categories.map(c => `
      <div class="cat-bar-row">
        <div class="cat-bar-head"><span>${escapeHtml(c.category_label)}</span><span>${c.count} products</span></div>
        <div class="cat-bar-track"><div class="cat-bar-fill" style="width:${Math.round((c.count / maxCount) * 100)}%"></div></div>
        <div class="cat-bar-meta">
          <span>${icon("checkCircle")} ${Math.round(c.avg_confidence * 100)}% avg confidence</span>
          <span>${c.needs_review > 0 ? icon("alert") + " " + c.needs_review + " pending review" : icon("check") + " all clear"}</span>
        </div>
      </div>
    `).join("");

    compBox.innerHTML = `
      <div style="display:flex; gap:24px; align-items:center; flex-wrap:wrap;">
        <div style="text-align:center;">
          ${gaugeRing(dash.classification_coverage, "#4f46e5", 84)}
          <div style="font-size:12px; color:var(--text-muted); margin-top:8px; max-width:120px;">ETIM/UNSPSC classification coverage</div>
        </div>
        <div style="text-align:center;">
          ${gaugeRing(dash.avg_dpp_readiness, "#0d9488", 84)}
          <div style="font-size:12px; color:var(--text-muted); margin-top:8px; max-width:120px;">Avg. Digital Product Passport readiness</div>
        </div>
      </div>
      <p class="dpp-note" style="margin-top:20px;">Every product gets a deterministic ETIM + UNSPSC code the moment its
        category is identified — that's why classification coverage tracks 1:1 with catalog completeness. DPP readiness
        tracks four EU ESPR-relevant fields (country of origin, recyclability, hazardous-substance declaration, carbon
        footprint) that are optional today but phasing in as mandatory by category between 2026 and 2030.</p>`;
  }

  return { initHome, initProductDetail, initReviewQueue, initDashboard };
})();

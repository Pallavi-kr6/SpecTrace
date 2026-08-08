// Lightweight toast + confirm-modal system. Replaces native alert()/confirm()
// which feel jarring and block the whole page.

function ensureToastRoot() {
  let root = document.getElementById("toast-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "toast-root";
    root.className = "toast-root";
    document.body.appendChild(root);
  }
  return root;
}

function showToast(message, type = "info", timeout = 4200) {
  const root = ensureToastRoot();
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  const iconName = type === "success" ? "checkCircle" : type === "error" ? "alert" : "sparkles";
  el.innerHTML = `${icon(iconName)}<span>${message}</span><button class="toast-close" aria-label="Dismiss">${icon("x")}</button>`;
  root.appendChild(el);
  requestAnimationFrame(() => el.classList.add("toast-in"));

  const remove = () => {
    el.classList.remove("toast-in");
    setTimeout(() => el.remove(), 200);
  };
  el.querySelector(".toast-close").addEventListener("click", remove);
  if (timeout) setTimeout(remove, timeout);
}

function showConfirmModal({ title, message, confirmLabel = "Confirm", danger = false, onConfirm }) {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.innerHTML = `
    <div class="modal-card" role="dialog" aria-modal="true">
      <h3>${title}</h3>
      <p>${message}</p>
      <div class="modal-actions">
        <button class="btn btn-ghost" data-act="cancel">Cancel</button>
        <button class="btn ${danger ? "btn-danger-solid" : "btn-primary"}" data-act="confirm">${confirmLabel}</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
  requestAnimationFrame(() => overlay.classList.add("modal-in"));

  const close = () => { overlay.classList.remove("modal-in"); setTimeout(() => overlay.remove(), 150); };
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  overlay.querySelector('[data-act="cancel"]').addEventListener("click", close);
  overlay.querySelector('[data-act="confirm"]').addEventListener("click", () => { close(); onConfirm && onConfirm(); });
}

// Minimal line-icon set, Feather/Lucide-style strokes, hand-authored so the
// app has zero external icon-library dependency. All icons are 24x24,
// stroke=currentColor so they inherit text color automatically.

const ICONS = {
  upload: '<path d="M12 16V4M12 4l-4 4M12 4l4 4"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/>',
  alert: '<path d="M12 9v4"/><circle cx="12" cy="16.5" r="0.5" fill="currentColor"/><path d="M10.3 3.9 2.5 17a2 2 0 0 0 1.7 3h15.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  x: '<path d="M18 6 6 18"/><path d="M6 6l12 12"/>',
  tag: '<path d="M12.6 2H4a2 2 0 0 0-2 2v8.6a2 2 0 0 0 .6 1.4l9 9a2 2 0 0 0 2.8 0l7.6-7.6a2 2 0 0 0 0-2.8l-9-9A2 2 0 0 0 12.6 2Z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  leaf: '<path d="M11 20A7 7 0 0 1 4 13c0-5 4-9 9-11 1 5 3 7 3 11a7 7 0 0 1-5 7Z"/><path d="M11 20c0-6 2-10 6-13"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  link: '<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><path d="M8 12h8"/>',
  layers: '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
  arrowRight: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  sparkles: '<path d="M12 3v4"/><path d="M12 17v4"/><path d="M3 12h4"/><path d="M17 12h4"/><path d="m6 6 2 2"/><path d="m16 16 2 2"/><path d="m6 18 2-2"/><path d="m16 8 2-2"/>',
  boxes: '<path d="M2.5 8.5 12 3l9.5 5.5v9L12 23l-9.5-5.5Z"/><path d="M12 12v11"/><path d="m2.5 8.5 9.5 5.5 9.5-5.5"/>',
  package: '<path d="m21 8-9-5-9 5v8l9 5 9-5Z"/><path d="M3.3 8.6 12 13l8.7-4.4"/><path d="M12 22V13"/>',
};

function icon(name, cls = "") {
  const body = ICONS[name] || "";
  return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
}

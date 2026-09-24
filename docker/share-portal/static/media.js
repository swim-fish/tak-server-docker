"use strict";
const form = document.getElementById("publisher-form");
const cards = [...document.querySelectorAll("#publisher-cards > article")];
const search = document.getElementById("media-search");
let statusFilter = "all";
function refresh() {
  const term = search.value.trim().toLocaleLowerCase();
  let visible = 0;
  for (const card of cards) {
    const statusMatches = statusFilter === "all" || card.dataset.enabled === (statusFilter === "enabled" ? "yes" : "no");
    card.hidden = !statusMatches || !card.dataset.search.toLocaleLowerCase().includes(term);
    if (card.hidden) card.querySelector('input[name="publisher"]').checked = false;
    if (!card.hidden) visible++;
  }
  const selected = form.querySelectorAll('input[name="publisher"]:checked').length;
  const selectedCards = cards.filter((card) => card.querySelector('input[name="publisher"]').checked);
  document.getElementById("media-count").textContent = `顯示 ${visible}／總計 ${cards.length}；隱藏 ${cards.length - visible}；已選 ${selected}`;
  form.querySelectorAll('button[type="submit"]').forEach((button) => {
    button.disabled = selected === 0 || (button.value === "reshare" &&
      !selectedCards.every((card) => card.dataset.kind === "squad" && card.dataset.enabled === "yes"));
  });
}
search.addEventListener("input", refresh);
document.querySelectorAll("[data-media-status]").forEach((button) => button.addEventListener("click", () => {
  statusFilter = button.dataset.mediaStatus;
  document.querySelectorAll("[data-media-status]").forEach((option) => {
    const selected = option === button;
    option.classList.toggle("active", selected);
    option.setAttribute("aria-pressed", String(selected));
  });
  refresh();
}));
form.addEventListener("change", refresh);
document.getElementById("media-select-visible").addEventListener("click", () => { cards.forEach((card) => { if (!card.hidden) card.querySelector('input[name="publisher"]').checked = true; }); refresh(); });
document.getElementById("media-select-none").addEventListener("click", () => { cards.forEach((card) => card.querySelector('input[name="publisher"]').checked = false); refresh(); });
refresh();
document.querySelectorAll("[data-preview-url]").forEach((button) => button.addEventListener("click", () => {
  const panel = document.getElementById("media-preview");
  const frame = document.getElementById("media-preview-frame");
  frame.src = button.dataset.previewUrl;
  panel.hidden = false;
  panel.scrollIntoView({behavior: "smooth", block: "nearest"});
}));
document.getElementById("media-preview-close").addEventListener("click", () => {
  const frame = document.getElementById("media-preview-frame");
  frame.removeAttribute("src");
  document.getElementById("media-preview").hidden = true;
});
const viewerStatus = document.getElementById("viewer-live-status");
function setViewerStatus(label, sessions, kind) {
  const badge = document.createElement("span");
  badge.className = `badge status-badge ${kind}`;
  badge.textContent = label;
  const detail = document.createElement("span");
  detail.textContent = sessions === null ? " 公開觀看狀態暫時無法更新" : ` 目前 ${sessions} 個公開觀看工作階段`;
  viewerStatus.replaceChildren(badge, detail);
}
async function refreshViewerStatus() {
  if (!viewerStatus || document.hidden) return;
  try {
    const response = await fetch("/media/status", {cache: "no-store"});
    if (!response.ok) throw new Error("status unavailable");
    const state = await response.json();
    setViewerStatus(state.desired ? "已開啟" : "已關閉", state.sessions,
      state.desired ? "text-bg-success" : "text-bg-secondary");
  } catch (_error) {
    setViewerStatus("更新失敗", null, "text-bg-warning");
  }
}
setInterval(refreshViewerStatus, 3000);
document.addEventListener("visibilitychange", refreshViewerStatus);

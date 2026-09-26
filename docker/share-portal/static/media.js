"use strict";
const form = document.getElementById("publisher-form");
const entries = [...document.querySelectorAll("[data-media-entry]")];
const search = document.getElementById("media-search");
const pageSizeInput = document.getElementById("media-page-size");
const previousPage = document.getElementById("media-page-prev");
const nextPage = document.getElementById("media-page-next");
const pageIndicator = document.getElementById("media-page-indicator");
let statusFilter = form.dataset.defaultStatus;
let currentPage = 1;
function refresh() {
  const term = search.value.trim().toLocaleLowerCase();
  const matches = entries.filter((entry) => {
    const statusMatches = statusFilter === "all" || entry.dataset.enabled === (statusFilter === "enabled" ? "yes" : "no");
    return statusMatches && entry.dataset.search.toLocaleLowerCase().includes(term);
  });
  const pageSize = pageSizeInput ? Number(pageSizeInput.value) : Math.max(1, matches.length);
  const pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
  currentPage = Math.min(currentPage, pageCount);
  const visible = matches.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  for (const entry of entries) {
    entry.hidden = !visible.includes(entry);
    if (entry.hidden) entry.querySelector('input[name="publisher"]').checked = false;
  }
  const selected = form.querySelectorAll('input[name="publisher"]:checked').length;
  const selectedEntries = visible.filter((entry) => entry.querySelector('input[name="publisher"]').checked);
  const selectedPaths = selectedEntries.flatMap((entry) => [...entry.querySelectorAll('input[name="reshare_path"]')]);
  for (const entry of entries) {
    const pathEnabled = entry.querySelector('input[name="publisher"]').checked && entry.dataset.enabled === "yes";
    entry.querySelectorAll('input[name="reshare_path"]').forEach((path) => { path.disabled = !pathEnabled; });
  }
  const pathCount = document.getElementById("media-path-count");
  if (pathCount) pathCount.textContent = `已選 ${selectedPaths.filter((path) => path.checked).length}／${selectedPaths.length} 條路徑`;
  document.getElementById("media-count").textContent = pageSizeInput
    ? `顯示 ${visible.length}／符合搜尋 ${matches.length}／總計 ${entries.length}；已選 ${selected}`
    : `顯示 ${visible.length}／總計 ${entries.length}；隱藏 ${entries.length - visible.length}；已選 ${selected}`;
  const empty = document.getElementById("media-empty");
  if (empty) empty.hidden = matches.length !== 0;
  if (pageIndicator) pageIndicator.textContent = `${currentPage}／${pageCount} 頁`;
  if (previousPage) previousPage.disabled = currentPage === 1;
  if (nextPage) nextPage.disabled = currentPage === pageCount;
  form.querySelectorAll('button[type="submit"]').forEach((button) => {
    button.disabled = selected === 0 ||
      (button.value === "reshare" && (!selectedEntries.every((entry) => entry.dataset.enabled === "yes") ||
        !selectedPaths.some((path) => path.checked))) ||
      (button.value === "reset" && !selectedEntries.every((entry) => entry.dataset.enabled === "yes"));
  });
}
search.addEventListener("input", () => { currentPage = 1; refresh(); });
document.querySelectorAll("[data-media-status]").forEach((button) => button.addEventListener("click", () => {
  statusFilter = button.dataset.mediaStatus;
  currentPage = 1;
  document.querySelectorAll("[data-media-status]").forEach((option) => {
    const selected = option === button;
    option.classList.toggle("active", selected);
    option.setAttribute("aria-pressed", String(selected));
  });
  refresh();
}));
form.addEventListener("change", refresh);
if (pageSizeInput) pageSizeInput.addEventListener("change", () => { currentPage = 1; refresh(); });
if (previousPage) previousPage.addEventListener("click", () => { currentPage--; refresh(); });
if (nextPage) nextPage.addEventListener("click", () => { currentPage++; refresh(); });
document.getElementById("media-select-visible").addEventListener("click", () => { entries.forEach((entry) => { if (!entry.hidden) entry.querySelector('input[name="publisher"]').checked = true; }); refresh(); });
document.getElementById("media-select-none").addEventListener("click", () => { entries.forEach((entry) => entry.querySelector('input[name="publisher"]').checked = false); refresh(); });
const selectAllPaths = document.getElementById("media-path-select-all");
const selectNoPaths = document.getElementById("media-path-select-none");
if (selectAllPaths && selectNoPaths) {
  const choosePaths = (checked) => {
    entries.filter((entry) => !entry.hidden && entry.querySelector('input[name="publisher"]').checked)
      .forEach((entry) => entry.querySelectorAll('input[name="reshare_path"]').forEach((path) => {
        path.checked = checked;
      }));
    refresh();
  };
  selectAllPaths.addEventListener("click", () => choosePaths(true));
  selectNoPaths.addEventListener("click", () => choosePaths(false));
}
refresh();
const reactivateModal = document.getElementById("device-reactivate");
if (reactivateModal) reactivateModal.addEventListener("show.bs.modal", (event) => {
  const button = event.relatedTarget;
  reactivateModal.querySelector("#device-reactivate-key").value = button.dataset.reactivateKey;
  reactivateModal.querySelector("#device-reactivate-name").textContent = button.dataset.reactivateName;
  reactivateModal.querySelector('input[value="rotate"]').checked = true;
  reactivateModal.querySelector('input[name="confirmation"]').checked = false;
});
const thumbnails = [...document.querySelectorAll("[data-thumbnail-url]")];
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((observations) => {
    for (const {target, isIntersecting} of observations) {
      if (isIntersecting && !target.hasAttribute("src")) target.src = target.dataset.thumbnailUrl;
      if (!isIntersecting && target.hasAttribute("src")) target.removeAttribute("src");
    }
  }, {rootMargin: "100px 0px"});
  thumbnails.forEach((frame) => observer.observe(frame));
} else {
  thumbnails.forEach((frame) => { frame.src = frame.dataset.thumbnailUrl; });
}
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
const squadLiveBadges = [...document.querySelectorAll("[data-squad-live]")];
const livePathBadges = [...document.querySelectorAll("[data-live-path]")];
async function refreshSquadStreams() {
  if ((!squadLiveBadges.length && !livePathBadges.length) || document.hidden) return;
  try {
    const response = await fetch("/media/squads/status", {cache: "no-store"});
    if (!response.ok) throw new Error("squad stream status unavailable");
    const {counts, paths} = await response.json();
    const activePaths = new Set(paths);
    for (const badge of squadLiveBadges) {
      const count = Number(counts[badge.dataset.squadLive] || 0);
      badge.hidden = count < 1;
      badge.textContent = `串流中 · ${count}`;
    }
    livePathBadges.forEach((badge) => { badge.hidden = !activePaths.has(badge.dataset.livePath); });
  } catch (_error) {
    squadLiveBadges.forEach((badge) => { badge.hidden = true; });
    livePathBadges.forEach((badge) => { badge.hidden = true; });
  }
}
refreshSquadStreams();
setInterval(refreshSquadStreams, 3000);
document.addEventListener("visibilitychange", refreshSquadStreams);

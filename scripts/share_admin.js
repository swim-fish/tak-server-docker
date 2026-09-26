"use strict";

const byId = (id) => document.getElementById(id);
const csrf = document.querySelector("#master-form input[name=csrf]").value;
let requestPending = false;
let lastSources = "";
let clockOffsetMs = Date.now() - Number(byId("share-rows").dataset.serverNow) * 1000;
let currentQrShareId = null;
let recordItems = [];
let recordPage = 1;
let shareStatusFilter = "all";

function shareStatusCategory(item) {
  if (item.status === "已手動停止") return "stopped";
  if (item.status === "時間到期" || item.status === "次數額滿") return "expired";
  return "active";
}

function remainingText(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor(seconds % 86400 / 3600);
  const minutes = Math.floor(seconds % 3600 / 60);
  const rest = seconds % 60;
  const pair = (number) => String(number).padStart(2, "0");
  if (days) return `剩餘 ${days} 天 ${pair(hours)}:${pair(minutes)}:${pair(rest)}`;
  if (hours) return `剩餘 ${hours}:${pair(minutes)}:${pair(rest)}`;
  return `剩餘 ${pair(minutes)}:${pair(rest)}`;
}

function updateCountdowns() {
  for (const status of document.querySelectorAll("#share-rows td[data-expiry]")) {
    const countdown = status.querySelector(".share-countdown");
    const live = status.querySelector(".share-state").textContent === "分享中";
    countdown.hidden = !live;
    if (!live) continue;
    const expiry = Number(status.dataset.expiry);
    countdown.textContent = expiry ? remainingText(Math.max(0,
      Math.ceil((expiry * 1000 + clockOffsetMs - Date.now()) / 1000))) : "無時間限制";
  }
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function cell(label, child, id) {
  const node = element("td");
  node.dataset.label = label;
  if (id) node.id = id;
  if (typeof child === "string") node.textContent = child;
  else node.append(child);
  return node;
}

function makeRow(item) {
  const row = element("tr");
  row.id = `row-${item.id}`;
  const name = element("strong", item.display_name);
  const kind = element("span", item.kind === "icu" ? "ICU 設定" : "TAK 套件", "badge text-bg-secondary");
  const file = cell("檔案", name);
  file.append(element("br"), kind);
  const status = cell("狀態", element("span", "", "share-state badge text-bg-secondary"), `status-${item.id}`);
  status.append(element("small", "", "share-countdown"));
  const count = cell("已使用／上限", "", `count-${item.id}`);
  const dates = cell("建立／截止時間", item.created_at);
  dates.append(element("br"), element("span", `截止：${item.expires_at}`));
  const view = cell("查看", element("a", "檢視 QR", "btn btn-outline-info view"));
  const link = view.querySelector("a");
  link.dataset.active = "";
  link.dataset.qrOpen = "";
  link.dataset.shareId = item.id;
  link.dataset.qrName = item.display_name;
  link.dataset.qrImage = item.qr_image_url;
  link.dataset.qrAccepted = item.accepted;
  link.dataset.qrMax = item.max_downloads ?? "∞";
  link.href = item.qr_url;
  const ended = element("span", "已結束");
  ended.dataset.ended = "";
  view.append(ended);
  const action = cell("控制", element("form"));
  action.className = "action-danger";
  const form = action.querySelector("form");
  form.dataset.active = "";
  form.method = "post";
  form.action = "/stop";
  for (const [key, value] of [["csrf", csrf], ["id", item.id]]) {
    const input = element("input");
    input.type = "hidden";
    input.name = key;
    input.value = value;
    form.append(input);
  }
  form.append(element("button", "停止此分享", "btn btn-danger stop"));
  row.append(file, status, count, dates, view, action);
  return row;
}

function updateRow(row, item) {
  const stopped = item.inactive;
  row.classList.toggle("inactive", stopped);
  row.querySelector("td:first-child strong").textContent = item.display_name;
  const status = byId(`status-${item.id}`);
  const badge = status.querySelector(".share-state");
  badge.textContent = item.status;
  badge.classList.toggle("text-bg-success", item.status === "分享中");
  badge.classList.toggle("text-bg-secondary", item.status !== "分享中");
  status.dataset.expiry = item.expires_at_epoch ?? "";
  status.classList.toggle("status-live", item.status === "分享中");
  status.classList.toggle("status-muted", item.status !== "分享中");
  const view = row.querySelector("[data-qr-open]");
  view.href = item.qr_url;
  view.dataset.qrImage = item.qr_image_url;
  view.dataset.qrName = item.display_name;
  view.dataset.qrAccepted = item.accepted;
  view.dataset.qrMax = item.max_downloads ?? "∞";
  view.hidden = item.status !== "分享中";
  if (currentQrShareId === String(item.id) && item.status !== "分享中") {
    bootstrap.Modal.getInstance(byId("share-qr-dialog"))?.hide();
  }
  const count = byId(`count-${item.id}`);
  count.textContent = `${item.accepted} / ${item.max_downloads ?? "∞"}`;
  for (const node of row.querySelectorAll("[data-active]")) node.hidden = stopped;
  const ended = row.querySelector("[data-ended]");
  ended.textContent = item.status === "全部暫停" ? "已暫停" : "已結束";
  ended.hidden = item.status === "分享中";
}

function renderRecordPage() {
  const table = byId("share-rows");
  const pageSize = Number(byId("share-page-size").value);
  const filtered = shareStatusFilter === "all" ? recordItems : recordItems.filter((item) => shareStatusCategory(item) === shareStatusFilter);
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  recordPage = Math.min(recordPage, pages);
  const start = (recordPage - 1) * pageSize;
  const visible = filtered.slice(start, start + pageSize);
  const current = new Set(visible.map((item) => `row-${item.id}`));
  for (const row of [...table.children]) if (!current.has(row.id)) row.remove();
  visible.forEach((item, index) => {
    let row = byId(`row-${item.id}`);
    if (!row) row = makeRow(item);
    if (table.children[index] !== row) table.insertBefore(row, table.children[index] || null);
    updateRow(row, item);
  });
  table.closest("table").hidden = filtered.length === 0;
  const empty = byId("share-record-empty");
  empty.hidden = filtered.length > 0;
  empty.textContent = recordItems.length ? "沒有符合條件的分享紀錄。" : "目前沒有分享紀錄。";
  const shown = visible.length ? `顯示 ${start + 1}–${start + visible.length} / ${filtered.length} 筆` : "顯示 0 筆";
  const hidden = recordItems.length > filtered.length ? `；隱藏 ${recordItems.length - filtered.length} 筆` : "";
  byId("share-record-count").textContent = `${shown}（總計 ${recordItems.length} 筆${hidden}）`;
  byId("share-page-label").textContent = `第 ${recordPage} / ${pages} 頁`;
  byId("share-page-prev").disabled = recordPage === 1;
  byId("share-page-next").disabled = recordPage === pages;
  byId("share-page-prev-item").classList.toggle("disabled", recordPage === 1);
  byId("share-page-next-item").classList.toggle("disabled", recordPage === pages);
  updateCountdowns();
}

function updateShares(items) {
  recordItems = items;
  renderRecordPage();
  if (currentQrShareId && !items.some((item) =>
    String(item.id) === currentQrShareId && item.status === "分享中")) {
    bootstrap.Modal.getInstance(byId("share-qr-dialog"))?.hide();
  }
  if (currentQrShareId) updateQrCount(items.find((item) => String(item.id) === currentQrShareId));

  const live = items.filter((item) => item.status === "分享中");
  const list = byId("live-links");
  const activeIds = new Set(live.map((item) => `active-${item.id}`));
  for (const link of [...list.children]) if (!activeIds.has(link.id)) link.remove();
  live.forEach((item, index) => {
    let entry = byId(`active-${item.id}`);
    if (!entry) {
      entry = element("li");
      entry.id = `active-${item.id}`;
      const link = element("a", item.qr_url);
      link.href = item.qr_url;
      link.dataset.qrOpen = "";
      link.dataset.shareId = item.id;
      link.dataset.qrName = item.display_name;
      link.dataset.qrImage = item.qr_image_url;
      link.dataset.qrAccepted = item.accepted;
      link.dataset.qrMax = item.max_downloads ?? "∞";
      entry.append(element("strong", item.display_name), link);
    }
    const link = entry.querySelector("a");
    link.textContent = item.qr_url;
    link.href = item.qr_url;
    link.dataset.qrName = item.display_name;
    link.dataset.qrImage = item.qr_image_url;
    link.dataset.qrAccepted = item.accepted;
    link.dataset.qrMax = item.max_downloads ?? "∞";
    entry.querySelector("strong").textContent = item.display_name;
    if (list.children[index] !== entry) list.insertBefore(entry, list.children[index] || null);
  });
  byId("live-count").textContent = live.length;
  byId("live-empty").hidden = live.length > 0;
}

byId("share-page-size").addEventListener("change", () => {
  recordPage = 1;
  renderRecordPage();
});
for (const button of document.querySelectorAll("[data-share-status]")) button.addEventListener("click", () => {
  shareStatusFilter = button.dataset.shareStatus;
  for (const option of document.querySelectorAll("[data-share-status]")) {
    const selected = option === button;
    option.classList.toggle("active", selected);
    option.setAttribute("aria-pressed", String(selected));
  }
  recordPage = 1;
  renderRecordPage();
});
byId("share-page-prev").addEventListener("click", () => {
  recordPage -= 1;
  renderRecordPage();
});
byId("share-page-next").addEventListener("click", () => {
  recordPage += 1;
  renderRecordPage();
});

function updateSources(groups) {
  if (!byId("source-select")) return;
  const signature = JSON.stringify(groups);
  if (signature === lastSources) return;
  lastSources = signature;
  const select = byId("source-select");
  const previous = select.value;
  const generated = element("optgroup");
  generated.label = "即時產生";
  const initial = element("option", "使用目前發布密碼建立 ICU 設定");
  initial.value = "icu:new";
  generated.append(initial);
  const options = [generated];
  for (const [title, files] of groups) {
    const group = element("optgroup");
    group.label = title;
    for (const [value, label] of files) {
      const option = element("option", label);
      option.value = value;
      group.append(option);
    }
    options.push(group);
  }
  select.replaceChildren(...options);
  if ([...select.options].some((option) => option.value === previous)) select.value = previous;
}

function updateMaster(paused) {
  byId("master-panel").classList.toggle("paused", paused);
  byId("master-icon").textContent = paused ? "⏸" : "✓";
  byId("master-status").textContent = paused ? "所有分享下載已暫停" : "分享下載開放中";
  byId("master-detail").textContent = paused ? "公開下載已停止" : "公開連結可正常下載";
  byId("master-form").action = paused ? "/resume" : "/pause";
  const button = byId("master-button");
  button.textContent = paused ? "恢復所有分享下載" : "暫停所有分享下載";
  button.classList.toggle("stop", !paused);
  button.classList.toggle("btn-danger", !paused);
  button.classList.toggle("btn-primary", paused);
}

async function refresh() {
  if (requestPending || document.hidden) return;
  requestPending = true;
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), 5000);
  try {
    const response = await fetch("/stats", {cache: "no-store", signal: timeout.signal});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    clockOffsetMs = Date.now() - data.server_now * 1000;
    updateMaster(data.paused);
    updateShares(data.shares);
    updateCountdowns();
    updateSources(data.sources);
    byId("live-sync").textContent = `已同步 ${new Date().toLocaleTimeString("zh-TW", {hour12: false})}`;
    byId("live-sync").classList.remove("alert", "alert-warning");
  } catch (_) {
    byId("live-sync").textContent = "同步中斷，正在重試";
    byId("live-sync").classList.add("alert", "alert-warning");
  } finally {
    clearTimeout(timer);
    requestPending = false;
  }
}

function updateQrCount(item) {
  byId("share-qr-count").textContent = item
    ? `已下載 ${item.accepted}／${item.max_downloads ?? "∞"} 次` : "";
}

document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-qr-open]");
  if (!link || !window.bootstrap?.Modal) return;
  event.preventDefault();
  const selected = recordItems.find((item) => String(item.id) === link.dataset.shareId);
  const group = selected?.kind === "icu" && selected.media_owner ? recordItems.filter((item) =>
    item.kind === "icu" && item.media_owner === selected.media_owner && item.status === "分享中") :
    selected?.batch_id ? recordItems.filter((item) =>
      item.batch_id === selected.batch_id && item.status === "分享中") : [];
  const items = group.length ? group.sort((a, b) => a.display_name.localeCompare(b.display_name, undefined,
    {numeric: true})) : [{id: link.dataset.shareId, display_name: link.dataset.qrName,
      qr_image_url: link.dataset.qrImage, qr_url: link.href,
      accepted: Number(link.dataset.qrAccepted), max_downloads: link.dataset.qrMax}];
  const slides = items.map((item) => {
    const slide = element("div", undefined, "carousel-item");
    slide.dataset.shareId = item.id;
    if (String(item.id) === link.dataset.shareId) slide.classList.add("active");
    const content = element("div", undefined, "text-center");
    const name = element("h3", item.display_name, "fs-5 mb-0");
    const image = element("img", undefined, "qr img-fluid rounded mx-auto my-2");
    image.src = item.qr_image_url;
    image.alt = `${item.display_name} QR Code`;
    const url = element("a", item.qr_url);
    url.href = item.qr_url;
    url.target = "_blank";
    url.rel = "noreferrer noopener";
    content.append(name, image, url);
    slide.append(content);
    return slide;
  });
  const carousel = byId("share-qr-carousel");
  bootstrap.Carousel.getInstance(carousel)?.dispose();
  byId("share-qr-slides").replaceChildren(...slides);
  byId("share-qr-controls").hidden = items.length < 2;
  byId("share-qr-position").textContent = `${items.findIndex((item) => String(item.id) === link.dataset.shareId) + 1}／${items.length}`;
  currentQrShareId = link.dataset.shareId;
  updateQrCount(items.find((item) => String(item.id) === currentQrShareId));
  bootstrap.Carousel.getOrCreateInstance(carousel, {interval: false, touch: true});
  bootstrap.Modal.getOrCreateInstance(byId("share-qr-dialog")).show();
});
byId("share-qr-carousel").addEventListener("slid.bs.carousel", () => {
  const slides = [...byId("share-qr-slides").children];
  const index = slides.findIndex((item) => item.classList.contains("active"));
  currentQrShareId = slides[index]?.dataset.shareId ?? null;
  updateQrCount(recordItems.find((item) => String(item.id) === currentQrShareId));
  byId("share-qr-position").textContent = `${index + 1}／${slides.length}`;
});
byId("share-qr-dialog").addEventListener("hidden.bs.modal", () => {
  currentQrShareId = null;
  byId("share-qr-count").textContent = "";
  byId("share-qr-slides").replaceChildren();
});
updateCountdowns();
setInterval(updateCountdowns, 1000);
refresh();
setInterval(refresh, 2000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
window.addEventListener("focus", refresh);

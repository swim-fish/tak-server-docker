"use strict";

const byId = (id) => document.getElementById(id);
const terminalStatuses = new Set(["已手動停止", "時間到期", "次數額滿"]);
const csrf = document.querySelector("#master-form input[name=csrf]").value;
let requestPending = false;
let lastSources = "";
let clockOffsetMs = Date.now() - Number(byId("share-rows").dataset.serverNow) * 1000;
let currentQrShareId = null;

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
  const name = element("span", item.filename);
  const kind = element("small", item.kind);
  const file = cell("檔案", name);
  file.append(element("br"), kind);
  const status = cell("狀態", element("span", "", "share-state"), `status-${item.id}`);
  status.append(element("small", "", "share-countdown"));
  const count = cell("已使用／上限", "", `count-${item.id}`);
  const dates = cell("建立／截止時間", item.created_at);
  dates.append(element("br"), element("span", `截止：${item.expires_at}`));
  const view = cell("查看", element("a", "檢視 QR", "btn btn-outline-info view"));
  const link = view.querySelector("a");
  link.dataset.active = "";
  link.dataset.qrOpen = "";
  link.dataset.shareId = item.id;
  link.dataset.qrName = item.filename;
  link.dataset.qrImage = item.qr_image_url;
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
  const stopped = terminalStatuses.has(item.status);
  row.classList.toggle("inactive", stopped);
  const status = byId(`status-${item.id}`);
  status.querySelector(".share-state").textContent = item.status;
  status.dataset.expiry = item.expires_at_epoch ?? "";
  status.classList.toggle("status-live", item.status === "分享中");
  status.classList.toggle("status-muted", item.status !== "分享中");
  const view = row.querySelector("[data-qr-open]");
  view.href = item.qr_url;
  view.dataset.qrImage = item.qr_image_url;
  view.dataset.qrName = item.filename;
  view.hidden = item.status !== "分享中";
  if (currentQrShareId === String(item.id) && item.status !== "分享中") {
    bootstrap.Modal.getInstance(byId("share-qr-dialog"))?.hide();
  }
  const count = byId(`count-${item.id}`);
  count.replaceChildren(document.createTextNode(`${item.accepted} / ${item.max_downloads ?? "∞"}`),
    element("br"), element("small", `完成 ${item.completed}`));
  for (const node of row.querySelectorAll("[data-active]")) node.hidden = stopped;
  const ended = row.querySelector("[data-ended]");
  ended.textContent = item.status === "全部暫停" ? "已暫停" : "已結束";
  ended.hidden = item.status === "分享中";
}

function updateShares(items) {
  const table = byId("share-rows");
  const current = new Set(items.map((item) => `row-${item.id}`));
  for (const row of [...table.children]) if (!current.has(row.id)) row.remove();
  items.forEach((item, index) => {
    let row = byId(`row-${item.id}`);
    if (!row) row = makeRow(item);
    if (table.children[index] !== row) table.insertBefore(row, table.children[index] || null);
    updateRow(row, item);
  });

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
      link.dataset.qrName = item.filename;
      link.dataset.qrImage = item.qr_image_url;
      entry.append(element("strong", item.filename), link);
    }
    const link = entry.querySelector("a");
    link.textContent = item.qr_url;
    link.href = item.qr_url;
    link.dataset.qrName = item.filename;
    link.dataset.qrImage = item.qr_image_url;
    if (list.children[index] !== entry) list.insertBefore(entry, list.children[index] || null);
  });
  byId("live-count").textContent = live.length;
  byId("live-empty").hidden = live.length > 0;
}

function updateSources(groups) {
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
  } catch (_) {
    byId("live-sync").textContent = "同步中斷，正在重試";
  } finally {
    clearTimeout(timer);
    requestPending = false;
  }
}

document.addEventListener("click", (event) => {
  const link = event.target.closest("[data-qr-open]");
  if (!link || !window.bootstrap?.Modal) return;
  event.preventDefault();
  currentQrShareId = link.dataset.shareId;
  byId("share-qr-name").textContent = link.dataset.qrName;
  byId("share-qr-image").src = link.dataset.qrImage;
  const url = byId("share-qr-url");
  url.textContent = link.href;
  url.href = link.href;
  bootstrap.Modal.getOrCreateInstance(byId("share-qr-dialog")).show();
});
byId("share-qr-dialog").addEventListener("hidden.bs.modal", () => {
  currentQrShareId = null;
  byId("share-qr-image").removeAttribute("src");
});
updateCountdowns();
setInterval(updateCountdowns, 1000);
refresh();
setInterval(refresh, 2000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
window.addEventListener("focus", refresh);

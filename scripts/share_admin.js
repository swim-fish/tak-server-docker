"use strict";

const byId = (id) => document.getElementById(id);
const terminalStatuses = new Set(["已手動停止", "時間到期", "次數額滿"]);
const csrf = document.querySelector("#master-form input[name=csrf]").value;
let requestPending = false;
let lastSources = "";

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
  const status = cell("狀態", "", `status-${item.id}`);
  const count = cell("已使用／上限", "", `count-${item.id}`);
  const dates = cell("建立／截止時間", item.created_at);
  dates.append(element("br"), element("span", `截止：${item.expires_at}`));
  const view = cell("查看", element("a", "檢視 QR", "button view"));
  const link = view.querySelector("a");
  link.dataset.active = "";
  link.href = item.qr_url;
  link.target = "_blank";
  link.rel = "noreferrer noopener";
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
  form.append(element("button", "停止此分享", "stop"));
  row.append(file, status, count, dates, view, action);
  return row;
}

function updateRow(row, item) {
  const stopped = terminalStatuses.has(item.status);
  row.classList.toggle("inactive", stopped);
  const status = byId(`status-${item.id}`);
  status.textContent = item.status;
  status.classList.toggle("status-live", item.status === "分享中");
  status.classList.toggle("status-muted", item.status !== "分享中");
  const count = byId(`count-${item.id}`);
  count.replaceChildren(document.createTextNode(`${item.accepted} / ${item.max_downloads ?? "∞"}`),
    element("br"), element("small", `完成 ${item.completed}`));
  for (const node of row.querySelectorAll("[data-active]")) node.hidden = stopped;
  row.querySelector("[data-ended]").hidden = !stopped;
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
      link.target = "_blank";
      link.rel = "noreferrer noopener";
      entry.append(element("strong", item.filename), link);
    }
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
  button.classList.toggle("button", paused);
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
    updateMaster(data.paused);
    updateShares(data.shares);
    updateSources(data.sources);
    byId("live-sync").textContent = `已同步 ${new Date().toLocaleTimeString("zh-TW", {hour12: false})}`;
  } catch (_) {
    byId("live-sync").textContent = "同步中斷，正在重試";
  } finally {
    clearTimeout(timer);
    requestPending = false;
  }
}

refresh();
setInterval(refresh, 2000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
window.addEventListener("focus", refresh);

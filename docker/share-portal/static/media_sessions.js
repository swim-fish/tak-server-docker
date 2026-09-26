"use strict";
const sessionList = document.getElementById("session-list");
const sessionSearch = document.getElementById("session-search");
const sessionUpdated = document.getElementById("session-updated");
const sessionError = document.getElementById("session-error");
let sessions = [];
let total = 0;

function addField(list, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = value || "—";
  list.append(term, detail);
}

function formatTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? (value || "—") : date.toLocaleString("zh-TW");
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const unit = bytes < 1024 ** 2 ? "KB" : bytes < 1024 ** 3 ? "MB" : "GB";
  const divisor = unit === "KB" ? 1024 : unit === "MB" ? 1024 ** 2 : 1024 ** 3;
  return `${(bytes / divisor).toFixed(1)} ${unit}`;
}

function renderSessions() {
  const term = sessionSearch.value.trim().toLocaleLowerCase();
  const visible = sessions.filter((item) => [item.path, item.remote_addr, item.id]
    .some((value) => String(value || "").toLocaleLowerCase().includes(term)));
  const cards = visible.map((item) => {
    const card = document.createElement("article");
    card.className = "media-session-card";
    const heading = document.createElement("div");
    heading.className = "d-flex flex-wrap align-items-center justify-content-between gap-2";
    const path = document.createElement("strong");
    path.textContent = item.path || "路徑不明";
    const badge = document.createElement("span");
    badge.className = `badge status-badge ${item.connected ? "text-bg-success" : "text-bg-warning"}`;
    badge.textContent = item.connected ? "已連線" : "連線中";
    heading.append(path, badge);
    const details = document.createElement("dl");
    details.className = "media-session-details";
    addField(details, "來源位址", item.remote_addr);
    addField(details, "開始時間", formatTime(item.created));
    addField(details, "已傳送", formatBytes(item.outbound_bytes));
    addField(details, "Session ID", item.id);
    if (item.user_agent) addField(details, "瀏覽器", item.user_agent);
    card.append(heading, details);
    return card;
  });
  sessionList.replaceChildren(...cards);
  const empty = document.getElementById("session-empty");
  empty.hidden = visible.length !== 0;
  empty.textContent = sessions.length ? "沒有符合搜尋的工作階段。" : "目前沒有公開觀看工作階段。";
  document.getElementById("session-limited").hidden = total <= sessions.length;
}

async function refreshSessions() {
  if (document.hidden) return;
  const loading = document.getElementById("session-loading");
  loading.hidden = false;
  try {
    const response = await fetch("/media/sessions/status", {cache: "no-store"});
    if (!response.ok) throw new Error("session status unavailable");
    const data = await response.json();
    sessions = data.items;
    total = data.total;
    const state = document.getElementById("session-viewer-state");
    state.textContent = !data.viewer.running ? "觀看服務未啟動" :
      (data.viewer.desired ? "公開觀看已開啟" : "公開觀看已關閉");
    state.className = `badge status-badge ${!data.viewer.running ? "text-bg-warning" :
      (data.viewer.desired ? "text-bg-success" : "text-bg-secondary")}`;
    document.getElementById("session-total").textContent = `${total} 個工作階段`;
    sessionUpdated.textContent = `更新於 ${new Date().toLocaleTimeString("zh-TW")}`;
    sessionError.hidden = true;
    renderSessions();
  } catch (_error) {
    sessionError.textContent = sessions.length ? "更新失敗；以下是上次取得的工作階段資料。" :
      "無法取得公開觀看工作階段，請稍後重試。";
    sessionError.hidden = false;
    sessionUpdated.textContent = "更新失敗";
  } finally {
    loading.hidden = true;
  }
}

sessionSearch.addEventListener("input", renderSessions);
document.getElementById("session-refresh").addEventListener("click", refreshSessions);
document.addEventListener("visibilitychange", refreshSessions);
refreshSessions();
setInterval(refreshSessions, 5000);

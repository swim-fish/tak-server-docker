(() => {
  'use strict';

  let available = JSON.parse(document.getElementById('wallConfig').textContent);
  let byPath = new Map(available.map(item => [item.path, item]));
  const capacities = new Map([[1, 1], [2, 2], [4, 2], [6, 3], [8, 4], [12, 4], [16, 4]]);
  const wall = document.getElementById('wall');
  const layoutSelect = document.getElementById('layout');
  const picker = document.getElementById('streamPicker');
  const addButton = document.getElementById('addStream');
  const message = document.getElementById('message');
  const storageKey = 'tak-local-media-wall:admin';
  let layout = 4;
  let slots = [];
  let active = new Set();
  let initialized = false;

  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
    if (capacities.has(saved.layout)) layout = saved.layout;
    if (Array.isArray(saved.slots)) {
      const seen = new Set();
      slots = saved.slots.filter(item => item && byPath.has(item.path) && !seen.has(item.path)
        && seen.add(item.path)).slice(0, layout).map(item => ({path: item.path, paused: item.paused === true}));
      initialized = true;
    }
  } catch (_) { /* Invalid local state is ignored. */ }
  layoutSelect.value = String(layout);

  function save() {
    try { sessionStorage.setItem(storageKey, JSON.stringify({layout, slots})); } catch (_) { /* Optional state. */ }
  }

  function say(value) { message.textContent = value; }

  function updateCatalog(items) {
    available = items;
    byPath = new Map(items.map(item => [item.path, item]));
    slots = slots.filter(item => byPath.has(item.path)).slice(0, layout);
  }

  function refreshPicker() {
    const chosen = picker.value;
    picker.replaceChildren();
    for (const item of available) {
      const option = document.createElement('option');
      option.value = item.path;
      option.textContent = `${item.label} ${active.has(item.path) ? '● 直播中' : '○ 待發布'}`;
      option.disabled = slots.some(slot => slot.path === item.path);
      picker.append(option);
    }
    if (chosen && [...picker.options].some(option => option.value === chosen && !option.disabled)) {
      picker.value = chosen;
    } else {
      const first = [...picker.options].find(option => !option.disabled);
      if (first) picker.value = first.value;
    }
    addButton.disabled = slots.length >= layout || ![...picker.options].some(option => !option.disabled);
  }

  function button(label, action, title) {
    const element = document.createElement('button');
    element.type = 'button';
    element.textContent = label;
    element.title = title;
    element.dataset.action = action;
    return element;
  }

  function makeTile(index) {
    const tile = document.createElement('article');
    tile.className = 'media-wall-tile';
    tile.dataset.index = String(index);
    const head = document.createElement('div');
    head.className = 'media-wall-tile-head';
    const drag = button('☰', 'drag', '拖曳排序');
    drag.className = 'btn btn-outline-secondary drag';
    drag.draggable = true;
    const title = document.createElement('h2');
    title.className = 'media-wall-tile-title';
    const previous = button('←', 'previous', '向前移動');
    const next = button('→', 'next', '向後移動');
    const pause = button('暫停', 'pause', '暫停或繼續');
    const close = button('×', 'close', '關閉這格');
    for (const control of [previous, next, pause, close]) control.className = 'btn btn-outline-secondary';
    head.append(drag, title, previous, next, pause, close);
    const screen = document.createElement('div');
    screen.className = 'media-wall-screen';
    const placeholder = document.createElement('div');
    placeholder.className = 'media-wall-placeholder';
    screen.append(placeholder);
    const foot = document.createElement('div');
    foot.className = 'media-wall-tile-foot';
    const status = document.createElement('span');
    const link = document.createElement('a');
    link.textContent = '單畫面';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    foot.append(status, link);
    tile.append(head, screen, foot);
    return tile;
  }

  function syncTile(tile, index) {
    const slot = slots[index];
    const title = tile.querySelector('.media-wall-tile-title');
    const screen = tile.querySelector('.media-wall-screen');
    const placeholder = tile.querySelector('.media-wall-placeholder');
    const status = tile.querySelector('.media-wall-tile-foot span');
    const link = tile.querySelector('.media-wall-tile-foot a');
    const pause = tile.querySelector('[data-action="pause"]');
    const controls = tile.querySelectorAll('[data-action="drag"], [data-action="previous"], [data-action="next"], [data-action="close"]');
    title.textContent = slot ? byPath.get(slot.path).label : `畫面 ${index + 1}`;
    title.title = title.textContent;
    for (const control of controls) control.disabled = !slot;
    tile.querySelector('[data-action="previous"]').disabled = !slot || index === 0;
    tile.querySelector('[data-action="next"]').disabled = !slot || index >= slots.length - 1;
    pause.disabled = !slot;
    pause.textContent = slot && slot.paused ? '繼續' : '暫停';
    const playing = slot && active.has(slot.path) && !slot.paused;
    const current = screen.querySelector('iframe');
    if (current && (!playing || current.dataset.path !== slot.path)) current.remove();
    if (playing && !screen.querySelector('iframe')) {
      const frame = document.createElement('iframe');
      frame.dataset.path = slot.path;
      frame.src = byPath.get(slot.path).url;
      frame.title = `${byPath.get(slot.path).label} 即時影像`;
      frame.allow = 'autoplay; fullscreen';
      frame.referrerPolicy = 'no-referrer';
      screen.prepend(frame);
    }
    placeholder.hidden = Boolean(playing);
    placeholder.textContent = !slot ? '選擇串流加入畫面' : slot.paused ? '已暫停' : active.has(slot.path) ? '' : '等待串流上線';
    status.textContent = !slot ? '空白' : slot.paused ? '已暫停' : active.has(slot.path) ? '直播中' : '未上線';
    status.className = playing ? 'media-wall-state-live' : slot && !slot.paused ? 'media-wall-state-wait' : '';
    link.hidden = !slot;
    if (slot) link.href = byPath.get(slot.path).url;
  }

  function syncWall() {
    const columns = capacities.get(layout);
    wall.dataset.layout = String(layout);
    document.body.classList.toggle('media-wall-dense', layout >= 12);
    wall.style.setProperty('--columns', String(columns));
    wall.style.setProperty('--rows', String(Math.ceil(layout / columns)));
    while (wall.children.length < layout) wall.append(makeTile(wall.children.length));
    while (wall.children.length > layout) wall.lastElementChild.remove();
    [...wall.children].forEach((tile, index) => syncTile(tile, index));
    document.getElementById('wallCount').textContent = `${active.size} 路上線`;
    refreshPicker();
    save();
  }

  function move(from, to) {
    if (from < 0 || to < 0 || from >= slots.length || to >= slots.length || from === to) return;
    const [item] = slots.splice(from, 1);
    slots.splice(to, 0, item);
    syncWall();
  }

  layoutSelect.addEventListener('change', () => {
    layout = Number(layoutSelect.value);
    slots = slots.slice(0, layout);
    syncWall();
  });
  addButton.addEventListener('click', () => {
    const path = picker.value;
    if (!byPath.has(path) || slots.some(slot => slot.path === path) || slots.length >= layout) return;
    slots.push({path, paused: false});
    syncWall();
  });
  document.getElementById('clearWall').addEventListener('click', () => {
    slots = [];
    initialized = true;
    syncWall();
  });
  document.getElementById('fullScreen').addEventListener('click', async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.body.requestFullscreen();
  });
  document.addEventListener('fullscreenchange', () => {
    document.getElementById('fullScreen').textContent = document.fullscreenElement ? '離開全螢幕' : '全螢幕';
  });
  wall.addEventListener('click', event => {
    const control = event.target.closest('button[data-action]');
    if (!control || control.disabled) return;
    const index = Number(control.closest('.media-wall-tile').dataset.index);
    if (control.dataset.action === 'pause') slots[index].paused = !slots[index].paused;
    else if (control.dataset.action === 'close') slots.splice(index, 1);
    else if (control.dataset.action === 'previous') return move(index, index - 1);
    else if (control.dataset.action === 'next') return move(index, index + 1);
    else return;
    syncWall();
  });
  wall.addEventListener('dragstart', event => {
    if (!event.target.matches('.drag') || event.target.disabled) return event.preventDefault();
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', event.target.closest('.media-wall-tile').dataset.index);
  });
  wall.addEventListener('dragover', event => {
    const tile = event.target.closest('.media-wall-tile');
    if (!tile || Number(tile.dataset.index) >= slots.length) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    tile.classList.add('drag-over');
  });
  wall.addEventListener('dragleave', event => {
    const tile = event.target.closest('.media-wall-tile');
    if (tile && !tile.contains(event.relatedTarget)) tile.classList.remove('drag-over');
  });
  wall.addEventListener('drop', event => {
    const tile = event.target.closest('.media-wall-tile');
    if (!tile) return;
    event.preventDefault();
    wall.querySelectorAll('.drag-over').forEach(item => item.classList.remove('drag-over'));
    move(Number(event.dataTransfer.getData('text/plain')), Number(tile.dataset.index));
  });
  wall.addEventListener('dragend', () => wall.querySelectorAll('.drag-over').forEach(item => item.classList.remove('drag-over')));

  async function poll() {
    try {
      const response = await fetch('/media/wall/status', {credentials: 'same-origin', cache: 'no-store'});
      if (response.status === 401) {
        active = new Set();
        syncWall();
        say('管理員預覽授權已到期，請重新整理管理頁。');
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      updateCatalog(data.available);
      active = new Set(data.active.filter(path => byPath.has(path)));
      if (!initialized) {
        slots = [...active].slice(0, layout).map(path => ({path, paused: false}));
        initialized = true;
      }
      syncWall();
      say(`${active.size} 路串流上線，已選取 ${slots.length} 路。`);
    } catch (_) {
      say('串流狀態暫時無法更新，現有畫面仍可觀看。');
    }
  }

  syncWall();
  poll();
  setInterval(poll, 10000);
})();

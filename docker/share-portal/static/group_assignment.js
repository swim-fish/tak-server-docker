(() => {
  'use strict';

  const groupName = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/;
  for (const board of document.querySelectorAll('[data-group-board]')) {
    const form = board.closest('form');
    const readOnly = board.dataset.readonly === 'true';
    const lists = Object.fromEntries([...board.querySelectorAll('[data-group-list]')]
      .map(list => [list.dataset.groupList, list]));
    const selected = new Set();
    const destination = board.querySelector('[data-group-destination]');
    const moveButton = board.querySelector('[data-group-move]');
    const newInput = board.querySelector('[data-group-new]');
    const message = board.querySelector('[data-group-message]');
    const fields = board.querySelector('[data-group-fields]');
    let dragged = null;

    function allEntries() {
      return [...board.querySelectorAll('.group-entry')];
    }

    function findEntry(name) {
      return allEntries().find(entry => entry.dataset.group === name);
    }

    function addField(name, group) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = name;
      input.setAttribute('value', group);
      fields.append(input);
    }

    function sync() {
      fields.replaceChildren();
      for (const [lane, list] of Object.entries(lists)) {
        for (const entry of list.querySelectorAll('.group-entry')) {
          if (lane === 'in' || lane === 'both') addField('in_group', entry.dataset.group);
          if (lane === 'out' || lane === 'both') addField('out_group', entry.dataset.group);
        }
        board.querySelector(`[data-count="${lane}"]`).textContent = `（${list.children.length}）`;
      }
      moveButton.disabled = readOnly || selected.size === 0;
    }

    function clearSelection() {
      selected.clear();
      for (const entry of allEntries()) {
        entry.classList.remove('is-selected');
        entry.querySelector('.group-pick').setAttribute('aria-pressed', 'false');
      }
    }

    function move(name, lane) {
      const entry = findEntry(name);
      if (!entry || !lists[lane]) return false;
      lists[lane].append(entry);
      return true;
    }

    board.addEventListener('click', event => {
      const button = event.target.closest('.group-pick');
      if (!button || readOnly || !board.contains(button)) return;
      const entry = button.closest('.group-entry');
      const name = entry.dataset.group;
      if (selected.has(name)) selected.delete(name);
      else selected.add(name);
      entry.classList.toggle('is-selected', selected.has(name));
      button.setAttribute('aria-pressed', String(selected.has(name)));
      sync();
    });

    moveButton.addEventListener('click', () => {
      if (readOnly || !selected.size) return;
      const count = [...selected].filter(name => move(name, destination.value)).length;
      clearSelection();
      sync();
      message.textContent = `已移動 ${count} 個群組。`;
    });

    function addGroup() {
      if (readOnly) return;
      const name = newInput.value.trim();
      if (!groupName.test(name)) {
        message.textContent = '群組名稱須以英文字母或數字開頭，長度 1–64，僅能包含英文、數字、點、底線、冒號與連字號。';
        return;
      }
      if (findEntry(name)) {
        message.textContent = '此群組已在清單中。';
        return;
      }
      const entry = document.createElement('li');
      entry.className = 'group-entry';
      entry.dataset.group = name;
      entry.draggable = true;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'group-pick';
      button.setAttribute('aria-pressed', 'false');
      button.textContent = name;
      const grip = document.createElement('span');
      grip.className = 'group-grip';
      grip.setAttribute('aria-hidden', 'true');
      grip.textContent = '⋮⋮';
      entry.append(button, grip);
      lists.none.append(entry);
      newInput.value = '';
      sync();
      message.textContent = `已將 ${name} 加入未指派清單。`;
    }

    board.querySelector('[data-group-add]').addEventListener('click', addGroup);
    newInput.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        addGroup();
      }
    });

    board.addEventListener('dragstart', event => {
      const entry = event.target.closest('.group-entry');
      if (readOnly || !entry || !board.contains(entry)) {
        event.preventDefault();
        return;
      }
      dragged = entry.dataset.group;
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', dragged);
    });
    board.addEventListener('dragover', event => {
      const lane = event.target.closest('.group-lane');
      for (const item of board.querySelectorAll('.group-lane')) item.classList.remove('drag-over');
      if (!lane || readOnly) return;
      event.preventDefault();
      lane.classList.add('drag-over');
      event.dataTransfer.dropEffect = 'move';
    });
    board.addEventListener('drop', event => {
      const lane = event.target.closest('.group-lane');
      for (const item of board.querySelectorAll('.group-lane')) item.classList.remove('drag-over');
      if (!lane || readOnly) return;
      event.preventDefault();
      const name = dragged || event.dataTransfer.getData('text/plain');
      if (move(name, lane.dataset.lane)) {
        clearSelection();
        sync();
        message.textContent = `已將 ${name} 移至 ${lane.querySelector('h3').firstChild.textContent.trim()}。`;
      }
      dragged = null;
    });
    board.addEventListener('dragend', () => {
      dragged = null;
      for (const item of board.querySelectorAll('.group-lane')) item.classList.remove('drag-over');
    });

    form.addEventListener('submit', event => {
      sync();
      if (!fields.querySelector('[name="in_group"], [name="out_group"]')) {
        event.preventDefault();
        message.textContent = '至少要有一個 In 或 Out 群組。';
        message.scrollIntoView({block: 'nearest'});
      }
    });
    sync();
  }
})();

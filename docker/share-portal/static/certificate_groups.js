(() => {
  "use strict";
  const source = document.getElementById("group-records");
  if (!source) return;

  const records = JSON.parse(source.textContent);
  const cards = [...document.querySelectorAll("[data-group-card]")];
  const groupNames = new Set(cards.map((card) => card.dataset.groupCard));
  const bySerial = new Map(records.map((record) => [record.serial, record]));
  const original = new Map(records.map((record) => [record.serial, {
    in: new Set(record.in_groups || []), out: new Set(record.out_groups || []),
  }]));
  let working = cloneGroups(original);
  let statusFilter = "active";
  let addGroup = null;
  let moveSelection = null;
  const selectedAdd = new Set();
  const message = document.getElementById("group-message");
  const addDialog = document.getElementById("group-add-dialog");
  const moveDialog = document.getElementById("group-move-dialog");

  function cloneGroups(sourceGroups) {
    return new Map([...sourceGroups].map(([serial, groups]) => [serial, {
      in: new Set(groups.in), out: new Set(groups.out),
    }]));
  }

  function status(record) {
    if (record.revoked) return "revoked";
    if (record.expired) return "expired";
    return "active";
  }

  function statusLabel(record) {
    if (record.revoked) return ["已撤銷", "text-bg-secondary"];
    if (record.expired) return ["已逾期", "text-bg-warning"];
    if (record.registered !== true) return ["未註冊", "text-bg-secondary"];
    return ["使用中", "text-bg-success"];
  }

  function editable(record) {
    return !record.revoked && !record.expired && record.registered === true && !!record.fingerprint;
  }

  function laneFor(serial, group) {
    const groups = working.get(serial);
    const inGroup = groups.in.has(group);
    const outGroup = groups.out.has(group);
    return inGroup && outGroup ? "both" : inGroup ? "in" : outGroup ? "out" : null;
  }

  function matchesFilter(record) {
    return statusFilter === "all" || status(record) === statusFilter;
  }

  function badge(record) {
    const [label, style] = statusLabel(record);
    const node = document.createElement("span");
    node.className = `badge ${style}`;
    node.textContent = label;
    return node;
  }

  function entry(record, group, lane) {
    const node = document.createElement("li");
    node.dataset.serial = record.serial;
    node.dataset.group = group;
    node.dataset.lane = lane;
    node.draggable = editable(record) && !!group;
    if (!editable(record)) node.classList.add("group-member-locked");
    const link = document.createElement("a");
    link.href = `/certificates/${encodeURIComponent(record.serial)}`;
    link.textContent = record.name;
    const detail = document.createElement("small");
    detail.textContent = `CN ${record.cn} · CRL ID ${record.serial}`;
    node.append(link, badge(record), detail);
    if (editable(record) && group) {
      const move = document.createElement("button");
      move.type = "button";
      move.className = "btn btn-sm btn-outline-info";
      move.dataset.memberMove = "";
      move.textContent = "移動";
      node.append(move);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "btn btn-sm btn-outline-danger";
      remove.dataset.memberRemove = "";
      remove.textContent = "從此群組移除";
      node.append(remove);
    }
    return node;
  }

  function changes() {
    const result = [];
    for (const record of records) {
      const before = original.get(record.serial);
      const after = working.get(record.serial);
      const sorted = (values) => [...values].sort();
      const expectedIn = sorted(before.in);
      const expectedOut = sorted(before.out);
      const inGroups = sorted(after.in);
      const outGroups = sorted(after.out);
      if (JSON.stringify([expectedIn, expectedOut]) === JSON.stringify([inGroups, outGroups])) continue;
      result.push({serial: record.serial, fingerprint: record.fingerprint,
        expected_in: expectedIn, expected_out: expectedOut,
        in_groups: inGroups, out_groups: outGroups});
    }
    return result;
  }

  function render() {
    for (const card of cards) {
      const group = card.dataset.groupCard;
      let total = 0;
      let shown = 0;
      for (const lane of card.querySelectorAll(".certificate-group-lane")) {
        const list = lane.querySelector("[data-members]");
        list.replaceChildren();
        let laneTotal = 0;
        for (const record of records) {
          if (laneFor(record.serial, group) !== lane.dataset.lane) continue;
          laneTotal++;
          if (matchesFilter(record)) list.append(entry(record, group, lane.dataset.lane));
        }
        total += laneTotal;
        shown += list.children.length;
        lane.querySelector("[data-lane-count]").textContent = statusFilter === "all"
          ? String(laneTotal) : `${list.children.length} / ${laneTotal}`;
        lane.querySelector("[data-empty]").hidden = list.children.length > 0;
      }
      card.querySelector("[data-group-total]").textContent = statusFilter === "all"
        ? `${total} 張` : `${shown} / ${total} 張`;
    }
    const unassigned = document.getElementById("group-unassigned-list");
    unassigned.replaceChildren();
    for (const record of records) {
      const groups = working.get(record.serial);
      if (!groups.in.size && !groups.out.size && matchesFilter(record)) {
        unassigned.append(entry(record, "", "none"));
      }
    }
    document.getElementById("group-unassigned-empty").hidden = unassigned.children.length > 0;
    const visible = records.filter(matchesFilter).length;
    document.getElementById("group-visible-count").textContent = `顯示 ${visible} / ${records.length}`;
    const pending = changes().length;
    document.getElementById("group-pending-count").textContent = `待儲存 ${pending}`;
    document.getElementById("group-save").disabled = pending === 0;
    document.getElementById("group-discard").disabled = pending === 0;
  }

  function warn(text) {
    message.textContent = text;
    message.hidden = false;
  }

  function moveMembership(serial, sourceGroup, targetGroup, targetLane) {
    const record = bySerial.get(serial);
    if (!record || !editable(record) || !groupNames.has(targetGroup) ||
        !["in", "out", "both"].includes(targetLane) || !laneFor(serial, sourceGroup)) return false;
    const groups = working.get(serial);
    groups.in.delete(sourceGroup);
    groups.out.delete(sourceGroup);
    groups.in.delete(targetGroup);
    groups.out.delete(targetGroup);
    if (targetLane === "in" || targetLane === "both") groups.in.add(targetGroup);
    if (targetLane === "out" || targetLane === "both") groups.out.add(targetGroup);
    message.hidden = true;
    render();
    return true;
  }

  function removeMembership(serial, sourceGroup) {
    const record = bySerial.get(serial);
    if (!record || !editable(record) || !laneFor(serial, sourceGroup)) return false;
    const groups = working.get(serial);
    groups.in.delete(sourceGroup);
    groups.out.delete(sourceGroup);
    message.hidden = true;
    render();
    return true;
  }

  document.querySelectorAll("[data-group-status]").forEach((button) => button.addEventListener("click", () => {
    statusFilter = button.dataset.groupStatus;
    document.querySelectorAll("[data-group-status]").forEach((option) => {
      const selected = option === button;
      option.classList.toggle("active", selected);
      option.setAttribute("aria-pressed", String(selected));
    });
    render();
  }));

  document.getElementById("group-discard").addEventListener("click", () => {
    working = cloneGroups(original);
    message.hidden = true;
    render();
  });

  document.addEventListener("dragstart", (event) => {
    const member = event.target.closest(".certificate-group-lane li[data-serial]");
    if (!member || !member.draggable) return;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", JSON.stringify({
      serial: member.dataset.serial, group: member.dataset.group,
    }));
  });
  for (const lane of document.querySelectorAll(".certificate-group-lane")) {
    lane.addEventListener("dragover", (event) => {
      if (!event.dataTransfer.types.includes("text/plain")) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      lane.classList.add("drag-over");
    });
    lane.addEventListener("dragleave", () => lane.classList.remove("drag-over"));
    lane.addEventListener("drop", (event) => {
      event.preventDefault();
      lane.classList.remove("drag-over");
      try {
        const item = JSON.parse(event.dataTransfer.getData("text/plain"));
        const targetGroup = lane.closest("[data-group-card]").dataset.groupCard;
        if (!moveMembership(item.serial, item.group, targetGroup, lane.dataset.lane)) {
          warn("無法移動這張憑證；請重新整理並核對權限。 ");
        }
      } catch (error) {
        console.error("Group drag failed", error);
        warn("無法讀取拖曳的憑證。");
      }
    });
  }
  const unassignedCard = document.getElementById("group-unassigned");
  unassignedCard.addEventListener("dragover", (event) => {
    if (!event.dataTransfer.types.includes("text/plain")) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    unassignedCard.classList.add("drag-over");
  });
  unassignedCard.addEventListener("dragleave", () => unassignedCard.classList.remove("drag-over"));
  unassignedCard.addEventListener("drop", (event) => {
    event.preventDefault();
    unassignedCard.classList.remove("drag-over");
    try {
      const item = JSON.parse(event.dataTransfer.getData("text/plain"));
      if (!removeMembership(item.serial, item.group)) warn("無法移除這張憑證的群組。 ");
    } catch (error) {
      console.error("Group removal drag failed", error);
      warn("無法讀取拖曳的憑證。");
    }
  });

  document.addEventListener("click", (event) => {
    const add = event.target.closest("[data-group-add]");
    if (add) {
      addGroup = add.closest("[data-group-card]").dataset.groupCard;
      selectedAdd.clear();
      document.getElementById("group-add-title").textContent = `新增憑證到 ${addGroup}`;
      document.getElementById("group-add-search").value = "";
      document.getElementById("group-add-lane").value = "both";
      renderCandidates();
      bootstrap.Modal.getOrCreateInstance(addDialog).show();
      return;
    }
    const move = event.target.closest("[data-member-move]");
    if (move) {
      const member = move.closest("[data-serial]");
      moveSelection = {serial: member.dataset.serial, group: member.dataset.group};
      document.getElementById("group-move-name").textContent = bySerial.get(moveSelection.serial).name;
      document.getElementById("group-move-target").value = moveSelection.group;
      document.getElementById("group-move-lane").value = member.dataset.lane;
      bootstrap.Modal.getOrCreateInstance(moveDialog).show();
      return;
    }
    const remove = event.target.closest("[data-member-remove]");
    if (remove) {
      const member = remove.closest("[data-serial]");
      if (!removeMembership(member.dataset.serial, member.dataset.group)) {
        warn("無法移除這張憑證的群組。");
      }
    }
  });

  function renderCandidates() {
    const list = document.getElementById("group-add-results");
    const query = document.getElementById("group-add-search").value.trim().toLocaleLowerCase();
    list.replaceChildren();
    let matches = 0;
    for (const record of records) {
      if (!editable(record)) continue;
      if (laneFor(record.serial, addGroup)) continue;
      if (!`${record.name} ${record.cn} ${record.serial}`.toLocaleLowerCase().includes(query)) continue;
      matches++;
      const label = document.createElement("label");
      label.className = "group-add-candidate";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "form-check-input";
      checkbox.value = record.serial;
      checkbox.checked = selectedAdd.has(record.serial);
      const name = document.createElement("strong");
      name.textContent = record.name;
      const detail = document.createElement("small");
      detail.textContent = `CN ${record.cn} · CRL ID ${record.serial}`;
      label.append(checkbox, name, badge(record), detail);
      list.append(label);
    }
    document.getElementById("group-add-count").textContent = `符合搜尋 ${matches} 張；已選 ${selectedAdd.size} 張`;
    document.getElementById("group-add-apply").disabled = selectedAdd.size === 0;
    if (!matches) list.append(document.createTextNode("沒有可加入的憑證。"));
  }

  document.getElementById("group-add-search").addEventListener("input", renderCandidates);
  document.getElementById("group-add-results").addEventListener("change", (event) => {
    const box = event.target.closest('input[type="checkbox"]');
    if (!box) return;
    if (box.checked) selectedAdd.add(box.value);
    else selectedAdd.delete(box.value);
    renderCandidates();
  });
  document.getElementById("group-add-apply").addEventListener("click", () => {
    const lane = document.getElementById("group-add-lane").value;
    for (const serial of selectedAdd) {
      const groups = working.get(serial);
      if (lane === "in" || lane === "both") groups.in.add(addGroup);
      if (lane === "out" || lane === "both") groups.out.add(addGroup);
    }
    bootstrap.Modal.getInstance(addDialog).hide();
    statusFilter = "all";
    document.querySelector('[data-group-status="all"]').click();
  });
  document.getElementById("group-move-apply").addEventListener("click", () => {
    if (!moveSelection) return;
    const target = document.getElementById("group-move-target").value;
    const lane = document.getElementById("group-move-lane").value;
    if (moveMembership(moveSelection.serial, moveSelection.group, target, lane)) {
      bootstrap.Modal.getInstance(moveDialog).hide();
    }
  });

  document.getElementById("group-save").addEventListener("click", () => {
    const pending = changes();
    if (!pending.length) return;
    document.getElementById("group-changes").value = JSON.stringify(pending);
    const names = pending.map((item) => bySerial.get(item.serial).name);
    document.getElementById("group-confirm-summary").textContent =
      `將更新 ${pending.length} 張憑證：${names.join("、")}`;
    const check = document.getElementById("group-confirm-check");
    check.checked = false;
    document.getElementById("group-confirm-submit").disabled = true;
    bootstrap.Modal.getOrCreateInstance(document.getElementById("group-confirm-dialog")).show();
  });
  document.getElementById("group-confirm-check").addEventListener("change", (event) => {
    document.getElementById("group-confirm-submit").disabled = !event.target.checked;
  });
  render();
})();

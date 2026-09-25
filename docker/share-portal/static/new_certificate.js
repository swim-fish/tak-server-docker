(() => {
  document.addEventListener("change", (event) => {
    const preset = event.target.closest("[data-expiry-preset]");
    if (preset) {
      const input = preset.closest(".batch-device-row, .issue-grid")?.querySelector('input[name="expires_at"]');
      if (!input) return;
      if (preset.value === "default") input.value = "";
      else if (preset.value) input.value = new Date(Date.now() + (Number(preset.value) + 8) * 3600000).toISOString().slice(0, 16);
    } else if (event.target.matches('input[name="expires_at"]')) {
      const selection = event.target.closest(".batch-device-row, .issue-grid")?.querySelector("[data-expiry-preset]");
      if (selection) selection.value = "";
    }
  });
  const rows = document.getElementById("batch-rows");
  const add = document.getElementById("add-device");
  const template = document.getElementById("batch-device-template");
  if (!rows || !add) return;
  const renumber = () => {
    [...rows.querySelectorAll(".batch-device-row")].forEach((row, index) => {
      row.querySelector("[data-device-title]").textContent = `裝置 ${index + 1}`;
    });
    add.disabled = rows.children.length >= 10;
    rows.querySelectorAll(".remove-device").forEach((button) => {
      button.disabled = rows.children.length === 1;
    });
  };
  add.addEventListener("click", () => {
    if (rows.children.length >= 10) return;
    const row = template.content.firstElementChild.cloneNode(true);
    rows.append(row);
    window.initializeGroupBoard(row.querySelector("[data-group-board]"));
    renumber();
  });
  rows.addEventListener("click", (event) => {
    if (event.target.closest(".remove-device") && rows.children.length > 1) {
      event.target.closest(".batch-device-row").remove();
      renumber();
    }
  });
  renumber();
})();

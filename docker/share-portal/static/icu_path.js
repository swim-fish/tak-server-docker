(() => {
  const section = document.getElementById("icu-advanced-path");
  if (!section) return;

  const input = document.getElementById("icu-custom-path");
  const base = document.getElementById("icu-url-base").textContent;
  const preview = document.getElementById("icu-path-preview");
  const modes = document.querySelectorAll('input[name="icu_mode"]');
  const squad = document.querySelector('select[name="squad"]');
  const memberSection = document.getElementById("icu-standard-members");
  const members = [...memberSection.querySelectorAll('input[name="person"]')];
  const memberCount = document.getElementById("icu-members-count");
  let suggestedPath = "live/";

  function updateMemberCount() {
    memberCount.textContent = `已選 ${members.filter((member) => member.checked).length}／${members.length} 名隊員`;
  }

  function update() {
    const advanced = document.querySelector('input[name="icu_mode"]:checked')?.value === "advanced";
    memberSection.hidden = advanced;
    members.forEach((member) => { member.disabled = advanced; });
    section.hidden = !advanced;
    input.disabled = !advanced;
    input.required = advanced;
    const prefix = squad.value === "default" ? "live/" : `live/${squad.value}/`;
    input.setCustomValidity(advanced && !input.value.startsWith(prefix)
      ? `Stream Path must begin with ${prefix}` : "");
    if (advanced) {
      preview.textContent = input.checkValidity() ? `${base}${input.value}VIDEO_1` : `請輸入有效的 ${prefix} 路徑`;
    }
  }

  modes.forEach((mode) => mode.addEventListener("change", update));
  squad.addEventListener("change", () => {
    const next = squad.value === "default" ? "live/" : `live/${squad.value}/`;
    if (input.value === suggestedPath) input.value = next;
    suggestedPath = next;
    update();
  });
  input.addEventListener("input", update);
  document.getElementById("icu-members-all").addEventListener("click", () => {
    members.forEach((member) => { member.checked = true; });
    updateMemberCount();
  });
  document.getElementById("icu-members-none").addEventListener("click", () => {
    members.forEach((member) => { member.checked = false; });
    updateMemberCount();
  });
  members.forEach((member) => member.addEventListener("change", updateMemberCount));
  updateMemberCount();
  update();
})();

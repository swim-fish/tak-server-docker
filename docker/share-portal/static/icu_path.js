(() => {
  const section = document.getElementById("icu-advanced-path");
  if (!section) return;

  const input = document.getElementById("icu-custom-path");
  const base = document.getElementById("icu-url-base").textContent;
  const preview = document.getElementById("icu-path-preview");
  const modes = document.querySelectorAll('input[name="icu_mode"]');

  function update() {
    const advanced = document.querySelector('input[name="icu_mode"]:checked')?.value === "advanced";
    section.hidden = !advanced;
    input.disabled = !advanced;
    input.required = advanced;
    if (advanced) {
      preview.textContent = input.checkValidity() ? `${base}${input.value}VIDEO_1` : "請輸入有效的 live/ 路徑";
    }
  }

  modes.forEach((mode) => mode.addEventListener("change", update));
  input.addEventListener("input", update);
  update();
})();

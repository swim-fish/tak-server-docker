(() => {
  const input = document.getElementById("device-path");
  if (!input) return;
  const base = document.getElementById("device-url-base").textContent;
  const preview = document.getElementById("device-path-preview");
  const update = () => {
    preview.textContent = input.checkValidity()
      ? `${base}${input.value}`
      : "請輸入有效的 live/ 完整路徑";
  };
  input.addEventListener("input", update);
  update();
})();

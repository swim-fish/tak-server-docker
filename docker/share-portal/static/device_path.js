(() => {
  const input = document.getElementById("device-path");
  if (!input) return;
  const base = document.getElementById("device-url-base").textContent;
  const preview = document.getElementById("device-path-preview");
  const squadPrefix = /^live\/(?:alpha|bravo|charlie|delta|echo|foxtrot|golf|hotel)(?:\/|$)/;
  const update = () => {
    input.setCustomValidity(squadPrefix.test(input.value) ? "This path is reserved for an ICU squad" : "");
    preview.textContent = input.checkValidity()
      ? `${base}${input.value}`
      : "請輸入未占用小隊前綴的 live/ 完整路徑";
  };
  input.addEventListener("input", update);
  update();
})();

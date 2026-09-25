"use strict";
document.querySelectorAll(".device-links").forEach((panel) => {
  const reveal = panel.querySelector("[data-device-reveal]");
  const hide = panel.querySelector("[data-device-hide]");
  const cards = panel.querySelector("[data-device-cards]");
  const error = panel.querySelector("[data-device-error]");
  reveal.addEventListener("click", async () => {
    error.hidden = true;
    reveal.disabled = true;
    const spinner = document.createElement("span");
    spinner.className = "spinner-border spinner-border-sm me-2";
    spinner.setAttribute("aria-hidden", "true");
    reveal.prepend(spinner);
    try {
      const response = await fetch("/media/device/reveal", {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: new URLSearchParams({csrf: panel.dataset.csrf, key: panel.dataset.deviceKey})});
      if (!response.ok) throw new Error("Device links are unavailable");
      const urls = await response.json();
      for (const scheme of ["rtsp", "rtsps"]) {
        const card = panel.querySelector(`[data-protocol="${scheme}"]`);
        card.querySelector("input").value = urls[scheme];
        card.querySelector("img").src = `/media/device/qr/${encodeURIComponent(panel.dataset.deviceKey)}/${scheme}`;
      }
      cards.hidden = false; reveal.hidden = true; hide.hidden = false;
    } catch (_error) {
      error.hidden = false;
    } finally {
      spinner.remove();
      reveal.disabled = false;
    }
  });
  hide.addEventListener("click", () => {
    cards.hidden = true; hide.hidden = true; reveal.hidden = false;
    panel.querySelectorAll("input").forEach((field) => field.value = "");
    panel.querySelectorAll("img").forEach((image) => image.removeAttribute("src"));
  });
  panel.closest(".modal")?.addEventListener("hidden.bs.modal", () => {
    if (!hide.hidden) hide.click();
  });
  panel.querySelectorAll("[data-device-copy]").forEach((button) => button.addEventListener("click", async () => {
    await navigator.clipboard.writeText(button.closest("article").querySelector("input").value);
    button.textContent = "已複製";
  }));
});

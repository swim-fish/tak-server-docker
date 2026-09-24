"use strict";

document.addEventListener("submit", (event) => {
  const form = event.target;
  const submitter = event.submitter;
  if (event.defaultPrevented || !(form instanceof HTMLFormElement) ||
      !(submitter instanceof HTMLButtonElement) || !form.checkValidity()) return;
  if (submitter.querySelector(".spinner-border")) return;

  const spinner = document.createElement("span");
  spinner.className = "spinner-border spinner-border-sm me-2";
  spinner.setAttribute("aria-hidden", "true");
  submitter.prepend(spinner);
  submitter.setAttribute("aria-busy", "true");
});

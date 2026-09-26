(() => {
  const squad = document.querySelector('[data-batch-squad]');
  if (squad) {
    const choices = [...document.querySelectorAll('[data-alias-group]')];
    const selectedGroup = () => squad.selectedOptions[0]?.dataset.group;
    let previous = selectedGroup();
    if (!choices.some(choice => choice.checked)) {
      const initial = choices.find(choice => choice.value === previous);
      if (initial) initial.checked = true;
    }
    squad.addEventListener('change', () => {
      const oldChoice = choices.find(choice => choice.value === previous);
      if (oldChoice) oldChoice.checked = false;
      previous = selectedGroup();
      const current = choices.find(choice => choice.value === previous);
      if (current) current.checked = true;
    });
  }
  const carousel = document.getElementById('icu-batch-carousel');
  if (!carousel) return;
  const slides = [...carousel.querySelectorAll('.carousel-item')];
  const position = document.getElementById('icu-batch-position');
  carousel.addEventListener('slid.bs.carousel', () => {
    position.textContent = `${slides.findIndex(slide => slide.classList.contains('active')) + 1}／${slides.length}`;
  });
  const update = () => {
    for (const label of carousel.querySelectorAll('[data-batch-expiry]')) {
      const remaining = Math.max(0, Number(label.dataset.batchExpiry) * 1000 - Date.now());
      const minutes = Math.floor(remaining / 60000);
      const seconds = Math.floor(remaining / 1000) % 60;
      label.textContent = remaining ? `剩餘 ${minutes} 分 ${String(seconds).padStart(2, '0')} 秒` : '時間到期';
    }
  };
  update();
  setInterval(update, 1000);
})();

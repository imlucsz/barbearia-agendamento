/* Isolated visual study: no API, storage, personal data or real reservations. */
(() => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.nav');
  function closeMenu() {
    menu?.setAttribute('aria-expanded', 'false');
    nav?.classList.remove('is-open');
  }
  menu?.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  });
  nav?.addEventListener('click', event => {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') {
      closeMenu(); menu.focus();
    }
  });
  const dialog = document.querySelector('.prototype-dialog');
  let trigger;
  function openPreview(button) {
    trigger = button;
    const selected = button.dataset.service || document.querySelector('input[name="service"]:checked')?.value;
    const output = dialog.querySelector('.dialog-selected');
    output.textContent = selected ? `Você explorou: ${selected}.` : 'Você começa escolhendo um serviço.';
    dialog.showModal();
  }
  document.querySelectorAll('[data-preview]').forEach(button => {
    button.addEventListener('click', () => openPreview(button));
  });
  dialog?.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => dialog.close()));
  dialog?.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('button:not(:disabled)')];
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });
  dialog?.addEventListener('close', () => trigger?.focus());
  document.querySelectorAll('input[name="service"]').forEach(input => {
    input.addEventListener('change', () => {
      const summary = document.querySelector('[data-selection]');
      if (summary) summary.textContent = input.value;
    });
  });
  const sculpture = document.querySelector('.sculpture');
  document.querySelectorAll('[data-form]').forEach(button => {
    button.addEventListener('click', () => {
      sculpture.dataset.form = button.dataset.form;
      document.querySelectorAll('[data-form]').forEach(control => {
        control.setAttribute('aria-pressed', String(control === button));
      });
    });
  });
})();

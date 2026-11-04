// Local enhancement only: never read, copy, log or persist the input's value.
const selector = 'input[data-password-visibility]';
const controls = new WeakMap();
let nextId = 0;

function fieldsIn(root) {
  return [...(root.matches?.(selector) ? [root] : []), ...root.querySelectorAll(selector)];
}

function enhance(input) {
  if (controls.has(input)) {
    controls.get(input).syncDisabled();
    return;
  }
  if (input.type !== 'password') return;
  const document = input.ownerDocument;
  // Keep text-assistance features off when the same field becomes type=text.
  input.setAttribute('spellcheck', 'false');
  input.setAttribute('autocorrect', 'off');
  input.setAttribute('autocapitalize', 'none');
  if (!input.id) {
    let id;
    do { id = `password-visibility-${++nextId}`; } while (document.getElementById(id));
    input.id = id;
  }
  const wrapper = document.createElement('div');
  wrapper.className = 'password-control';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'password-visibility';
  button.setAttribute('aria-controls', input.id);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [key, value] of Object.entries({ viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.8', 'aria-hidden': 'true', focusable: 'false' })) {
    svg.setAttribute(key, value);
  }
  for (const d of ['M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z', 'M9 12a3 3 0 1 0 6 0 3 3 0 1 0-6 0']) {
    const path = document.createElementNS(svg.namespaceURI, 'path');
    path.setAttribute('d', d);
    svg.append(path);
  }
  const slash = document.createElementNS(svg.namespaceURI, 'path');
  slash.setAttribute('d', 'm3 3 18 18');
  svg.append(slash);
  button.append(svg);

  function show(visible) {
    const selection = [input.selectionStart, input.selectionEnd, input.selectionDirection];
    input.type = visible ? 'text' : 'password';
    if (selection[0] !== null) {
      try { input.setSelectionRange(...selection); } catch { /* Not supported by every input implementation. */ }
    }
    button.setAttribute('aria-label', visible ? 'Ocultar senha' : 'Mostrar senha');
    slash.setAttribute('visibility', visible ? 'visible' : 'hidden');
  }
  function syncDisabled() {
    button.disabled = input.matches(':disabled');
    if (button.disabled) show(false);
  }
  button.addEventListener('click', () => {
    syncDisabled();
    if (!button.disabled) show(input.type === 'password');
  });
  controls.set(input, { show, syncDisabled });
  // Retain the original node, labels, name, autocomplete and form ownership.
  input.before(wrapper);
  wrapper.append(input, button);
  show(false);
  syncDisabled();
}

export function initPasswordVisibility(root = document) {
  fieldsIn(root).forEach(enhance);
}

if (typeof document !== 'undefined') {
  initPasswordVisibility();
  document.addEventListener('reset', event => {
    if (event.target.matches('form')) fieldsIn(event.target).forEach(input => controls.get(input)?.show(false));
  }, true);
  const observer = new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') {
        fieldsIn(record.target).forEach(input => controls.get(input)?.syncDisabled());
      } else {
        record.addedNodes.forEach(node => {
          if (node.nodeType === 1) initPasswordVisibility(node);
        });
      }
    }
  });
  observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled'] });
}

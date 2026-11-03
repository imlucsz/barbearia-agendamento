/* Installed before GSAP: actual pending RAF requests, not a guessed FPS counter. */
(() => {
  const request = window.requestAnimationFrame.bind(window);
  const cancel = window.cancelAnimationFrame.bind(window);
  const pending = new Set(), callbacks = new Map();
  const stats = { pending, callbacks, frames: 0, maxPending: 0 };
  window.requestAnimationFrame = callback => {
    const id = request(time => { pending.delete(id); callbacks.delete(id); stats.frames++; callback(time); });
    pending.add(id); callbacks.set(id,callback.name||'callback anônimo'); stats.maxPending = Math.max(stats.maxPending, pending.size); return id;
  };
  window.cancelAnimationFrame = id => { pending.delete(id); callbacks.delete(id); cancel(id); };
  window.__labRAF = stats;
})();

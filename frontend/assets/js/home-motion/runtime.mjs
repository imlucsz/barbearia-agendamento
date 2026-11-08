export function createRuntime(gsap) {
  const tasks = new Map(), disposers = new Set();
  let subscribed = false, disposed = false, paused = false, reduced = false, listeners = 0;
  let canvasCount = 0, webglCount = 0, particleCount = 0;
  const eligible = task => task.visible && !paused && !reduced && !document.hidden && !disposed;
  const tick = (time, delta) => {
    const dt = Math.min(delta / 1000 || 1 / 60, .05);
    for (const task of tasks.values()) if (eligible(task)) task.draw(time, dt);
  };
  function sync() {
    const needed = [...tasks.values()].some(eligible);
    if (needed === subscribed) return;
    subscribed = needed;
    if (needed) gsap.ticker.add(tick); else gsap.ticker.remove(tick);
  }
  function listen(target, type, handler, options) {
    target.addEventListener(type, handler, options); listeners++;
    let removed = false;
    const off = () => { if (removed) return; removed = true; target.removeEventListener(type, handler, options); listeners--; disposers.delete(off); };
    disposers.add(off); return off;
  }
  function watch(node, onVisibility) {
    if (!globalThis.IntersectionObserver) { onVisibility(true); return () => {}; }
    const observer = new IntersectionObserver(entries => onVisibility(entries[0].isIntersecting), { threshold: 0 });
    observer.observe(node);
    const off = () => { observer.disconnect(); disposers.delete(off); };
    disposers.add(off); return off;
  }
  listen(document, 'visibilitychange', sync);
  return {
    listen, watch,
    addTask(name, draw, visible = false) {
      tasks.set(name, { draw, visible }); sync();
      return { visible(value) { const task = tasks.get(name); if (task) { task.visible = value; sync(); } }, remove() { tasks.delete(name); sync(); } };
    },
    setPaused(value) { paused = value; sync(); },
    setReduced(value) { reduced = value; sync(); },
    canvas(delta) { canvasCount += delta; },
    webgl(delta) { webglCount += delta; },
    particles(value) { particleCount = value; },
    get paused() { return paused; },
    get reduced() { return reduced; },
    snapshot() {
      return { continuousRAFLoops: subscribed ? 1 : 0, activeTasks: [...tasks].filter(([,t]) => eligible(t)).map(([name]) => name), scheduledRAF: window.__labRAF?.pending.size ?? 0, rafCallbacks: [...(window.__labRAF?.callbacks.values()||[])], canvases: canvasCount, webglContexts: webglCount, particles: particleCount, listeners, paused, reduced, disposed };
    },
    destroy() { if (disposed) return; disposed = true; sync(); tasks.clear(); for (const off of [...disposers]) off(); }
  };
}

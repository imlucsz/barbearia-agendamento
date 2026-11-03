// DevTools Snippet only. Never imported by the application. No network/storage.
(() => {
  window.ritualDiagnostics?.stop();
  const video = document.querySelector('#ritual-video');
  if (!video) throw new Error('Open HOME first');
  const descriptor = Object.getOwnPropertyDescriptor(HTMLMediaElement.prototype, 'currentTime');
  const originalOwn = Object.getOwnPropertyDescriptor(video, 'currentTime');
  const rows = [], offs = [], observers = [];
  let running = true, callback = null, lastFrames = null;
  const counts = { writes: 0, writesWhileSeeking: 0, seeking: 0, seeked: 0, frameCallbacks: 0, unobservedPresentedFrames: 0 };
  const quality = () => {
    const q = video.getVideoPlaybackQuality?.();
    return q ? { total: q.totalVideoFrames, dropped: q.droppedVideoFrames, corrupted: q.corruptedVideoFrames } : null;
  };
  const initialQuality = quality();
  function record(type, extra = {}) {
    if (rows.length >= 20000) return;
    const state = window.homeExperience?.snapshot().ritualVideo;
    const trigger = window.ScrollTrigger?.getById('lab-ritual') || window.ScrollTrigger?.getById('lab-ritual-mobile');
    rows.push({ ms: performance.now(), type, scrollProgress: trigger?.progress,
      desiredProgress: state?.desiredScrollProgress, targetTime: state?.desiredTime,
      currentTime: video.currentTime, seeking: video.seeking, readyState: video.readyState,
      mode: state?.mode, ...extra });
  }
  Object.defineProperty(video, 'currentTime', { configurable: true,
    get() { return descriptor.get.call(this); },
    set(value) {
      counts.writes++; if (this.seeking) counts.writesWhileSeeking++;
      record('write', { targetTime: value });
      descriptor.set.call(this, value);
    }
  });
  for (const type of ['seeking','seeked','waiting','stalled','progress','loadedmetadata','loadeddata','error','emptied']) {
    const handler = () => { if (type in counts) counts[type]++; record(type); };
    video.addEventListener(type, handler); offs.push(() => video.removeEventListener(type, handler));
  }
  function frame(now, metadata) {
    if (!running) return;
    counts.frameCallbacks++;
    if (lastFrames !== null) counts.unobservedPresentedFrames += Math.max(0, metadata.presentedFrames - lastFrames - 1);
    lastFrames = metadata.presentedFrames;
    record('frame', { mediaTime: metadata.mediaTime, presentedFrames: metadata.presentedFrames,
      processingDuration: metadata.processingDuration, expectedDisplayTime: metadata.expectedDisplayTime });
    callback = video.requestVideoFrameCallback(frame);
  }
  if (video.requestVideoFrameCallback) callback = video.requestVideoFrameCallback(frame);
  for (const type of ['long-animation-frame','longtask']) {
    if (!PerformanceObserver.supportedEntryTypes.includes(type)) continue;
    const observer = new PerformanceObserver(list => {
      for (const e of list.getEntries()) record(type, { startTime: e.startTime, duration: e.duration,
        blockingDuration: e.blockingDuration, forcedStyleAndLayoutDuration:
          e.scripts?.reduce((sum, s) => sum + (s.forcedStyleAndLayoutDuration || 0), 0) });
    });
    observer.observe({ type }); observers.push(observer);
  }
  const timer = setInterval(() => record('sample'), 100);
  function report() {
    return { userAgent: navigator.userAgent, viewport: [innerWidth,innerHeight], dpr: devicePixelRatio,
      desktopMQ: matchMedia('(min-width:1000px) and (min-height:650px)').matches,
      reduced: matchMedia('(prefers-reduced-motion:reduce)').matches,
      rvfcSupported: !!video.requestVideoFrameCallback, counts: { ...counts },
      initialQuality, finalQuality: quality(), buffered: Array.from({length:video.buffered.length},(_,i)=>[video.buffered.start(i),video.buffered.end(i)]),
      snapshot: window.homeExperience?.snapshot().ritualVideo, truncated: rows.length >= 20000, rows: [...rows] };
  }
  window.ritualDiagnostics = { report, stop() {
    if (!running) return report(); running = false; clearInterval(timer);
    if (callback !== null) video.cancelVideoFrameCallback(callback);
    offs.forEach(off => off()); observers.forEach(o => o.disconnect());
    if (originalOwn) Object.defineProperty(video,'currentTime',originalOwn); else delete video.currentTime;
    return report();
  }};
  record('start');
})();

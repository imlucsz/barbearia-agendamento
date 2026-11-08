// Adapted from home-experience.mjs at 3aa7a80; scoped to this preview's DOM.
// Original tab-session key and scissors pivots are intentionally preserved.
export function createHeroIntro(gsap) {
  const root = document.documentElement;
  const shell = document.querySelector('.h-opening');
  const skip = document.querySelector('[data-skip-hero-intro]');
  const title = document.querySelector('#hero-title');
  const tool = document.querySelector('.h-tool');
  const pole = document.querySelector('.h-pole');
  const glow = document.querySelector('.h-hero-glow');
  const lines = [...document.querySelectorAll('.h-headline-line')];
  const copy = [...document.querySelectorAll('.h-copy > .eyebrow, .h-intro')];
  const halves = [tool.querySelector('.half-front'), tool.querySelector('.half-back')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const key = 'barbearia.home.intro.v1';
  let seen = false, timeline, watchdog, active = false, plays = 0, destroyed = false;
  const offs = [];
  try { seen = sessionStorage.getItem(key) === 'seen'; } catch { /* Storage is optional. */ }
  const remember = () => { try { sessionStorage.setItem(key, 'seen'); } catch { /* No persistence available. */ } };
  function listen(target, event, callback, options) {
    target.addEventListener(event, callback, options);
    offs.push(() => target.removeEventListener(event, callback, options));
  }
  function scissorsAngle(angle) {
    halves.forEach((half, index) => gsap.set(half, { rotation: index ? angle : -angle, svgOrigin: '300 300' }));
  }
  function settle(reason) {
    const hadSkipFocus = document.activeElement === skip;
    active = false; clearTimeout(watchdog); timeline?.kill();
    gsap.set([tool, pole, ...lines, ...copy, glow], { clearProps: 'transform,opacity,zIndex' });
    scissorsAngle(7);
    shell.hidden = true; skip.hidden = true;
    root.classList.remove('h-opening-active');
    root.dataset.heroIntro = 'complete'; root.dataset.heroIntroReason = reason;
    remember();
    if (hadSkipFocus && (reason === 'skip' || reason === 'escape')) title.focus({ preventScroll: true });
  }
  const cancel = reason => { if (active) settle(reason); };
  const destroy = () => {
    if (destroyed) return;
    cancel('pagehide'); destroyed = true; clearTimeout(watchdog);
    offs.splice(0).forEach(off => off());
  };
  function start() {
    if (seen || reduced.matches || location.hash || scrollY > 12) {
      settle(seen ? 'seen' : reduced.matches ? 'reduced' : 'restored-position'); return;
    }
    active = true; plays++; remember();
    root.dataset.heroIntro = 'playing'; root.classList.add('h-opening-active');
    shell.hidden = false; skip.hidden = false;
    const small = matchMedia('(max-width:700px)').matches;
    const box = tool.getBoundingClientRect();
    gsap.set(tool, { x: innerWidth * .5 - (box.left + box.width / 2), y: innerHeight * .56 - (box.top + box.height / 2), rotation: -12, scale: .88, opacity: 0, zIndex: 54 });
    gsap.set(pole, { y: 16, opacity: 0 });
    gsap.set(lines, { y: 16, opacity: 0 });
    gsap.set(copy, { opacity: 0 });
    gsap.set('.h-opening-mark', { y: 8, opacity: 0 });
    gsap.set('.h-opening-seam', { opacity: 0, scaleY: .65 });
    gsap.set(glow, { opacity: 0 });
    scissorsAngle(23);
    timeline = gsap.timeline({ paused: true, defaults: { ease: 'power2.inOut' }, onComplete: () => settle('complete') });
    timeline.to('.h-opening-mark', { y: 0, opacity: 1, duration: .35 }, 0)
      .to(tool, { opacity: 1, duration: .25 }, .16)
      .to(halves[0], { rotation: 0, duration: .3, ease: 'power3.inOut' }, .43)
      .to(halves[1], { rotation: 0, duration: .3, ease: 'power3.inOut' }, .43)
      .to('.h-opening-seam', { opacity: .6, scaleY: 1, duration: .15 }, .64)
      .to('.h-opening-left', { xPercent: -101, duration: .75, ease: 'power3.inOut' }, .72)
      .to('.h-opening-right', { xPercent: 101, duration: .75, ease: 'power3.inOut' }, .72)
      .to('.h-opening-mark', { opacity: 0, duration: .25 }, .73)
      .to('.h-opening-seam', { opacity: 0, duration: .3 }, .79)
      .to(pole, { y: 0, opacity: 1, duration: .62, ease: 'power3.out' }, .94)
      .to(tool, { x: 0, y: 0, rotation: -24, scale: 1, duration: .8, ease: 'power3.inOut' }, .94)
      .to(lines, { y: 0, opacity: 1, duration: .56, stagger: .09, ease: 'power3.out' }, 1.08)
      .to(copy, { opacity: 1, duration: .42 }, 1.24)
      .to(glow, { opacity: .18, duration: .4 }, 1.12)
      .to(glow, { opacity: .1, duration: .45 }, 1.52)
      .to(halves[0], { rotation: -7, duration: .4 }, 1.55)
      .to(halves[1], { rotation: 7, duration: .4 }, 1.55)
      .to({}, { duration: .23 }, 1.97);
    if (small) timeline.timeScale(2.2 / 1.7);
    watchdog = setTimeout(() => cancel('watchdog'), 3000);
    timeline.play();
  }
  listen(skip, 'click', () => cancel('skip'));
  listen(document, 'keydown', event => {
    if (event.key === 'Escape') cancel('escape');
    if (event.key === 'Tab') cancel('tab');
  });
  listen(document, 'pointerdown', event => { if (event.target !== skip && !skip.contains(event.target)) cancel('interaction'); }, { capture: true });
  listen(window, 'wheel', () => cancel('scroll'), { passive: true });
  listen(window, 'touchmove', () => cancel('scroll'), { passive: true });
  listen(window, 'scroll', () => { if (scrollY > 12) cancel('scroll'); }, { passive: true });
  listen(window, 'resize', () => cancel('resize'));
  listen(reduced, 'change', () => { if (reduced.matches) cancel('reduced'); });
  listen(document, 'visibilitychange', () => { if (document.hidden) cancel('hidden'); });
  listen(window, 'pagehide', destroy);
  try { start(); } catch { settle('fallback'); }
  return { snapshot: () => ({ active, plays, reason: root.dataset.heroIntroReason, duration: timeline ? timeline.duration() / timeline.timeScale() : 0 }), destroy };
}

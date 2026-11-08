import { scissors, pole } from './home-motion/assets.mjs';
import { createRuntime } from './home-motion/runtime.mjs';
import { createVideoRitual } from './home-motion/ritual-video.mjs';
import { createHeroIntro } from './home-motion/intro.mjs';
import { INSTALLATION_CONFIG } from './installation-config.mjs';
import { normalizeBrandConfiguration } from './installation-brand.mjs';

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];

// Versioned SVG artwork is available even if the animation dependency fails.
function mountArtwork(selector, svg) {
  const parsed = new DOMParser().parseFromString(svg, 'image/svg+xml');
  if (parsed.querySelector('parsererror')) return;
  $(selector).append(document.importNode(parsed.documentElement, true));
}
mountArtwork('.hero-tool', scissors('home-tool'));
mountArtwork('[data-home-pole]', pole('home-pole'));

async function start() {
  const load = name => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = new URL('./vendor/gsap/' + name, import.meta.url);
    script.onload = resolve; script.onerror = reject;
    document.head.append(script);
  });
  await load('gsap.min.js');
  await load('ScrollTrigger.min.js');
  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);
  $('.intro-mark strong').textContent = $('.brand-copy strong').textContent;
  $('.intro-mark small').textContent = $('.brand-copy small').textContent;
  const brandMark = $('.brand-mark'), introMark = $('.intro-mark > span');
  const fallbackMark = normalizeBrandConfiguration(INSTALLATION_CONFIG.brand, location.href).mark;
  introMark.replaceChildren(...[...brandMark.childNodes].map(node => node.cloneNode(true)));
  introMark.querySelector('img')?.addEventListener('error', () => {
    introMark.textContent = fallbackMark;
  }, { once: true });
  const intro = createHeroIntro(gsap);
  const root = document.documentElement, runtime = createRuntime(gsap);
  let destroyed = false, refreshTimer = 0, controller;
  function scheduleRefresh() {
    if (destroyed) return;
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => { if (!destroyed) ScrollTrigger.refresh(); }, 120);
  }
  const mm = gsap.matchMedia();
  mm.add({ desktop: '(min-width:1000px) and (min-height:650px)', reduced: '(prefers-reduced-motion:reduce)', all: '(min-width:0px)' }, context => {
    runtime.setReduced(context.conditions.reduced);
    root.classList.toggle('experience-ready', !context.conditions.reduced);
    controller = createVideoRitual({ gsap, ScrollTrigger, runtime, ...context.conditions, scheduleRefresh });
    if (!context.conditions.reduced) {
      for (const node of $$('.section-heading,.step-card,.location-copy,.final-booking')) {
        gsap.fromTo(node, { y: 14 }, { y: 0, duration: .65, ease: 'power3.out', scrollTrigger: { trigger: node, start: 'top 92%', toggleActions: 'play none none reverse' } });
      }
    }
    return () => controller?.destroy();
  });
  for (const button of $$('#ritual [data-stage]')) {
    runtime.listen(button, 'click', () => controller?.goStage(Number(button.dataset.stage)));
  }
  const layoutObserver = globalThis.ResizeObserver ? new ResizeObserver(scheduleRefresh) : null;
  for (const node of $$('#services,#business-info,#reviews')) layoutObserver?.observe(node);
  const destroy = () => {
    if (destroyed) return;
    destroyed = true; intro.destroy(); layoutObserver?.disconnect();
    clearTimeout(refreshTimer); mm.revert(); runtime.destroy();
  };
  window.homeExperience = { destroy, snapshot: () => ({ ...runtime.snapshot(), scrollTriggers: ScrollTrigger.getAll().length, ritualVideo: controller?.snapshot(), intro: intro.snapshot() }) };
  runtime.listen(window, 'pagehide', event => { if (!event.persisted) destroy(); });
  runtime.listen(window, 'pageshow', event => { if (event.persisted) scheduleRefresh(); });
  document.fonts.ready.then(scheduleRefresh);
}
start().catch(() => {
  $('.intro-shell').hidden = true; $('#skip-intro').hidden = true;
  document.documentElement.classList.remove('experience-ready');
});

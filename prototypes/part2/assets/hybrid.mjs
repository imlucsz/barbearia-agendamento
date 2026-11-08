import { pole, scissors } from '/shared/js/home-motion/assets.mjs';
import { createRuntime } from '/shared/js/home-motion/runtime.mjs';
import { createVideoRitual } from '/shared/js/home-motion/ritual-video.mjs';
import { createHeroIntro } from './hero-intro.mjs';

// Both SVGs are trusted, versioned artwork already used by the application.
function mountArtwork(selector, svg) {
  const parsed = new DOMParser().parseFromString(svg, 'image/svg+xml');
  if (parsed.querySelector('parsererror')) return;
  document.querySelector(selector)?.append(document.importNode(parsed.documentElement, true));
}
mountArtwork('[data-hybrid-pole]', pole('hybrid-pole'));
mountArtwork('[data-hybrid-scissors]', scissors('hybrid-scissors'));

async function loadScript(name) {
  await new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `/shared/js/vendor/gsap/${name}`;
    script.onload = resolve; script.onerror = reject;
    document.head.append(script);
  });
}

try {
  await loadScript('gsap.min.js');
  await loadScript('ScrollTrigger.min.js');
  const { gsap, ScrollTrigger } = window;
  gsap.registerPlugin(ScrollTrigger);
  const intro = createHeroIntro(gsap);
  const runtime = createRuntime(gsap);
  let controller, refreshTimer;
  const scheduleRefresh = () => {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => ScrollTrigger.refresh(), 100);
  };
  const media = gsap.matchMedia();
  media.add({ desktop: '(min-width:1000px) and (min-height:650px)', reduced: '(prefers-reduced-motion:reduce)', all: '(min-width:0px)' }, context => {
    runtime.setReduced(context.conditions.reduced);
    controller = createVideoRitual({ gsap, ScrollTrigger, runtime, ...context.conditions, scheduleRefresh });
    document.documentElement.dataset.hybridReady = 'true';
    return () => controller?.destroy();
  });
  document.querySelectorAll('#ritual [data-stage]').forEach(button => {
    runtime.listen(button, 'click', () => controller?.goStage(Number(button.dataset.stage)));
  });
  document.fonts.ready.then(scheduleRefresh);
  // Read-only diagnostics for the isolated browser regression, not product state.
  window.hybridPreview = { snapshot: () => controller?.snapshot(), intro: () => intro.snapshot() };
  runtime.listen(window, 'pagehide', event => {
    if (event.persisted) return;
    clearTimeout(refreshTimer); media.revert(); runtime.destroy();
  });
} catch {
  // Static markup already includes the poster, all chapters and booking CTA.
  document.documentElement.dataset.hybridReady = 'fallback';
}

try {
  await import('/shared/js/estrelinha/cinematic.mjs');
} catch {
  // Optional local Three.js/WebGL: never block content or booking navigation.
  document.querySelectorAll('[data-estrelinha-cameo]').forEach(node => { node.hidden = true; });
}

// A single non-interactive portrait, shared by three brief editorial cameos.
import * as THREE from 'three';
import { gerarPet } from './pets/especies.js';
import { criarPet3D, animarPet } from './pets/malha.js';
import { anexarAventalBarbeiro, anexarItensBarbeiro } from './itens-barbeiro.js';

const slots = [...document.querySelectorAll('[data-estrelinha-cameo]')];
if (slots.length) {
  const canvas = document.createElement('canvas');
  canvas.className = 'estrela-cameo-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffefd4, 0x756043, 1.8));
  const light = new THREE.DirectionalLight(0xffe4aa, 2.1);
  light.position.set(-6, 12, 14); scene.add(light);
  const mascot = criarPet3D(gerarPet('estrelinha'));
  await anexarItensBarbeiro(THREE, mascot, {
    navalha: { braco: 'bracoD', pos: [2, -1.7, 4.8], escala: .018, rotZ: -2.5 },
    maquininha: { braco: 'bracoE', pos: [-4.4, .8, 4.8], escala: .24, rotZ: Math.PI / 2, src: null },
  });
  anexarAventalBarbeiro(THREE, mascot, { pos: [0, 3.6], z: 3.35, escala: .68 });
  scene.add(mascot.raiz);
  const camera = new THREE.OrthographicCamera(-17.5, 17.5, 17.5, -17.5, .1, 120);
  camera.position.set(0, 17.1, 60); camera.lookAt(0, 17.1, 0);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const seen = new WeakSet();
  let active = null, timer = 0, closed = false;
  function hide() { clearTimeout(timer); if (active) active.classList.remove('is-visible'); active = null; }
  function show(slot) {
    if (closed || document.hidden || seen.has(slot)) return;
    seen.add(slot); hide(); active = slot; slot.append(canvas);
    const size = Math.max(1, Math.round(slot.getBoundingClientRect().width));
    renderer.setSize(size, size, false);
    animarPet(mascot, 0, 'parado'); renderer.render(scene, camera);
    void slot.offsetWidth;
    slot.classList.add('is-visible');
    timer = setTimeout(hide, reduced.matches ? 1800 : slot.dataset.estrelinhaCameo === 'finale' ? 3600 : 2600);
  }
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) show(entry.target);
      else if (active === entry.target) hide();
    }
  }, { threshold: .35 });
  slots.forEach(slot => observer.observe(slot));
  const visibility = () => { if (document.hidden) hide(); };
  const preference = () => hide();
  document.addEventListener('visibilitychange', visibility);
  reduced.addEventListener('change', preference);
  window.addEventListener('pagehide', event => {
    if (event.persisted) { hide(); return; }
    closed = true; hide(); observer.disconnect();
    document.removeEventListener('visibilitychange', visibility);
    reduced.removeEventListener('change', preference);
    scene.traverse(object => {
      object.geometry?.dispose();
      for (const material of (Array.isArray(object.material) ? object.material : [object.material])) material?.dispose();
    });
    renderer.dispose();
  });
}

import * as THREE from 'three'
import { gerarPet } from './pets/especies.js'
import { animarPet, criarPet3D } from './pets/malha.js'
import { anexarAventalBarbeiro, anexarItensBarbeiro } from './itens-barbeiro.js'

const ITENS = {
  navalha: { braco: 'bracoD', pos: [2.0, -1.7, 4.8], escala: 0.018, rotZ: -2.5 },
  // Troque src para a URL de um PNG limpo quando ele estiver disponível.
  maquininha: { braco: 'bracoE', pos: [-4.4, 0.8, 4.8], escala: 0.24, rotZ: Math.PI / 2, src: null },
}
const AVENTAL = { pos: [0, 3.6], z: 3.35, escala: 0.68 }
const som = new Audio(new URL('../../audio/starsound.mp3', import.meta.url).href)
som.preload = 'auto'
som.addEventListener('error', () => {
  console.warn('Falha ao carregar starsound:', som.currentSrc || som.src)
})

const mount = document.querySelector('[data-estrelinha-barbeiro]')
if (!mount) throw new Error('Adicione data-estrelinha-barbeiro dentro do card do hero.')

mount.innerHTML = '<canvas class="estrela-canvas" role="button" tabindex="0" aria-label="Estrelinha barbeiro. Clique para ela acenar."></canvas>'
const canvas = mount.querySelector('canvas')
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
renderer.outputColorSpace = THREE.SRGBColorSpace
renderer.setClearColor(0x000000, 0)

const scene = new THREE.Scene()
scene.add(new THREE.HemisphereLight(0xffffff, 0x8e704d, 2))
const key = new THREE.DirectionalLight(0xfff3d5, 2.1)
key.position.set(-6, 12, 14)
scene.add(key)
const fill = new THREE.DirectionalLight(0xffd078, 0.65)
fill.position.set(9, 5, 5)
scene.add(fill)

const mascot = criarPet3D(gerarPet('estrelinha'))
mascot.raiz.scale.setScalar(1.08)
await anexarItensBarbeiro(THREE, mascot, ITENS)
anexarAventalBarbeiro(THREE, mascot, AVENTAL)
scene.add(mascot.raiz)

const viewHeight = 35
const camera = new THREE.OrthographicCamera(-15, 15, 15, -15, 0.1, 120)
camera.position.set(0, 17.1, 60)
camera.lookAt(0, 17.1, 0)

const resize = () => {
  const { width, height } = canvas.getBoundingClientRect()
  if (!width || !height) return
  const mobile = width < 600
  const cameraTargetY = mobile ? 14.6 : 17.1
  mascot.raiz.scale.setScalar(mobile ? 0.9 : 1.08)
  camera.position.y = cameraTargetY
  camera.lookAt(0, cameraTargetY, 0)
  renderer.setSize(width, height, false)
  const halfHeight = viewHeight / 2
  const halfWidth = halfHeight * (width / height)
  camera.left = -halfWidth
  camera.right = halfWidth
  camera.top = halfHeight
  camera.bottom = -halfHeight
  camera.updateProjectionMatrix()
  render(performance.now())
}

let waveUntil = 0
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
const barberPole = document.querySelector('[data-barber-pole]')
if (barberPole) {
  const animatedSrc = barberPole.dataset.animatedSrc
  const stillSrc = barberPole.dataset.stillSrc
  const syncBarberPole = () => { barberPole.src = motionPreference.matches ? stillSrc : animatedSrc }
  syncBarberPole()
  motionPreference.addEventListener('change', syncBarberPole)
}
const render = (now) => {
  const t = now / 1000
  animarPet(mascot, t, now < waveUntil && !motionPreference.matches ? 'acenar' : 'parado')
  mascot.raiz.rotation.y = 0
  renderer.render(scene, camera)
}

const animate = (now) => {
  render(now)
  if (!motionPreference.matches) requestAnimationFrame(animate)
}
new ResizeObserver(resize).observe(canvas)
resize()
if (!motionPreference.matches) requestAnimationFrame(animate)
motionPreference.addEventListener('change', () => requestAnimationFrame(animate))

const wave = () => {
  if (motionPreference.matches) return
  waveUntil = performance.now() + 2400
}
const interagir = () => {
  wave()
  som.currentTime = 0
  som.play().catch((e) => console.warn('Falha ao tocar starsound:', e))
}
canvas.addEventListener('click', interagir)
canvas.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    interagir()
  }
})

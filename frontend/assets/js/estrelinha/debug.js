import * as THREE from 'three'
import { gerarPet } from './pets/especies.js'
import { animarPet, criarPet3D, mostrarParte } from './pets/malha.js'
import { anexarAventalBarbeiro, anexarItensBarbeiro } from './itens-barbeiro.js'

const ITENS_DEBUG = {
  navalha: { braco: 'bracoD', pos: [2.0, -1.7, 4.8], escala: 0.018, rotZ: -2.5 },
  maquininha: { braco: 'bracoE', pos: [-4.4, 0.8, 4.8], escala: 0.24, rotZ: Math.PI / 2, src: null },
}
const AVENTAL_DEBUG = { pos: [0, 3.6], z: 3.35, escala: 0.68 }

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
const animationEnabled = !reducedMotion.matches && !new URLSearchParams(location.search).has('still')
const angleHeight = (angle) => ({ frente: 41, 'tres-quartos': 45, lado: 34 })[angle] ?? 41
const stages = [...document.querySelectorAll('canvas[data-view]')].map((canvas) => {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: false, antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.setClearColor(0x000000, 1)

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x000000)
  scene.add(new THREE.HemisphereLight(0xffffff, 0x777777, 2.1))
  const key = new THREE.DirectionalLight(0xffffff, 2.4)
  key.position.set(-8, 15, 18)
  scene.add(key)
  const fill = new THREE.DirectionalLight(0xffd17d, 0.45)
  fill.position.set(12, 5, 10)
  scene.add(fill)

  const pet = criarPet3D(gerarPet('estrelinha'))
  pet.raiz.scale.setScalar(1)
  const itens2D = {}
  itens2D.avental = anexarAventalBarbeiro(THREE, pet, AVENTAL_DEBUG)
  const itemsReady = anexarItensBarbeiro(THREE, pet, ITENS_DEBUG).then((meshes) => {
    for (const mesh of meshes) itens2D[mesh.name.replace('item-2d-', '')] = mesh
  })
  scene.add(pet.raiz)

  const viewHeight = angleHeight(canvas.dataset.view)
  const camera = new THREE.OrthographicCamera(-17, 17, 17, -17, 0.1, 200)
  const target = new THREE.Vector3(0, 13.5, 0)
  const angle = canvas.dataset.view
  const positions = {
    frente: [0, 13.5, 75],
    'tres-quartos': [48, 26, 52],
    lado: [75, 13.5, 0],
  }
  camera.position.set(...positions[angle])
  camera.lookAt(target)

  const resize = () => {
    const { width, height } = canvas.getBoundingClientRect()
    if (!width || !height) return
    renderer.setSize(width, height, false)
    const halfHeight = viewHeight / 2
    const halfWidth = halfHeight * width / height
    camera.left = -halfWidth
    camera.right = halfWidth
    camera.top = halfHeight
    camera.bottom = -halfHeight
    camera.updateProjectionMatrix()
    draw(performance.now())
  }
  new ResizeObserver(resize).observe(canvas)

  let waveUntil = new URLSearchParams(location.search).has('wave') ? performance.now() + 8000 : 0
  const draw = (now) => {
    const t = now / 1000
    animarPet(pet, t, now < waveUntil ? 'acenar' : 'parado')
    renderer.render(scene, camera)
  }
  const animate = (now) => {
    draw(now)
    if (animationEnabled) requestAnimationFrame(animate)
  }
  itemsReady.then(() => {
    resize()
    if (animationEnabled) requestAnimationFrame(animate)
  }).catch((error) => console.error(error))

  const wave = () => {
    if (!animationEnabled) return
    waveUntil = performance.now() + 2200
  }
  canvas.addEventListener('click', wave)
  canvas.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      wave()
    }
  })
  canvas.tabIndex = 0
  canvas.setAttribute('role', 'button')
  return { pet, itens2D, render: () => draw(performance.now()) }
})

document.querySelectorAll('[data-parte]').forEach((button) => {
  button.addEventListener('click', () => {
    const visible = button.getAttribute('aria-pressed') !== 'true'
    button.setAttribute('aria-pressed', String(visible))
    for (const stage of stages) {
      if (button.dataset.item) {
        const mesh = stage.itens2D[button.dataset.item]
        if (mesh) mesh.visible = visible
      } else {
        mostrarParte(stage.pet, button.dataset.parte, visible)
      }
      stage.render()
    }
  })
})

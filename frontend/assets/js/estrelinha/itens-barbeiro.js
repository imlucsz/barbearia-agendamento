function carregarImagem(src) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error(`Falha ao carregar o item: ${src}`))
    image.src = src
  })
}

function texturaPixelArt(THREE, image) {
  const texture = new THREE.Texture(image)
  texture.colorSpace = THREE.SRGBColorSpace
  texture.magFilter = THREE.NearestFilter
  texture.minFilter = THREE.NearestFilter
  texture.generateMipmaps = false
  texture.needsUpdate = true
  return texture
}

function texturaMaquininha(THREE) {
  const grade = [
    '...LLLL...',
    '..LLLLLL..',
    '..LGLGLL..',
    '..DDDDDD..',
    '.DDDDDDD..',
    '.DDWWDDD..',
    '.DDWWDDD..',
    '.DDDDDDD..',
    '.DDWDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '.DDDDDDD..',
    '..DDDDD...',
    '..DDDDD...',
  ]
  const paleta = { D: '#292725', G: '#77736e', L: '#c9c5bd', W: '#f1ece2' }
  const canvas = document.createElement('canvas')
  canvas.width = 10
  canvas.height = 20
  const context = canvas.getContext('2d')
  context.clearRect(0, 0, canvas.width, canvas.height)
  grade.forEach((linha, y) => [...linha].forEach((pixel, x) => {
    if (paleta[pixel]) {
      context.fillStyle = paleta[pixel]
      context.fillRect(x, y, 1, 1)
    }
  }))
  return texturaPixelArt(THREE, canvas)
}

function texturaAvental(THREE) {
  const grade = [
    'BBBBBBBBB',
    'AAAAAAAAA',
    'AADDDDDAA',
    'AAD....AA',
    'AAD....AA',
    'AADDDD.AA',
    'AAD....AA',
    'AAD....AA',
    'AADDDDDAA',
    'SSSSSSSSS',
  ]
  const paleta = {
    A: '#eadcc0',
    B: '#6a4a34',
    D: '#8a643f',
    S: '#cdb590',
    '.': '#eadcc0',
  }
  const canvas = document.createElement('canvas')
  canvas.width = 9
  canvas.height = 10
  const context = canvas.getContext('2d')
  grade.forEach((linha, y) => [...linha].forEach((pixel, x) => {
    context.fillStyle = paleta[pixel]
    context.fillRect(x, y, 1, 1)
  }))
  return texturaPixelArt(THREE, canvas)
}

export function anexarAventalBarbeiro(THREE, mascot, config) {
  const texture = texturaAvental(THREE)
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(9 * config.escala, 10 * config.escala),
    new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      alphaTest: 0.5,
      side: THREE.DoubleSide,
    }),
  )
  mesh.name = 'avental-barbeiro-2d'
  mesh.position.set(config.pos[0], config.pos[1], config.z)
  mascot.grupos.corpo.add(mesh)
  return mesh
}

/** Cria os planos 2D como filhos dos grupos dos braços para acompanharem as animações. */
export async function anexarItensBarbeiro(THREE, mascot, itens) {
  const navalhaSrc = new URL('../../images/navalha-recortada.png', import.meta.url).href
  const meshes = []

  for (const [nome, config] of Object.entries(itens)) {
    const texture = nome === 'maquininha' && !config.src
      ? texturaMaquininha(THREE)
      : texturaPixelArt(THREE, await carregarImagem(config.src || navalhaSrc))
    const image = texture.image
    const plane = new THREE.PlaneGeometry(image.width * config.escala, image.height * config.escala)
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      alphaTest: 0.5,
      side: THREE.DoubleSide,
    })
    const mesh = new THREE.Mesh(plane, material)
    mesh.name = `item-2d-${nome}`
    mesh.position.set(...config.pos)
    mesh.rotation.z = config.rotZ
    mascot.grupos[config.braco].add(mesh)
    meshes.push(mesh)
  }
  return meshes
}

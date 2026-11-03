// The only Three.js scene in this study. No control over intro, Ritual or CTA.
export async function createPoleStudy(canvas, runtime) {
  const THREE = await import('three');
  const renderer = new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'low-power'});
  const host=canvas.parentElement,disposers=[];
  let closed=false,lost=false,counted=false;
  disposers.push(()=>renderer.forceContextLoss(),()=>renderer.dispose());
  function release() {
    if(closed)return;closed=true;
    for(const dispose of disposers.reverse()){try{dispose();}catch{}}
    host.classList.remove('is-ready');canvas.width=1;canvas.height=1;
    if(counted){runtime.canvas(-1);runtime.webgl(-1);counted=false;}
  }
  try {
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1,1.5));
  renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.3;
  renderer.setClearColor(0x000000,0);
  runtime.canvas(1); runtime.webgl(1);counted=true;
  const scene=new THREE.Scene(), group=new THREE.Group(); scene.add(group);
  const releaseTree=tree=>{const geometries=new Set(),materials=new Set();tree.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)materials.add(o.material);});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());};
  disposers.push(()=>releaseTree(scene));
  const camera=new THREE.PerspectiveCamera(29,1,.1,50); camera.position.set(3.5,1.3,10); camera.lookAt(0,0,0);
  scene.add(new THREE.HemisphereLight(0xfff4d5,0x1e382b,2));
  function area(color,power,x,y,z,w,h) { const light=new THREE.RectAreaLight(color,power,w,h); light.position.set(x,y,z); light.lookAt(0,0,0); scene.add(light); }
  area(0xffe4ac,9,-3,3,4,2,6); area(0xf4fff4,7,3,1,1,1,5); area(0xb68843,5,-2,-2,-1,2,3);
  const key=new THREE.DirectionalLight(0xffe7ad,3); key.position.set(-3,5,5);scene.add(key);
  // A tiny procedural studio environment gives metal actual broad reflections.
  const envScene=new THREE.Scene();envScene.background=new THREE.Color(0x171e19);
  disposers.push(()=>releaseTree(envScene));
  for (const [x,z,w,color] of [[-4,0,1.6,0xffe4b4],[3,-2,.8,0xd3ead4],[0,4,.35,0xfff8d9]]) {
    const card=new THREE.Mesh(new THREE.PlaneGeometry(w,7),new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide}));card.position.set(x,1,z);card.lookAt(0,0,0);envScene.add(card);
  }
  const pmrem=new THREE.PMREMGenerator(renderer);disposers.push(()=>pmrem.dispose());
  const env=pmrem.fromScene(envScene,.08);disposers.push(()=>env.dispose());scene.environment=env.texture;
  const metal=new THREE.MeshStandardMaterial({color:0xbba879,metalness:1,roughness:.23,envMapIntensity:1.4});
  const darkMetal=new THREE.MeshStandardMaterial({color:0x343c32,metalness:.9,roughness:.26});
  const ivory=new THREE.MeshStandardMaterial({color:0xded7bd,metalness:.18,roughness:.34});
  const gold=new THREE.MeshStandardMaterial({color:0xb18b49,metalness:.72,roughness:.3});
  const black=new THREE.MeshStandardMaterial({color:0x122823,metalness:.3,roughness:.4});
  const drum=new THREE.Group();group.add(drum);
  function mesh(geometry,material,y=0,parent=group) { const o=new THREE.Mesh(geometry,material);o.position.y=y;parent.add(o);return o; }
  mesh(new THREE.CylinderGeometry(.46,.46,3.58,64),ivory,0,drum);
  // Wrapped ribbon surfaces: y = pitch * (angle/2π + phase), clipped to drum.
  function ribbon(material,phase) {
    const positions=[],indices=[];const segments=320, turns=5.4,pitch=.88,halfWidth=.115;
    for(let i=0;i<=segments;i++) {const angle=i/segments*turns*Math.PI*2;for(const side of [-1,1]) {const y=-2.4+angle/(Math.PI*2)*pitch+phase+side*halfWidth; positions.push(Math.cos(angle)*.465,Math.max(-1.78,Math.min(1.78,y)),Math.sin(angle)*.465);} if(i<segments){const k=i*2;indices.push(k,k+1,k+2,k+1,k+3,k+2);} }
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));geometry.setIndex(indices);geometry.computeVertexNormals();mesh(geometry,material,0,drum);
  }
  ribbon(gold,0);ribbon(black,.29);
  for(const sign of [-1,1]) {
    mesh(new THREE.CylinderGeometry(.58,.58,.16,64),metal,sign*1.87);
    mesh(new THREE.CylinderGeometry(.53,.58,.08,64),darkMetal,sign*1.98);
    const cap=mesh(new THREE.SphereGeometry(.56,64,32),metal,sign*2.03);cap.scale.y=.45;
    mesh(new THREE.CylinderGeometry(.11,.11,.28,32),metal,sign*2.37);
    const tip=mesh(new THREE.SphereGeometry(.13,32,16),metal,sign*2.52);tip.scale.y=.6;
    const ring=mesh(new THREE.TorusGeometry(.535,.018,12,64),metal,sign*1.76);ring.rotation.x=Math.PI/2;
  }
  // Outer glass is a low-cost sheen, not transmission/refraction postprocessing.
  const glass=new THREE.MeshPhysicalMaterial({color:0xe8f0d0,metalness:.05,roughness:.13,transparent:true,opacity:.13,clearcoat:1,clearcoatRoughness:.12,depthWrite:false});
  mesh(new THREE.CylinderGeometry(.488,.488,3.57,64,1,true),glass);
  group.rotation.z=-.025;
  function resize() {const b=host.getBoundingClientRect();if(!b.width||!b.height)return;renderer.setSize(b.width,b.height,false);camera.aspect=b.width/b.height;camera.updateProjectionMatrix();renderer.render(scene,camera);}
  resize();
  const task=runtime.addTask('barber pole Three.js',(time)=>{if(lost)return;drum.rotation.y=time*.16;group.rotation.y=Math.sin(time*.11)*.13;renderer.render(scene,camera);});
  disposers.push(()=>task.remove());
  const unwatch=runtime.watch(host,visible=>task.visible(visible&&!lost));
  disposers.push(unwatch);
  const observer=new ResizeObserver(resize);disposers.push(()=>observer.disconnect());observer.observe(host);
  const offLost=runtime.listen(canvas,'webglcontextlost',event=>{event.preventDefault();lost=true;task.visible(false);host.classList.remove('is-ready');document.querySelector('#three-status').textContent='Contexto indisponível — representação SVG ativa.';document.querySelector('#three-retry').hidden=false;});
  disposers.push(offLost);
  host.classList.add('is-ready');document.querySelector('#three-status').textContent='Volume real. Reflexo de estúdio. Rotação lenta.';
  return {
    render:resize,
    stats:()=>({drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles}),
    destroy:release
  };
  }catch(error){release();throw error;}
}

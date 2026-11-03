// One Canvas, no private RAF. Impact is evaluated from intro time, so seeking/replay
// reproduces the same causal reaction instead of accumulating random emitters.
export function createDust(canvas, hero, runtime) {
  const context = canvas.getContext('2d');
  if (!context) return { setIntro() {}, resize() {}, destroy() {} };
  runtime.canvas(1);
  let width = 1, height = 1, clock = 0, introTime = 4, impact = 1.49, closed = false, impactOrigin = null;
  let count = matchMedia('(max-width: 767px)').matches ? 23 : 62;
  const random = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const motes = Array.from({length: 62}, (_, i) => ({ x: random(i+1), y: random(i+81), r: .3 + random(i+230)*1.15, phase: random(i+32)*6.28, speed: .002 + random(i+52)*.004 }));
  function resize() {
    const box = hero.getBoundingClientRect(); width = box.width; height = box.height; count=width<768?23:62;
    const dpr = Math.min(devicePixelRatio || 1, width < 768 ? 1 : 1.5);
    canvas.width = Math.round(width*dpr); canvas.height = Math.round(height*dpr);
    context.setTransform(dpr,0,0,dpr,0,0);
    runtime.particles(runtime.reduced?0:count);
  }
  function draw(_time,dt) {
    clock += dt; context.clearRect(0,0,width,height);
    if (runtime.reduced) { runtime.particles(0); return; }
    const t = introTime-impact, burst = t > 0 && t < 1.65;
    const originX = impactOrigin?.x ?? width*.61, originY = impactOrigin?.y ?? height*.53;
    context.globalCompositeOperation = 'lighter';
    for (let i=0;i<count;i++) {
      const m=motes[i], driftX=Math.sin(clock*.12+m.phase)*9;
      let x=((m.x+clock*m.speed*.12)%1)*width+driftX;
      let y=((m.y-clock*m.speed*.2+20)%1)*height;
      let alpha=.08+.16*(.5+.5*Math.sin(clock*.22+m.phase));
      let radius=m.r;
      if (burst && i<Math.floor(count*.66)) {
        const angle=(random(i+400)*2-1)*Math.PI;
        const speed=40+random(i+500)*145;
        const distance=speed*(1-Math.exp(-t*2.8))/2.8;
        x=originX+Math.cos(angle)*distance; y=originY+Math.sin(angle)*distance*.55+t*t*22;
        alpha=Math.max(0,(1-t/1.65))*(.3+random(i+600)*.6); radius=m.r*(i%7===0?1.4:.8);
      }
      const lit=Math.max(.12,1-Math.abs(x-width*.62)/(width*.7));
      context.fillStyle=`rgba(237,211,156,${alpha*lit})`;
      context.beginPath(); context.ellipse(x,y,radius,radius*(i%6===0?.38:1),-.6,0,Math.PI*2); context.fill();
      if (burst && i%8===0) { context.fillStyle=`rgba(255,242,207,${alpha*.25})`; context.beginPath(); context.arc(x,y,radius*4,0,Math.PI*2); context.fill(); }
    }
    context.globalCompositeOperation='source-over'; runtime.particles(count);
  }
  resize();
  const task=runtime.addTask('poeira Canvas 2D',draw);
  const unwatch=runtime.watch(hero,visible=>task.visible(visible));
  const resizeObserver=new ResizeObserver(resize); resizeObserver.observe(hero);
  const off=runtime.listen(window,'resize',resize,{passive:true});
  return {
    setIntro(time,impactAt=1.49) {
      if (introTime<impactAt && time>=impactAt) {
        const matrix=hero.querySelector('.hero-tool .half-front')?.getScreenCTM();
        if(matrix){const point=new DOMPoint(430,300).matrixTransform(matrix),box=hero.getBoundingClientRect();impactOrigin={x:point.x-box.left,y:point.y-box.top};}
      }
      introTime=time; impact=impactAt;
    },
    clear() { context.clearRect(0,0,width,height); runtime.particles(0); },
    resize,
    destroy() { if(closed)return; closed=true; task.remove(); unwatch(); off(); resizeObserver.disconnect(); context.clearRect(0,0,width,height); canvas.width=1; canvas.height=1; runtime.canvas(-1); runtime.particles(0); }
  };
}

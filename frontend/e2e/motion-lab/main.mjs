import { scissors, pole, mirror } from './assets.mjs';
import { createRuntime } from './runtime.mjs';
import { createDust } from './particles.mjs';
import { createVideoRitual } from './ritual-video.mjs';

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const mirrorStudy=new URLSearchParams(location.search).get('ritual')==='mirror';
if(mirrorStudy){const response=await fetch(new URL('./ritual-mirror.html',import.meta.url));if(response.ok)$('#ritual').outerHTML=await response.text();}
for (const node of $$('[data-scissors]')) node.innerHTML=scissors(`scissors-${node.dataset.scissors}`);
for (const node of $$('[data-pole]')) node.innerHTML=pole(`pole-${node.dataset.pole}`);
if($('.mirror-mount'))$('.mirror-mount').innerHTML=mirror('ritual');

try {
  const [{gsap},{ScrollTrigger},{CustomEase}]=await Promise.all([import('gsap'),import('gsap/ScrollTrigger'),import('gsap/CustomEase')]);
  initialize(gsap,ScrollTrigger,CustomEase);
} catch (error) {
  document.documentElement.classList.add('motion-reduced');
  $('#lab-status').textContent='Motor de movimento indisponível. Composição estática disponível.';
  $('#pause').disabled=true; $('#replay').disabled=true;
  console.warn('Motion Lab: apresentação estática.',error.message);
}

function initialize(gsap,ScrollTrigger,CustomEase) {
  gsap.registerPlugin(ScrollTrigger,CustomEase);
  CustomEase.create('ritual-precision','M0,0 C0.48,0 0.66,0.08 0.74,0.54 0.82,0.94 0.89,1 1,1');
  CustomEase.create('ritual-premium','.4,0,.2,1');
  const root=document.documentElement, runtime=createRuntime(gsap), hero=$('.hero');
  const dust=createDust($('#dust'),hero,runtime);
  let intro=null, introActive=false, introClock=4, watchdog=0, destroyed=false, scene3D=null, loading3D=false, failed3D=false;
  let ritualTimeline=null, ritualTrigger=null, metricsTimer=0, refreshTimer=0, lastStage=-1;
  let videoRitual=null,lastVideoSnapshot=null;
  const mm=gsap.matchMedia();
  const sessionKey='barbearia.motionlab.intro.v1';
  let seen=false; try { seen=sessionStorage.getItem(sessionKey)==='seen'; } catch {}
  const reducedMQ=matchMedia('(prefers-reduced-motion: reduce)');
  const mobileMQ=matchMedia('(max-width: 767px)');
  const ownTweens=new Set();
  let threeVisibility=false;

  // Shared GSAP ticker: Canvas, SVG stripes and Three never start their own RAF.
  for (const host of $$('[data-pole]:not([data-pole="fallback"])')) {
    const pattern=host.querySelector('pattern');
    const task=runtime.addTask(`faixas SVG ${host.dataset.pole}`,time=>pattern.setAttribute('patternTransform',`translate(0 ${time*7}) rotate(-32)`));
    runtime.watch(host,visible=>task.visible(visible));
  }

  function closeScissors(host,angle) {
    gsap.set(host.querySelector('.half-front'),{rotation:-angle,svgOrigin:'300 300'});
    gsap.set(host.querySelector('.half-back'),{rotation:angle,svgOrigin:'300 300'});
  }
  closeScissors($('.hero-tool'),7);if($('.ritual-tool'))closeScissors($('.ritual-tool'),17);

  function settleIntro(reason='complete') {
    if (destroyed && reason!=='destroy') return;
    const hadSkipFocus=document.activeElement===$('#skip-intro');
    clearTimeout(watchdog); intro?.pause();
    // Seek final values without invoking callbacks/recursive completion.
    intro?.progress(1,true);
    introActive=false; introClock=4; dust.setIntro(4);
    $('.intro-shell').hidden=true; $('#skip-intro').hidden=true;
    gsap.set($('.hero-tool'),{x:0,y:0,scale:1,rotation:-24,opacity:1,zIndex:4});
    gsap.set($('.hero-pole'),{x:0,y:0,scale:1,opacity:1,zIndex:3});
    gsap.set($$('.headline-line'),{yPercent:0,opacity:1});
    gsap.set(['.hero-kicker','.hero-detail','.hero-footer'],{opacity:1});
    gsap.set('.hero-beam',{opacity:.18});
    closeScissors($('.hero-tool'),7);
    root.classList.remove('intro-playing');
    root.dataset.intro='complete';
    try {sessionStorage.setItem(sessionKey,'seen');}catch{}
    if(hadSkipFocus && (reason==='skip'||reason==='escape')) {$('#hero-title').tabIndex=-1;$('#hero-title').focus({preventScroll:true});}
  }

  function buildIntro(manual=false) {
    if(destroyed||reducedMQ.matches) {settleIntro('reduced');return null;}
    intro?.kill(); clearTimeout(watchdog);
    window.scrollTo({top:0,behavior:'instant'});
    const tool=$('.hero-tool'), poleNode=$('.hero-pole');
    gsap.set([tool,poleNode],{clearProps:'transform'});
    const box=tool.getBoundingClientRect(), poleBox=poleNode.getBoundingClientRect();
    const small=mobileMQ.matches;
    const x=innerWidth*.5-(box.left+box.width*.44);
    const y=innerHeight*(small?.56:.56)-(box.top+box.height*.5);
    introActive=true;introClock=0;root.dataset.intro='playing';root.classList.add('intro-playing');
    $('.intro-shell').hidden=false;$('#skip-intro').hidden=false;
    gsap.set('.intro-panel',{xPercent:0});
    gsap.set('.intro-mark',{opacity:0,y:12,scale:.98});
    gsap.set('.intro-caption',{opacity:0});gsap.set('.intro-seam',{opacity:0,scaleY:.5});
    gsap.set('.hero-beam',{opacity:0});
    gsap.set(tool,{x,y,rotation:-12,scale:small?.94:1.05,opacity:0,zIndex:85});
    gsap.set(poleNode,{x:innerWidth*.71-(poleBox.left+poleBox.width/2),y:innerHeight*.5-(poleBox.top+poleBox.height/2),scale:.67,opacity:0,zIndex:83});
    gsap.set('.headline-line',{yPercent:112,opacity:1});
    gsap.set(['.hero-kicker','.hero-detail','.hero-footer'],{opacity:0});
    closeScissors(tool,24);dust.setIntro(0);
    const front=tool.querySelector('.half-front'),back=tool.querySelector('.half-back');
    intro=gsap.timeline({paused:true,defaults:{ease:'ritual-premium'},onUpdate(){introClock=intro.time();dust.setIntro(introClock);},onComplete(){settleIntro('complete');}});
    for(const [label,time] of Object.entries({escuridao:0,luz:.12,marca:.38,simbolo:.76,antecipacao:1.06,gesto:1.28,impacto:1.49,abertura:1.66,hero:2.04,acomodacao:2.46,continuidade:2.94,fim:3.5}))intro.addLabel(label,time);
    intro.to('.hero-beam',{opacity:.58,duration:.5},'luz')
      .to('.intro-mark',{opacity:1,y:0,scale:1,duration:.62},'marca')
      .to('.intro-caption',{opacity:1,duration:.6},'marca+=.13')
      .to(poleNode,{opacity:.65,duration:.54},'simbolo')
      .to(tool,{opacity:1,duration:.26},'simbolo+=.16')
      .to(front,{rotation:-29,duration:.18,ease:'power2.inOut'},'antecipacao')
      .to(back,{rotation:29,duration:.18,ease:'power2.inOut'},'antecipacao')
      .to(front,{rotation:0,duration:.24,ease:'ritual-precision'},'gesto')
      .to(back,{rotation:0,duration:.24,ease:'ritual-precision'},'gesto')
      .to('.intro-seam',{opacity:.95,scaleY:1,duration:.09,ease:'power3.out'},'impacto')
      .to('.hero-beam',{opacity:.95,duration:.1,ease:'power3.out'},'impacto')
      .fromTo(tool.querySelector('.blade-glint'),{x:0},{x:330,duration:.35,ease:'power3.out',immediateRender:false},'impacto')
      .to('.hero-beam',{opacity:.2,duration:.65},'impacto+=.1')
      .to('.intro-panel-left',{xPercent:-55,duration:.4},'abertura')
      .to('.intro-panel-right',{xPercent:55,duration:.4},'abertura')
      .to('.intro-panel-left',{xPercent:-103,duration:.52,ease:'power3.out'},'abertura+=.4')
      .to('.intro-panel-right',{xPercent:103,duration:.52,ease:'power3.out'},'abertura+=.4')
      .to('.intro-mark',{opacity:0,scale:1.04,duration:.4},'abertura')
      .to('.intro-caption',{opacity:0,duration:.3},'abertura')
      .to('.intro-seam',{opacity:0,duration:.3},'abertura+=.14')
      .to('.headline-line',{yPercent:0,duration:.67,stagger:.1,ease:'power3.out'},'hero')
      .to('.hero-kicker',{opacity:1,duration:.45},'hero')
      .to('.hero-detail',{opacity:1,duration:.45},'hero+=.38')
      .to('.hero-footer',{opacity:1,duration:.45},'hero+=.4')
      .to(tool,{x:0,y:0,scale:1,rotation:-24,duration:.84},'acomodacao')
      .to(poleNode,{x:0,y:0,scale:1,opacity:1,duration:.84},'acomodacao')
      .to(front,{rotation:-7,duration:.45},'continuidade')
      .to(back,{rotation:7,duration:.45},'continuidade')
      .to({},{duration:.21},3.29);
    intro.timeScale(small?3.5/2.3:1);
    if(!manual){intro.play();watchdog=setTimeout(()=>settleIntro('watchdog'),4500);}
    return intro;
  }

  function readStage(progress) {
    const index=progress<.38?0:progress<.75?1:2;
    $('.ritual-progress span').style.transform=`scaleX(${progress})`;
    $('.stage-percent').textContent=String(Math.round(progress*100)).padStart(3,'0');
    if(index===lastStage)return;
    lastStage=index;$('.stage-index').textContent=`0${index+1}`;$('.stage-name').textContent=['PREPARO','TÉCNICA','ACABAMENTO'][index];
    $('.mirror-caption').textContent=`0${index+1} / ${['PREPARO','TÉCNICA','ACABAMENTO'][index]}`;
    root.dataset.ritualStage=String(index);
    for(const button of $$('[data-stage]')){if(Number(button.dataset.stage)===index)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');}
  }

  function setupMirrorRitual(desktop,reduced) {
    const stage=$('.ritual-stage'),mount=$('.mirror-stage'),tool=$('.ritual-tool'),chapters=$$('.ritual-chapter');
    root.classList.toggle('ritual-is-pinned',desktop&&!reduced);
    lastStage=-1;
    gsap.set('.precision-guides',{opacity:0});gsap.set('.precision-line',{x:i=>i%2?75:-70,rotation:i=>i%2?7:-6,transformOrigin:'center'});
    gsap.set('.mirror-fog',{opacity:.94,y:0});gsap.set('.mirror-sweep',{x:-100,opacity:.55});
    gsap.set('.result-contour',{strokeDasharray:1,strokeDashoffset:1,opacity:.8});
    gsap.set('.silhouette',{opacity:.28,scale:.98,svgOrigin:'400 550'});gsap.set('.rough-lines',{opacity:.8});
    gsap.set('.frame-glow',{opacity:.28});gsap.set(tool,{x:32,y:42,rotation:-32,scale:.8,opacity:.2});
    closeScissors(tool,22);
    if(desktop&&!reduced){gsap.set(chapters,{autoAlpha:0,y:24});gsap.set(chapters[0],{autoAlpha:1,y:0});}
    const timeline=gsap.timeline({paused:true,defaults:{ease:'none'},onUpdate(){readStage(timeline.progress());}});
    timeline.addLabel('preparo',0).addLabel('tecnica',1.14).addLabel('acabamento',2.25)
      .to('.mirror-fog',{y:-170,opacity:.55,duration:.9},0)
      .to('.silhouette',{opacity:.72,scale:1,duration:1},.05)
      .to('.mirror-sweep',{x:270,duration:.95},0)
      .to(tool,{x:0,y:0,scale:1,opacity:.95,rotation:-18,duration:.65},.65)
      .to('.precision-guides',{opacity:.65,duration:.24},.94)
      .to('.precision-line',{x:0,rotation:0,duration:.65},1.02)
      .to('.mirror-fog',{y:-320,opacity:.15,duration:.8},1.02)
      .to('.mirror-sweep',{x:540,opacity:.2,duration:.85},1.05)
      .to(tool.querySelector('.half-front'),{rotation:-28,svgOrigin:'300 300',duration:.2},1.28)
      .to(tool.querySelector('.half-back'),{rotation:28,svgOrigin:'300 300',duration:.2},1.28)
      .to(tool.querySelector('.half-front'),{rotation:0,duration:.29,ease:'power3.in'},1.51)
      .to(tool.querySelector('.half-back'),{rotation:0,duration:.29,ease:'power3.in'},1.51)
      .to(tool.querySelector('.blade-glint'),{x:350,duration:.25},1.76)
      .to('.rough-lines',{opacity:0,duration:.28},1.73)
      .to('.result-contour',{strokeDashoffset:0,duration:.54},1.8)
      .to('.precision-guides',{opacity:0,duration:.3},2.12)
      .to(tool,{x:65,y:90,rotation:-33,scale:.8,opacity:.25,duration:.55},2.2)
      .to('.mirror-fog',{opacity:0,duration:.45},2.15)
      .fromTo('.mirror-sweep',{x:80,opacity:.75},{x:940,duration:.65,immediateRender:false},2.26)
      .to('.frame-glow',{opacity:1,duration:.33},2.25)
      .to('.silhouette',{opacity:1,duration:.55},2.25)
      .to('.result-contour',{opacity:.35,duration:.35},2.65)
      .to({},{duration:.1},2.9);
    if(desktop&&!reduced){
      timeline.to(chapters[0],{autoAlpha:0,y:-20,duration:.16},1.02).fromTo(chapters[1],{autoAlpha:0,y:24},{autoAlpha:1,y:0,duration:.2,immediateRender:false},1.15)
        .to(chapters[1],{autoAlpha:0,y:-20,duration:.16},2.15).fromTo(chapters[2],{autoAlpha:0,y:24},{autoAlpha:1,y:0,duration:.2,immediateRender:false},2.28);
      ritualTrigger=ScrollTrigger.create({id:'lab-ritual',trigger:$('#ritual'),pin:stage,start:'top top',end:()=>`+=${Math.round(innerHeight*2.1)}`,animation:timeline,scrub:.55,invalidateOnRefresh:true});
    } else if(!reduced) {
      ritualTrigger=ScrollTrigger.create({id:'lab-ritual-mobile',trigger:mount,start:'top 85%',end:'bottom 15%',animation:timeline,scrub:.25});
    } else {
      timeline.progress(1);readStage(1);gsap.set(chapters,{clearProps:'opacity,visibility,transform'});gsap.set(tool,{opacity:.5});
    }
    ritualTimeline=timeline;
    return()=>{ritualTrigger?.kill();ritualTrigger=null;timeline.kill();ritualTimeline=null;root.classList.remove('ritual-is-pinned');};
  }

  function setupRitual(desktop,reduced){
    if(mirrorStudy)return setupMirrorRitual(desktop,reduced);
    const controller=createVideoRitual({gsap,ScrollTrigger,runtime,desktop,reduced,scheduleRefresh});
    videoRitual=controller;ritualTimeline=controller.timeline;ritualTrigger=controller.trigger;
    return()=>{controller.destroy();lastVideoSnapshot=controller.snapshot();if(videoRitual===controller)videoRitual=null;ritualTimeline=null;ritualTrigger=null;};
  }

  function scheduleRefresh(){clearTimeout(refreshTimer);refreshTimer=setTimeout(()=>{if(!destroyed&&ScrollTrigger.getAll().length)ScrollTrigger.refresh();},120);}
  mm.add({screen:'(min-width: 0px)',desktop:'(min-width: 1000px) and (min-height: 650px)',reduced:'(prefers-reduced-motion: reduce)',fine:'(hover: hover) and (pointer: fine)'},context=>{
    const {desktop,reduced,fine}=context.conditions;
    if(introActive)settleIntro('resize');
    root.classList.toggle('motion-reduced',reduced);runtime.setReduced(reduced);
    dust.resize();
    if(reduced)dust.clear();
    const cleanupRitual=setupRitual(desktop,reduced);
    const pointerOff=[],pointerTweens=[];
    if(!reduced){
      gsap.fromTo('.interlude-track span',{xPercent:-40},{xPercent:220,ease:'none',scrollTrigger:{trigger:'.chapter-interlude',start:'top bottom',end:'bottom top',scrub:.5}});
      gsap.fromTo('.finale-reflection',{xPercent:-30},{xPercent:240,ease:'none',scrollTrigger:{trigger:'.finale',start:'top bottom',end:'bottom top',scrub:.6}});
      gsap.fromTo('.finale-ring',{scale:.82},{scale:1.05,ease:'none',scrollTrigger:{trigger:'.finale',start:'top bottom',end:'bottom top',scrub:.6}});
      gsap.fromTo('.finale-line',{yPercent:105},{yPercent:0,stagger:.09,duration:.85,ease:'power3.out',scrollTrigger:{trigger:'.finale',start:'top 65%',toggleActions:'play none none reverse'}});
      if(fine){
        const xTo=gsap.quickTo('.hero-light','x',{duration:.65,ease:'power3.out'}),yTo=gsap.quickTo('.hero-light','y',{duration:.65,ease:'power3.out'});
        const roomTo=gsap.quickTo('.room-portal','x',{duration:.8,ease:'power3.out'});
        for(const tween of [xTo.tween,yTo.tween,roomTo.tween]){ownTweens.add(tween);pointerTweens.push(tween);}
        pointerOff.push(runtime.listen(hero,'pointermove',event=>{if(runtime.paused||introActive)return;const b=hero.getBoundingClientRect();const x=gsap.utils.clamp(-1,1,(event.clientX-b.left)/b.width*2-1),y=gsap.utils.clamp(-1,1,(event.clientY-b.top)/b.height*2-1);xTo(x*12);yTo(y*9);roomTo(-x*5);},{passive:true}));
        pointerOff.push(runtime.listen(hero,'pointerleave',()=>{xTo(0);yTo(0);roomTo(0);}));
      }
    }
    scheduleRefresh();
    return()=>{pointerOff.forEach(off=>off());pointerTweens.forEach(tween=>{tween.kill();ownTweens.delete(tween);});cleanupRitual();};
  });

  async function loadThree(force=false){
    if(destroyed||loading3D||(!force&&failed3D)||(!force&&scene3D))return;
    loading3D=true;$('#three-status').textContent='Preparando luz e metal…';
    try {
      scene3D?.destroy();scene3D=null;
      if(force){const oldCanvas=$('#pole-canvas');oldCanvas.replaceWith(oldCanvas.cloneNode(false));}
      if(new URLSearchParams(location.search).has('no3d'))throw new Error('Fallback solicitado pelo laboratório');
      const {createPoleStudy}=await import('./pole-three.mjs');
      const study=await createPoleStudy($('#pole-canvas'),runtime);
      if(destroyed){study.destroy();return;}
      scene3D=study;failed3D=false;$('#three-retry').hidden=true;
    }catch(error){failed3D=true;$('#three-status').textContent='3D indisponível — representação SVG ativa.';$('#three-retry').hidden=false;}
    finally{loading3D=false;}
  }
  runtime.watch($('.pole-three'),visible=>{threeVisibility=visible;if(visible)loadThree();});
  runtime.listen($('#three-retry'),'click',()=>loadThree(true));
  runtime.listen($('#replay'),'click',()=>{if(runtime.paused){runtime.setPaused(false);$('#pause').setAttribute('aria-pressed','false');$('#pause').textContent='PAUSAR AMBIENTE';}buildIntro();});
  runtime.listen($('#skip-intro'),'click',()=>settleIntro('skip'));
  runtime.listen(document,'keydown',event=>{if(!introActive)return;if(event.key==='Escape')settleIntro('escape');else if(event.key==='Tab')settleIntro('keyboard');});
  runtime.listen(window,'wheel',()=>{if(introActive)settleIntro('scroll');},{passive:true});
  runtime.listen(window,'touchstart',()=>{if(introActive)settleIntro('touch');},{passive:true});
  runtime.listen(document,'click',event=>{if(introActive&&event.target.closest('a'))settleIntro('navigate');});
  runtime.listen(document,'visibilitychange',()=>{if(document.hidden&&introActive)settleIntro('hidden');});
  runtime.listen($('#pause'),'click',()=>{const next=!runtime.paused;runtime.setPaused(next);$('#pause').setAttribute('aria-pressed',String(next));$('#pause').textContent=next?'RETOMAR AMBIENTE':'PAUSAR AMBIENTE';if(introActive){if(next){intro.pause();clearTimeout(watchdog);}else{intro.play();watchdog=setTimeout(()=>settleIntro('watchdog'),4500);}}});
  runtime.listen($('#metrics-toggle'),'click',()=>{const open=$('#metrics').hidden;$('#metrics').hidden=!open;$('#metrics-toggle').setAttribute('aria-expanded',String(open));updateMetrics();});
  runtime.listen(document,'click',event=>{
    const button=event.target.closest('[data-stage]');if(!button)return;
    if(videoRitual){videoRitual.goStage(Number(button.dataset.stage));return;}
    const index=Number(button.dataset.stage),progress=[.16,.57,.94][index];
    if(ritualTrigger?.pin){window.scrollTo({top:ritualTrigger.start+(ritualTrigger.end-ritualTrigger.start)*progress,behavior:'instant'});}
    else {$$('.ritual-chapter')[index].scrollIntoView({block:'center',behavior:'instant'});if(!reducedMQ.matches)ritualTimeline?.progress(progress);}
  });
  function snapshot(){
    const resources=performance.getEntriesByType('resource').filter(r=>r.name.startsWith(location.origin));
    return {...runtime.snapshot(),scrollTriggers:ScrollTrigger.getAll().length,activeCanvases:(runtime.snapshot().activeTasks.some(n=>n.includes('Canvas'))?1:0)+(runtime.snapshot().activeTasks.some(n=>n.includes('Three'))?1:0),resourceBytes:resources.reduce((sum,r)=>sum+(r.decodedBodySize||0),0),resourceCount:resources.length,three:scene3D?scene3D.stats():null,threeVisible:threeVisibility,introActive,introTime:introClock,introDuration:intro?intro.duration()/intro.timeScale():0,ritualProgress:ritualTimeline?.progress()??1,ritualStage:root.dataset.ritualStage,ritualVideo:videoRitual?.snapshot()??lastVideoSnapshot};
  }
  function updateMetrics(){
    const m=snapshot();
    const v=m.ritualVideo;
    $('#metrics-text').textContent=[`RAF lab          ${m.continuousRAFLoops} compartilhado`,`RAF totais       ${m.scheduledRAF} pendentes`,`Callbacks        ${m.rafCallbacks.join(', ')||'nenhum'}`,`Consumidores     ${m.activeTasks.length}`,`Canvas ativos    ${m.activeCanvases} / ${m.canvases}`,`WebGL contexts   ${m.webglContexts}`,`Partículas pool  ${m.particles}`,`ScrollTriggers   ${m.scrollTriggers}`,`Listeners lab    ${m.listeners}`,`Subrecursos raw  ${(m.resourceBytes/1024).toFixed(1)} KiB / ${m.resourceCount}`,`Estado           ${m.disposed?'desmontado':m.reduced?'reduzido':m.paused?'pausado':'ativo'}`,...(v?[`Vídeo            ${v.mode}`,`VP9 / 720p / 24  ${(v.webmBytes/1048576).toFixed(2)} MiB`,`GOP              ${v.gopFrames} frames / 250ms`,`Metadata         ${v.metadataMs??'—'} ms`,`Seek p50 / p95   ${v.seekMedianMs??'—'} / ${v.seekP95Ms??'—'} ms`,`Tempo / alvo     ${v.presentedTime.toFixed(2)} / ${v.desiredTime.toFixed(2)} s`,`Seeks / fila     ${v.completed} / ${v.inFlight?1:0}`,`RAF extra vídeo  ${v.additionalRAFLoops}`]:[]),...m.activeTasks.map(name=>` · ${name}`)].join('\n');
  }
  function destroy(){
    if(destroyed)return;
    settleIntro('destroy');destroyed=true;intro?.kill();clearTimeout(watchdog);clearTimeout(refreshTimer);clearInterval(metricsTimer);
    mm.revert();for(const tween of ownTweens)tween.kill();scene3D?.destroy();scene3D=null;dust.destroy();runtime.destroy();
    root.classList.remove('ritual-is-pinned');root.classList.add('motion-reduced');
    gsap.set(['.headline-line','.finale-line','.ritual-chapter'],{clearProps:'all'});gsap.set('.hero-tool',{zIndex:4});
    if(mirrorStudy){gsap.set('.mirror-fog',{opacity:0});gsap.set('.precision-guides',{opacity:0});}
    ScrollTrigger.disable();gsap.ticker.sleep();
    $('#replay').disabled=true;$('#pause').disabled=true;$('#destroy').disabled=true;
    updateMetrics();
  }
  runtime.listen($('#destroy'),'click',destroy);
  runtime.listen(window,'pagehide',event=>{if(event.persisted){runtime.setPaused(true);if(introActive)settleIntro('hidden');}else destroy();});
  runtime.listen(window,'pageshow',event=>{if(event.persisted){runtime.setPaused($('#pause').getAttribute('aria-pressed')==='true');scheduleRefresh();}});
  metricsTimer=setInterval(()=>{if(!document.hidden&&!$('#metrics').hidden)updateMetrics();},750);
  document.fonts?.ready.then(scheduleRefresh);
  window.motionLab={snapshot,replay:()=>buildIntro(),skip:()=>settleIntro('skip'),seekIntro(time){const tl=buildIntro(true);tl?.time(time,false).pause();return snapshot();},seekRitual(progress){if(videoRitual){videoRitual.seekProgress(progress);return;}if(ritualTrigger?.pin){window.scrollTo({top:ritualTrigger.start+(ritualTrigger.end-ritualTrigger.start)*progress,behavior:'instant'});}else ritualTimeline?.progress(progress);},destroy,get intro(){return intro;},get ritual(){return ritualTimeline;}};
  root.dataset.labReady='true';
  if(!seen&&!location.hash&&!reducedMQ.matches&&!new URLSearchParams(location.search).has('nointro'))buildIntro();else settleIntro('bypass');
  updateMetrics();
}

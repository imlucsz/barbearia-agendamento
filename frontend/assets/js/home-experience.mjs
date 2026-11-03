import {scissors,pole} from './home-motion/assets.mjs';
import {createRuntime} from './home-motion/runtime.mjs';
import {createDust} from './home-motion/particles.mjs';
import {createVideoRitual} from './home-motion/ritual-video.mjs';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
async function start(){
 const load=name=>new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=new URL('./vendor/gsap/'+name,import.meta.url);script.onload=resolve;script.onerror=reject;document.head.append(script)});await load('gsap.min.js');await load('ScrollTrigger.min.js');await load('CustomEase.min.js');
 const {gsap,ScrollTrigger,CustomEase}=window;gsap.registerPlugin(ScrollTrigger,CustomEase);
 CustomEase.create('ritual-precision','M0,0 C0.48,0 0.66,0.08 0.74,0.54 0.82,0.94 0.89,1 1,1');CustomEase.create('ritual-premium','.4,0,.2,1');
 $('.hero-tool').innerHTML=scissors('home-tool');$('[data-home-pole]').innerHTML=pole('home-pole');
 $('.intro-mark strong').textContent=$('.brand-copy strong').textContent;
 const root=document.documentElement,runtime=createRuntime(gsap),hero=$('.hero'),dust=createDust($('#dust'),hero,runtime);
 const reducedMQ=matchMedia('(prefers-reduced-motion: reduce)'),mobileMQ=matchMedia('(max-width:767px)');
 const sessionKey='barbearia.home.intro.v1';let seen=false;try{seen=sessionStorage.getItem(sessionKey)==='seen'}catch{}
 let intro=null,introActive=false,introClock=4,watchdog=0,destroyed=false,refreshTimer=0,controller=null;
 function scheduleRefresh(){if(destroyed)return;clearTimeout(refreshTimer);refreshTimer=setTimeout(()=>{if(!destroyed)ScrollTrigger.refresh()},120)}
  function closeScissors(host,angle) {
    gsap.set(host.querySelector('.half-front'),{rotation:-angle,svgOrigin:'300 300'});
    gsap.set(host.querySelector('.half-back'),{rotation:angle,svgOrigin:'300 300'});
  }
  closeScissors($('.hero-tool'),7);

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


 const mm=gsap.matchMedia();
 mm.add({desktop:'(min-width:1000px) and (min-height:650px)',reduced:'(prefers-reduced-motion:reduce)',all:'(min-width:0px)'},ctx=>{
  runtime.setReduced(ctx.conditions.reduced);root.classList.toggle('experience-ready',!ctx.conditions.reduced);dust.resize();
  if(ctx.conditions.reduced){settleIntro('reduced');dust.clear()}
  controller=createVideoRitual({gsap,ScrollTrigger,runtime,...ctx.conditions,scheduleRefresh});
  if(!ctx.conditions.reduced){for(const node of $$('.section-heading,.step-card,.location-copy,.final-booking'))gsap.fromTo(node,{y:14},{y:0,duration:.65,ease:'power3.out',scrollTrigger:{trigger:node,start:'top 92%',toggleActions:'play none none reverse'}})}
  return()=>{controller?.destroy()};
 });
 const offs=[runtime.listen($('#skip-intro'),'click',()=>settleIntro('skip')),runtime.listen(document,'keydown',e=>{if(introActive&&(e.key==='Escape'||e.key==='Tab'))settleIntro(e.key==='Escape'?'escape':'tab')}),runtime.listen(window,'resize',()=>{if(introActive)settleIntro('resize')}),runtime.listen(document,'visibilitychange',()=>{if(document.hidden&&introActive)settleIntro('hidden')})];
 for(const button of $$('#ritual [data-stage]'))offs.push(runtime.listen(button,'click',()=>controller?.goStage(Number(button.dataset.stage))));
 if(!seen&&!reducedMQ.matches&&!location.hash)buildIntro();else settleIntro('seen');
 const destroy=()=>{if(destroyed)return;settleIntro('destroy');destroyed=true;layoutObserver?.disconnect();clearTimeout(watchdog);clearTimeout(refreshTimer);intro?.kill();mm.revert();dust.destroy();offs.forEach(off=>off());runtime.destroy()};
 const layoutObserver=globalThis.ResizeObserver?new ResizeObserver(scheduleRefresh):null;
 for(const node of $$('#services,#business-info,#reviews'))layoutObserver?.observe(node);
 window.homeExperience={destroy,snapshot:()=>({...runtime.snapshot(),scrollTriggers:ScrollTrigger.getAll().length,ritualVideo:controller?.snapshot()})};
 window.addEventListener('pagehide',()=>{layoutObserver?.disconnect();destroy()},{once:true});document.fonts.ready.then(scheduleRefresh);
}
start().catch(()=>{document.querySelector('.intro-shell').hidden=true;document.querySelector('#skip-intro').hidden=true;document.documentElement.classList.remove('experience-ready')});

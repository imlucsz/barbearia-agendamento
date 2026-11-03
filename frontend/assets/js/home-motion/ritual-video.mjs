import { createVideoSeeker } from './video-seek.mjs';

export const RITUAL_CUTS=[0,2.5,7.75,10];
export const RITUAL_STILLS=[1.25,5.25,9.25];
const NAMES=['PREPARO','TÉCNICA','ACABAMENTO'];
const handoffs=new WeakMap();
export function createVideoRitual({gsap,ScrollTrigger,runtime,desktop,reduced,scheduleRefresh}) {
  const root=document.documentElement,section=document.querySelector('#ritual'),stage=section.querySelector('.ritual-stage');
  const video=section.querySelector('video'),chapters=[...section.querySelectorAll('.ritual-chapter')],buttons=[...section.querySelectorAll('[data-stage]')];
  const previousView=handoffs.get(section);handoffs.delete(section);
  const offs=[];let closed=false,failed=false,trigger=null,lastStage=-1,desiredProgress=0,duration=10,nearObserver=null,visibilityObserver=null;
  let fallbackReason=null,textTransition=null;
  root.classList.toggle('ritual-is-pinned',desktop&&!reduced);
  section.classList.toggle('ritual-mobile',!desktop&&!reduced);
  section.classList.toggle('ritual-static',reduced);
  const timeline=gsap.timeline({paused:true,defaults:{ease:'none'}});
  function nativeScrollTo(top){ScrollTrigger.getScrollFunc(window)(Math.round(top));ScrollTrigger.update();}
  function readTime(time) {
    if(closed)return;
    const index=time<RITUAL_CUTS[1]?0:time<RITUAL_CUTS[2]?1:2;
    root.dataset.ritualStage=String(index);
    section.querySelector('.stage-percent').textContent=String(Math.round(time/duration*100)).padStart(3,'0');
    if(index!==lastStage){
      const previous=lastStage;lastStage=index;
      if(!reduced&&!failed&&previous>=0){
        textTransition?.kill();gsap.killTweensOf(chapters);
        chapters.forEach((node,i)=>{if(i!==index&&i!==previous)gsap.set(node,{autoAlpha:0,y:0,clipPath:'inset(0%)'});});
        textTransition=gsap.timeline({defaults:{ease:'power3.out'}})
          .to(chapters[previous],{autoAlpha:0,y:-16,duration:.2,ease:'power2.in'},0)
          .fromTo(chapters[index],{autoAlpha:0,y:18,clipPath:'inset(0%)'},{autoAlpha:1,y:0,duration:.28,immediateRender:false},.12);
      }
      section.querySelector('.stage-index').textContent=`0${index+1}`;section.querySelector('.stage-name').textContent=NAMES[index];section.querySelector('.video-stage-caption').textContent=`0${index+1} / ${NAMES[index]}`;
      buttons.forEach((button,i)=>{if(i===index)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');});}
  }
  function showFallback(reason) {
    if(closed||failed)return;failed=true;fallbackReason=reason;
    const keepChapter=seeker.snapshot().visible,chapter=Math.max(0,lastStage);
    section.classList.add('video-error');section.classList.remove('ritual-mobile');root.classList.remove('ritual-is-pinned');
    trigger?.kill(true);trigger=null;timeline.pause();textTransition?.kill();gsap.killTweensOf(chapters);
    gsap.set(chapters,{clearProps:'opacity,visibility,transform,clip-path'});
    section.querySelector('.ritual-film').classList.remove('has-video-frame');
    if(keepChapter)queueMicrotask(()=>{if(!closed){chapters[chapter].scrollIntoView({block:'center',behavior:'instant'});nativeScrollTo(window.scrollY);}});
    scheduleRefresh();
  }
  const seeker=createVideoSeeker(video,{runtime,source:new URL('../../media/home/ritual-scrub.webm',import.meta.url).href,
    onMetadata(value){duration=value;scheduleRefresh();},
    onFrame(time){section.querySelector('.ritual-film').classList.add('has-video-frame');readTime(time);},
    onFailure:showFallback});

  if(!reduced){
    gsap.set(chapters,{autoAlpha:0,y:20,clipPath:'inset(0%)'});gsap.set(chapters[0],{autoAlpha:1,y:0});
    timeline.addLabel('preparo',0).addLabel('tecnica',2.5).addLabel('acabamento',7.75)
      .fromTo('.ritual-video .ritual-film',{clipPath:desktop?'inset(2% 2% 2% 2% round 2px)':'inset(3% 3% 3% 3% round 2px)'},{clipPath:desktop?'inset(0.5% 0.5% 0.5% 0.5% round 1px)':'inset(1% 0% 1% 0% round 1px)',duration:5.3},0)
      .fromTo('.ritual-video .film-content',{scale:1.015,xPercent:0},{scale:1.005,xPercent:0,duration:5.3},0)
      .to('.ritual-video .ritual-film',{clipPath:'inset(0% 0% 0% 0% round 0px)',duration:2.25},7.75)
      .to('.ritual-video .film-content',{scale:1,duration:2.25},7.75)
      .fromTo('.ritual-video .film-gold-reflection',{xPercent:-100,opacity:.015},{xPercent:170,opacity:.035,duration:10},0)
      .fromTo('.ritual-video .ritual-progress span',{scaleX:0},{scaleX:1,duration:10},0);
    const synchronize=()=>{
      if(closed||failed)return;
      desiredProgress=timeline.progress();
      // Responsive layout affects pin/crop, never the video's time semantics.
      seeker.seekProgress(desiredProgress);
    };
    timeline.eventCallback('onUpdate',synchronize);
    trigger=ScrollTrigger.create({id:desktop?'lab-ritual':'lab-ritual-mobile',trigger:section,
      ...(desktop?{pin:stage,start:'top top',end:()=>`+=${Math.round(innerHeight*2.1)}`,scrub:.16,invalidateOnRefresh:true}:{start:'top top',end:'bottom bottom',scrub:true}),animation:timeline,
      // Refresh temporarily renders progress 0, then restores with callbacks suppressed.
      // Read the restored playhead after that transaction, including late metadata.
      onRefresh:()=>queueMicrotask(synchronize)});
    if(globalThis.IntersectionObserver){
      nearObserver=new IntersectionObserver(entries=>{if(entries[0].isIntersecting)seeker.prepare();},{rootMargin:'500px 0px'});nearObserver.observe(section);
      visibilityObserver=new IntersectionObserver(entries=>seeker.setVisible(entries[0].isIntersecting),{threshold:0});visibilityObserver.observe(section);
    }else{seeker.setVisible(true);}
  }else{
    gsap.set(chapters,{clearProps:'opacity,visibility,transform,clip-path'});readTime(9.25);
  }
  readTime(reduced?9.25:0);
  // matchMedia reverts pins before rebuilding. Keep the visitor in this chapter
  // instead of allowing the temporary collapsed layout to send them to the hero.
  if(previousView?.visible)queueMicrotask(()=>{
    if(closed)return;
    if(reduced){const i=previousView.progress<.25?0:previousView.progress<.775?1:2;chapters[i].scrollIntoView({block:'center',behavior:'instant'});nativeScrollTo(window.scrollY);}
    else if(trigger)nativeScrollTo(trigger.start+(trigger.end-trigger.start)*previousView.progress);
  });
  return {
    timeline,get trigger(){return trigger;},
    goStage(index){
      if(reduced||failed){chapters[index].scrollIntoView({block:'center',behavior:'instant'});return;}
      const progress=RITUAL_STILLS[index]/duration;
      if(trigger)nativeScrollTo(trigger.start+(trigger.end-trigger.start)*progress);
    },
    seekProgress(progress){if(trigger)nativeScrollTo(trigger.start+(trigger.end-trigger.start)*progress);else timeline.progress(progress);},
    snapshot(){return {...seeker.snapshot(),mode:reduced?'poster':'continuous-scrub',handoff:previousView??null,failureReason:fallbackReason,sourceWidth:1280,sourceHeight:720,decodedWidth:video.videoWidth,decodedHeight:video.videoHeight,fps:24,codec:'VP9',webmBytes:1707525,gopFrames:6,desiredScrollProgress:desiredProgress,additionalCanvas:0,additionalWebGL:0};},
    destroy(){if(closed)return;const bounds=section.getBoundingClientRect(),media=seeker.snapshot();handoffs.set(section,{progress:reduced?(previousView?.progress??.925):(media.duration?media.presentedTime/media.duration:desiredProgress),visible:media.visible||(reduced&&bounds.top<innerHeight&&bounds.bottom>0)});closed=true;nearObserver?.disconnect();visibilityObserver?.disconnect();offs.forEach(off=>off());seeker.destroy();trigger?.kill(true);timeline.kill();textTransition?.kill();gsap.killTweensOf(chapters);root.classList.remove('ritual-is-pinned');section.classList.remove('ritual-mobile','video-error');section.classList.add('ritual-static');}
  };
}

import assert from 'node:assert/strict';
import { readFile,writeFile,mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { createLabServer } from './server.mjs';
import { progressToTime } from './video-seek.mjs';

const lab=new URL('./',import.meta.url),artifacts=new URL('./artifacts/video-validation/',lab);
await mkdir(artifacts,{recursive:true});
const server=createLabServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`,base=origin+'/frontend/e2e/motion-lab/';
const report={passed:[],measurements:{},consoleErrors:[],externalRequests:[],generatedAt:new Date().toISOString()};
let browser;
const sha=data=>createHash('sha256').update(typeof data==='string'?data.replace(/\r\n/g,'\n'):data).digest('hex');
const state=page=>page.evaluate(()=>motionLab.snapshot());
async function ready(page,suffix='?nointro=1'){await page.goto(base+suffix,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.motionLab);}
async function snapshot(page,name){await page.evaluate(()=>document.activeElement?.blur());await page.screenshot({path:fileURLToPath(new URL(name+'.png',artifacts))});}
async function check(name,fn){await fn();report.passed.push(name);console.log('PASS '+name);}
function monitor(page){page.on('pageerror',error=>report.consoleErrors.push(error.message));page.on('console',message=>{if(message.type()==='error')report.consoleErrors.push(message.text());});page.on('request',request=>{if(!request.url().startsWith(origin)&&!request.url().startsWith('data:'))report.externalRequests.push(request.url());if(/\/services\/|\/informacoes\/|\/appointments|\/auth\//.test(request.url()))report.externalRequests.push(request.url());});}
async function seek(page,progress,expectedTime){
  await page.evaluate(p=>motionLab.seekRitual(p),progress);
  // Loading and seek convergence are distinct phases. The feature's existing
  // metadata watchdog remains authoritative; an event alone is not readiness.
  await page.waitForFunction(()=>{const v=motionLab.snapshot().ritualVideo;return v?.failed||(v?.readyState>=1&&Number.isFinite(v.duration));},null,{polling:100});
  assert.equal((await state(page)).ritualVideo.failed,false,'media failed before seek');
  try{await page.waitForFunction(({p,time})=>{const m=motionLab.snapshot(),v=m.ritualVideo;return v&&!v.failed&&!v.inFlight&&!v.seeking&&Math.abs(v.currentTime-time)<.07&&Math.abs(m.ritualProgress-p)<.008;},{p:progress,time:expectedTime},{timeout:6000});}
  catch(error){report.measurements.failure=await page.evaluate(()=>({m:motionLab.snapshot(),scrollY,viewport:[innerWidth,innerHeight],start:motionLab.ritual?.scrollTrigger?.start,end:motionLab.ritual?.scrollTrigger?.end}));console.log('Seek diagnostic',JSON.stringify(report.measurements.failure));await snapshot(page,'failure');throw error;}
}
try{
  await check('master intacto, asset VP9 720p/24 sem áudio e GOP 6 verificado',async()=>{
    const meta=JSON.parse(await readFile(new URL('./assets/ritual-media.json',lab),'utf8'));
    const master=await readFile(new URL('./'+meta.master.filename,lab));
    assert.equal(sha(master),'8909ffa1632aa666c351a31d7efc2b7bc5637497315eb721e35f4c0041b3d0f6');assert.equal(master.length,2694499);
    assert.equal(meta.webm.codec,'vp9');assert.equal(meta.webm.audio,false);assert.equal(meta.webm.frameCount,240);assert.equal(meta.webm.keyframeTimes.length,40);assert.equal(meta.webm.bytes,1707525);
    assert(meta.webm.keyframeTimes.every((t,i)=>Math.abs(t-i*.25)<.001));report.media=meta;
    assert.equal(progressToTime(1,10),239/24);assert.equal(progressToTime(-1,10),0);assert.equal(progressToTime(.5,NaN),0);
  });
  await check('hero, intro, CTA e arte original preservados por hash',async()=>{
    const before=JSON.parse(await readFile(new URL('./video-protected.json',lab),'utf8'));
    const html=await readFile(new URL('./index.html',lab),'utf8'),main=await readFile(new URL('./main.mjs',lab),'utf8');
    const section=name=>html.split(`<section class="${name}"`)[1].split('</section>')[0];
    const current={hero:sha(section('hero')),finale:sha(section('finale')),intro:sha(html.split('<div class="intro-shell')[1].split('<aside class="lab-dock')[0]),'lab.css':sha(await readFile(new URL('./lab.css',lab),'utf8')),'assets.mjs':sha(await readFile(new URL('./assets.mjs',lab),'utf8')),buildIntro:sha(main.slice(main.indexOf('  function buildIntro('),main.indexOf('  function readStage(')))};
    assert.deepEqual(current,before);
  });
  await check('servidor fornece MIME, HEAD, Range 206, suffix e erro 416 corretos',async()=>{
    const media=base+'assets/ritual-scrub.webm';const head=await fetch(media,{method:'HEAD'});
    assert.equal(head.headers.get('content-type'),'video/webm');assert.equal(Number(head.headers.get('content-length')),1707525);assert.equal(head.headers.get('accept-ranges'),'bytes');
    const response=await fetch(media,{headers:{Range:'bytes=16-127'}});assert.equal(response.status,206);assert.equal(response.headers.get('content-range'),'bytes 16-127/1707525');assert.equal((await response.arrayBuffer()).byteLength,112);
    const suffix=await fetch(media,{headers:{Range:'bytes=-64'}});assert.equal(suffix.status,206);assert.equal((await suffix.arrayBuffer()).byteLength,64);
    const invalid=await fetch(media,{headers:{Range:'bytes=9999999-'}});assert.equal(invalid.status,416);
  });
  browser=await chromium.launch({headless:true,channel:'chrome',args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader']});
  const desktop=await browser.newContext({viewport:{width:1440,height:960},deviceScaleFactor:1});const page=await desktop.newPage();monitor(page);
  await ready(page);
  await check('desktop: metadata real, um pin e seção de aproximadamente 310vh',async()=>{
    await seek(page,.125,1.25);await page.waitForTimeout(400);
    const m=await state(page);assert.equal(m.ritualVideo.mode,'continuous-scrub');assert.equal(m.ritualVideo.duration,10);assert.equal(m.ritualVideo.decodedWidth,1280);assert.equal(m.ritualVideo.decodedHeight,720);assert.equal(m.ritualVideo.paused,true);assert.equal(m.scrollTriggers,5);assert.equal(await page.locator('.pin-spacer').count(),1);
    const ratio=await page.locator('#ritual').evaluate(n=>n.getBoundingClientRect().height/innerHeight);assert(ratio>=2.8&&ratio<=3.4);
    report.measurements.firstAccess=m;await snapshot(page,'preparo');
  });
  await check('texto HTML acompanha os eventos de 2.5s e 7.75s; máscara se expande',async()=>{
    const masks=[];
    for(const [name,p,time,index] of [['preparo',.125,1.25,'0'],['tecnica',.525,5.25,'1'],['acabamento',.925,9.25,'2']]){
      await seek(page,p,time);
      // A completed seek precedes rVFC publication and the HTML text transition.
      await page.waitForFunction(i=>motionLab.snapshot().ritualStage===i,index,{polling:100});
      await page.locator(`[data-chapter="${index}"]`).waitFor({state:'visible'});
      const m=await state(page);assert.equal(m.ritualStage,index);
      masks.push(await page.locator('.ritual-film').evaluate(n=>getComputedStyle(n).clipPath));report.measurements[name]=m;await snapshot(page,name);
    }
    assert.notEqual(masks[0],masks[1]);assert.notEqual(masks[1],masks[2]);report.masks=masks;
  });
  await check('parar na troca não deixa texto apagado; fim clampa no último frame',async()=>{
    await seek(page,.25,2.5);await page.waitForTimeout(450);assert.equal((await state(page)).ritualStage,'1');assert(Number(await page.locator('[data-chapter="1"]').evaluate(n=>getComputedStyle(n).opacity))>.99);
    await seek(page,.775,7.75);await page.waitForTimeout(450);assert.equal((await state(page)).ritualStage,'2');
    await seek(page,1,239/24);assert.equal((await state(page)).ritualVideo.failed,false);
  });
  await check('scroll lento, rápido, reverso e parada convergem para o último destino',async()=>{
    for(const p of [.12,.18,.24,.31,.38,.45,.52,.6,.7,.82,.94,.8,.6,.4,.2,.1]){await page.evaluate(p=>motionLab.seekRitual(p),p);await page.waitForTimeout(45);}
    await seek(page,.1,1);assert.equal((await state(page)).ritualStage,'0');
    await page.evaluate(async()=>{for(const p of [.9,.1,.8,.2,.99,.3,.7,.4,.88]){motionLab.seekRitual(p);await new Promise(resolve=>setTimeout(resolve,8));}});
    await seek(page,.88,8.7916666667);const m=await state(page);assert.equal(m.ritualStage,'2');assert(m.ritualVideo.seeks>10);assert.equal(m.ritualVideo.additionalRAFLoops,0);assert.equal(m.ritualVideo.additionalCanvas,0);assert.equal(m.ritualVideo.additionalWebGL,0);report.measurements.stress=m;
  });
  await check('offscreen para novas buscas; voltar por baixo retoma o destino correto',async()=>{
    await page.locator('#finale').scrollIntoViewIfNeeded();await page.waitForTimeout(600);const before=(await state(page)).ritualVideo.seeks;await page.waitForTimeout(400);
    const m=await state(page);assert.equal(m.ritualVideo.visible,false);assert.equal(m.ritualVideo.seeks,before);assert.equal(m.ritualVideo.pendingFrameCallbacks,0);assert.equal(m.activeCanvases,0);
    await seek(page,.525,5.25);assert.equal((await state(page)).ritualStage,'1');
  });
  await check('resize não duplica listeners/pin; reduced-motion remove vídeo ativo',async()=>{
    const baseline=(await state(page)).listeners;await page.setViewportSize({width:1200,height:900});await page.waitForTimeout(350);await seek(page,.45,4.5);assert.equal((await state(page)).listeners,baseline);assert.equal(await page.locator('.pin-spacer').count(),1);
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.waitForFunction(()=>motionLab.snapshot().reduced&&motionLab.snapshot().scrollTriggers===0,null,{polling:100});const m=await state(page);
    assert.equal(m.scrollTriggers,0);assert.equal(m.ritualVideo.attached,false);assert.equal(m.ritualVideo.mode,'poster');assert.equal(m.activeCanvases,0);assert.equal(await page.locator('video').getAttribute('src'),null);assert.equal(await page.locator('.pin-spacer').count(),0);
    assert(await page.locator('#ritual').evaluate(n=>{const b=n.getBoundingClientRect();return b.top<innerHeight&&b.bottom>0;}));
    for(const chapter of await page.locator('.ritual-chapter').all())assert(await chapter.isVisible());await page.locator('#ritual').scrollIntoViewIfNeeded();await snapshot(page,'reduced');
    await page.emulateMedia({reducedMotion:'no-preference'});await page.waitForFunction(()=>motionLab.snapshot().ritualVideo.mode==='continuous-scrub');await seek(page,.525,5.25);
  });
  await check('cleanup cancela mídia, callbacks, triggers e listeners',async()=>{
    const frames=await page.evaluate(async()=>{
      motionLab.destroy();const samples=[motionLab.snapshot()];
      // ScrollTrigger.disable() stops rescheduling _rafBugFix, but cannot cancel
      // its already queued frame. Drain actual frame boundaries, not wall time.
      for(let i=0;i<2;i++){await new Promise(resolve=>requestAnimationFrame(resolve));samples.push(motionLab.snapshot());}
      return samples;
    });
    const m=frames[2];report.measurements.cleanupFrames=frames;
    assert.equal(m.listeners,0);assert.equal(m.scrollTriggers,0);assert.equal(m.scheduledRAF,0);assert.equal(m.ritualVideo.closed,true);assert.equal(m.ritualVideo.pendingFrameCallbacks,0);assert.equal(await page.locator('video').getAttribute('src'),null);report.measurements.cleanup=m;
  });await desktop.close();

  await check('entrada no meio antes de metadata conserva apenas o destino mais recente',async()=>{
    const context=await browser.newContext({viewport:{width:1440,height:960}});const p=await context.newPage();monitor(p);
    let release;const pending=new Promise(resolve=>{release=resolve;});await p.route('**/assets/ritual-scrub.webm',async route=>{await pending;await route.continue();});
    await ready(p);await p.evaluate(()=>motionLab.seekRitual(.3));await p.waitForTimeout(100);await p.evaluate(()=>motionLab.seekRitual(.67));await p.waitForTimeout(150);
    const before=await state(p);assert.equal(before.ritualVideo.readyState,0);assert.equal(before.ritualVideo.seeks,0);release();
    await p.waitForFunction(()=>{const v=motionLab.snapshot().ritualVideo;return v.duration===10&&!v.inFlight&&Math.abs(v.currentTime-6.7083333333)<.07;},null,{timeout:6000});report.measurements.delayedMetadata=await state(p);await context.close();
  });
  await check('mobile usa três estados reversíveis, sem pin e sem busca contínua',async()=>{
    const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const p=await context.newPage();monitor(p);await ready(p);
    for(const [name,progress,time,index] of [['preparo',.125,1.25,'0'],['tecnica',.525,5.25,'1'],['acabamento',.925,9.25,'2'],['preparo-reverso',.125,1.25,'0']]){await seek(p,progress,time);await p.waitForTimeout(400);assert.equal((await state(p)).ritualStage,index);await snapshot(p,'mobile-'+name);}
    const count=(await state(p)).ritualVideo.seeks;
    for(const progress of [.13,.15,.18,.2,.22]){await p.evaluate(v=>motionLab.seekRitual(v),progress);await p.waitForTimeout(25);}
    assert.equal((await state(p)).ritualVideo.seeks,count);assert.equal(await p.locator('.pin-spacer').count(),0);assert.equal((await state(p)).ritualVideo.mode,'segmented');
    report.measurements.mobile=await state(p);
    await p.setViewportSize({width:320,height:568});await p.waitForTimeout(350);await seek(p,.525,5.25);await p.waitForTimeout(400);const text=await p.locator('[data-chapter="1"]').boundingBox(),dock=await p.locator('.lab-dock').boundingBox();assert(text.y+text.height<dock.y);await snapshot(p,'small');
    for(const width of [320,390,768,820,1000,1440]){await p.setViewportSize({width,height:900});await p.waitForTimeout(250);assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`overflow ${width}`);assert((await p.locator('.pin-spacer').count())<=1);}
    await context.close();
  });
  await check('reduced-motion inicial não solicita WebM e mantém três capítulos',async()=>{
    const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});const p=await context.newPage();monitor(p);const requests=[];p.on('request',r=>{if(r.url().endsWith('.webm'))requests.push(r.url());});await ready(p);await p.locator('#ritual').scrollIntoViewIfNeeded();await p.waitForTimeout(300);
    assert.equal(requests.length,0);assert.equal((await state(p)).scrollTriggers,0);for(const chapter of await p.locator('.ritual-chapter').all())assert(await chapter.isVisible());await snapshot(p,'mobile-reduced');await context.close();
  });
  await check('vídeo indisponível cai para poster, textos completos e sem corredor pinned',async()=>{
    const context=await browser.newContext({viewport:{width:1440,height:960}});const p=await context.newPage();await p.route('**/assets/ritual-scrub.webm',route=>route.abort());await ready(p);await p.locator('#ritual').scrollIntoViewIfNeeded();await p.waitForSelector('.video-error');
    const m=await state(p);assert(m.ritualVideo.failed);assert.equal(await p.locator('.pin-spacer').count(),0);for(const chapter of await p.locator('.ritual-chapter').all())assert(await chapter.isVisible());assert(await p.locator('.ritual-poster').isVisible());await snapshot(p,'fallback');await context.close();
  });
  await check('modo anterior permanece disponível para comparação',async()=>{
    const context=await browser.newContext({viewport:{width:1440,height:960}});const p=await context.newPage();monitor(p);await ready(p,'?ritual=mirror&nointro=1');assert.equal(await p.locator('.mirror-stage').count(),1);assert.equal(await p.locator('#ritual-video').count(),0);await p.evaluate(()=>motionLab.seekRitual(.6));await p.waitForTimeout(700);await snapshot(p,'legacy-tecnica');await context.close();
  });
  await check('erro durante o corte libera pin e mantém visitante no capítulo em fallback',async()=>{
    const context=await browser.newContext({viewport:{width:1440,height:960}});const p=await context.newPage();monitor(p);await ready(p);await seek(p,.525,5.25);await p.evaluate(()=>document.querySelector('#ritual-video').dispatchEvent(new Event('error')));await p.waitForSelector('.video-error');await p.waitForTimeout(250);
    assert.equal(await p.locator('.pin-spacer').count(),0);assert(await p.locator('[data-chapter="1"]').evaluate(n=>{const b=n.getBoundingClientRect();return b.top<innerHeight&&b.bottom>0;}));assert((await state(p)).ritualVideo.failed);await context.close();
  });
  await check('falha de GSAP e JavaScript desligado mantêm poster e textos em fluxo',async()=>{
    const context=await browser.newContext({viewport:{width:1440,height:960}});const p=await context.newPage();await p.route('**/node_modules/gsap/**',route=>route.abort());await p.goto(base+'?nointro=1');await p.waitForSelector('.motion-reduced');
    const boxes=await p.locator('.ritual-chapter').evaluateAll(nodes=>nodes.map(n=>({y:n.getBoundingClientRect().y,height:n.getBoundingClientRect().height,position:getComputedStyle(n).position})));
    assert(boxes.every(b=>b.position==='relative'));assert(boxes[1].y>=boxes[0].y+boxes[0].height);assert(await p.locator('.ritual-poster').isVisible());await context.close();
    const noJS=await browser.newContext({viewport:{width:390,height:844},javaScriptEnabled:false});const n=await noJS.newPage();await n.goto(base);assert(await n.locator('.ritual-poster').isVisible());assert.equal(await n.locator('.ritual-chapter').count(),3);assert.equal(await n.locator('.ritual-chapter').first().evaluate(el=>getComputedStyle(el).position),'relative');await noJS.close();
  });
  await check('console normal sem erros; sem backend, API ou recursos externos',async()=>{assert.deepEqual(report.consoleErrors,[]);assert.deepEqual(report.externalRequests,[]);});
  await writeFile(new URL('./report.json',artifacts),JSON.stringify(report,null,2)+'\n');console.log(`\n${report.passed.length}/${report.passed.length} checks passed.`);
}catch(error){await writeFile(new URL('./failure.json',artifacts),JSON.stringify({...report,error:error.stack},null,2)+'\n');throw error;}
finally{await browser?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}

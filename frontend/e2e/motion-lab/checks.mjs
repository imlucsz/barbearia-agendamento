import assert from 'node:assert/strict';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { createLabServer } from './server.mjs';

// Real browser, static fixtures only: this never starts the backend or accesses a DB.
const artifacts=fileURLToPath(new URL('./artifacts/legacy-video-round/',import.meta.url));
await mkdir(artifacts,{recursive:true});
const server=createLabServer();
await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
const origin=`http://127.0.0.1:${server.address().port}`;
const url=origin+'/frontend/e2e/motion-lab/';
let browser;
const results=[],normalErrors=[],unexpectedRequests=[],measurements={};
const capture=(page,name)=>page.screenshot({path:artifacts+name+'.png'});
const state=page=>page.evaluate(()=>motionLab.snapshot());
async function ready(page,suffix=''){const target=new URL(url+suffix);target.searchParams.set('ritual','mirror');await page.goto(target.href);await page.waitForFunction(()=>window.motionLab||document.documentElement.classList.contains('motion-reduced'));}
async function check(name,fn){await fn();results.push(name);console.log('PASS '+name);}
function monitor(page){page.on('pageerror',error=>normalErrors.push(error.message));page.on('console',message=>{if(message.type()==='error')normalErrors.push(message.text());});page.on('request',request=>{if(!request.url().startsWith(origin)&&!request.url().startsWith('data:'))unexpectedRequests.push(request.url());if(/\/services\/|\/informacoes\/|\/appointments|\/auth\//.test(request.url()))unexpectedRequests.push(request.url());});}
try{
  browser=await chromium.launch({headless:true,channel:'chrome',args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader']});
  const desktop=await browser.newContext({viewport:{width:1440,height:960},deviceScaleFactor:1});
  const page=await desktop.newPage();monitor(page);
  await ready(page);
  await check('intro natural 3.5s termina e mantém hero/CTA',async()=>{
    assert.equal((await state(page)).introDuration,3.5);
    // Observe the completion/watchdog independently of a throttled headless RAF.
    await page.waitForFunction(()=>!motionLab.snapshot().introActive,{},{timeout:6000,polling:100});
    assert.equal(await page.locator('.intro-shell').isVisible(),false);
    assert.equal(await page.locator('#hero-title').getAttribute('aria-label'),'O clássico nunca sai de cena.');
    assert(await page.locator('.hero .booking-button').isVisible());
    measurements.hero=await state(page);
    await capture(page,'hero');
  });
  await check('antecipação → fechamento → reação → handoff com mesmos elementos',async()=>{
    await page.evaluate(()=>motionLab.seekIntro(1.22));
    const before=await page.locator('.hero-tool .half-front').getAttribute('transform');
    await capture(page,'intro-antecipacao');
    await page.evaluate(()=>motionLab.seekIntro(1.56));
    const after=await page.locator('.hero-tool .half-front').getAttribute('transform');
    assert.notEqual(before,after);
    assert(Number(await page.locator('.intro-seam').evaluate(n=>getComputedStyle(n).opacity))>.5);
    const visibleTool=await page.locator('.hero-tool').evaluate(n=>{const b=n.getBoundingClientRect();return getComputedStyle(n).zIndex>80&&b.bottom>100&&b.top<innerHeight;});
    assert(visibleTool);await capture(page,'intro');
    await page.evaluate(()=>motionLab.seekIntro(2.5));await capture(page,'intro-handoff');
    await page.evaluate(()=>motionLab.skip());
    assert.equal(await page.locator('.hero-tool').count(),1);
  });
  await check('skip e Escape finalizam sem bloqueio; replay não duplica recursos',async()=>{
    const baseline=await state(page);
    for(let i=0;i<3;i++){await page.locator('#replay').click();await page.keyboard.press('Escape');assert.equal((await state(page)).introActive,false);}
    await page.locator('#replay').click();await page.locator('#skip-intro').click();
    const after=await state(page);assert.equal(after.introActive,false);assert.equal(after.listeners,baseline.listeners);assert.equal(after.canvases,baseline.canvases);
    await page.reload();await page.waitForFunction(()=>window.motionLab);assert.equal((await state(page)).introActive,false);
  });
  await check('Tab encerra intro e pointer move luz sem mover CTA',async()=>{
    await page.locator('#replay').click();await page.keyboard.press('Tab');assert.equal((await state(page)).introActive,false);
    const cta=await page.locator('.hero .booking-button').boundingBox();
    await page.mouse.move(1300,300);await page.waitForTimeout(200);
    const light=await page.locator('.hero-light').getAttribute('style');
    await page.mouse.move(100,300);await page.waitForTimeout(400);
    assert.notEqual(await page.locator('.hero-light').getAttribute('style'),light);
    const after=await page.locator('.hero .booking-button').boundingBox();assert(Math.abs(cta.x-after.x)<.5&&Math.abs(cta.y-after.y)<.5);
  });
  const ritualStates={};
  await check('Ritual pinned transforma e reverte PREPARO → TÉCNICA → ACABAMENTO → PREPARO',async()=>{
    for(const [name,p,index] of [['preparo',.16,'0'],['tecnica',.6,'1'],['acabamento',.94,'2']]){
      await page.evaluate(p=>motionLab.seekRitual(p),p);
      await page.waitForFunction(p=>Math.abs(motionLab.snapshot().ritualProgress-p)<.005,p);
      assert.equal((await state(page)).ritualStage,index);
      ritualStates[name]=await page.locator('.mirror-fog').evaluate(n=>Number(getComputedStyle(n).opacity));
      await capture(page,'ritual-'+name);
    }
    assert(ritualStates.preparo>ritualStates.tecnica&&ritualStates.tecnica>ritualStates.acabamento);
    await page.evaluate(()=>motionLab.seekRitual(.16));
    await page.waitForFunction(()=>motionLab.snapshot().ritualStage==='0'&&Math.abs(motionLab.snapshot().ritualProgress-.16)<.005);
    assert(await page.locator('html').evaluate(n=>n.classList.contains('ritual-is-pinned')));
    assert.equal(await page.locator('.pin-spacer').count(),1);
  });
  await check('pole Three real e SVG coexistem; pausa suspende os consumidores',async()=>{
    await page.locator('#pole-study').scrollIntoViewIfNeeded();
    await page.waitForFunction(()=>motionLab.snapshot().three!==null&&motionLab.snapshot().activeTasks.some(n=>n.includes('Three')),{},{timeout:12000});
    const m=await state(page);assert.equal(m.webglContexts,1);assert(m.three.triangles>0);assert.equal(m.continuousRAFLoops,1);assert(m.activeTasks.some(n=>n.includes('Three')));
    measurements.poles=m;
    await capture(page,'poles');
    await page.locator('#pause').click();assert.equal((await state(page)).activeCanvases,0);assert.equal((await state(page)).continuousRAFLoops,0);
    await page.locator('#pause').click();assert.equal((await state(page)).continuousRAFLoops,1);
  });
  await check('perda real de contexto ativa SVG; retry recupera Three em canvas novo',async()=>{
    await page.evaluate(()=>{window.__oldCanvas=document.querySelector('#pole-canvas');__oldCanvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext();});
    await page.waitForFunction(()=>!document.querySelector('#three-retry').hidden);
    assert(await page.locator('.three-fallback').isVisible());
    await page.locator('#three-retry').click();
    await page.waitForFunction(()=>motionLab.snapshot().three!==null&&document.querySelector('.pole-three').classList.contains('is-ready'));
    assert(await page.evaluate(()=>document.querySelector('#pole-canvas')!==__oldCanvas&&!document.querySelector('#pole-canvas').getContext('webgl2').isContextLost()));
    assert.equal((await state(page)).webglContexts,1);
  });
  await check('CTA encerra narrativa; Canvas suspensos fora de uso e sem overflow',async()=>{
    await page.locator('#finale').scrollIntoViewIfNeeded();await page.waitForTimeout(1000);
    assert.equal((await state(page)).activeCanvases,0);
    measurements.offscreen=await state(page);
    assert(await page.locator('.finale .booking-button').isVisible());
    const box=await page.locator('.finale .booking-button').boundingBox();assert(box.width>=240&&box.height>=50);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    await capture(page,'cta-final');
  });
  await check('reduced-motion em sessão remove pin, triggers e atmosfera',async()=>{
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.waitForFunction(()=>motionLab.snapshot().reduced&&motionLab.snapshot().scrollTriggers===0,null,{polling:100});
    const m=await state(page);assert(m.reduced);assert.equal(m.scrollTriggers,0);assert.equal(m.activeCanvases,0);assert.equal(m.introActive,false);
    measurements.reduced=m;
    assert.equal(await page.locator('.pin-spacer').count(),0);
    for(const chapter of await page.locator('.ritual-chapter').all())assert(await chapter.isVisible());
    await page.locator('#ritual').scrollIntoViewIfNeeded();await capture(page,'reduced-motion');
    await page.emulateMedia({reducedMotion:'no-preference'});
    await page.waitForFunction(()=>!motionLab.snapshot().reduced&&motionLab.snapshot().scrollTriggers===5,null,{polling:100});
    assert.equal((await state(page)).scrollTriggers,5);assert.equal(await page.locator('.pin-spacer').count(),1);
  });
  await check('cleanup libera Canvas/WebGL, triggers e listeners próprios',async()=>{
    await page.evaluate(()=>motionLab.destroy());await page.waitForTimeout(200);const m=await state(page);
    assert.equal(m.listeners,0);assert.equal(m.webglContexts,0);assert.equal(m.canvases,0);assert.equal(m.scrollTriggers,0);assert.equal(m.activeTasks.length,0);assert.equal(m.scheduledRAF,0);
    measurements.destroyed=m;
  });
  await desktop.close();

  const mobile=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true});
  const phone=await mobile.newPage();monitor(phone);await ready(phone);
  await check('mobile mantém intro 2.3s, gesto, CTA e 23 partículas',async()=>{
    assert(Math.abs((await state(phone)).introDuration-2.3)<.01);
    await phone.waitForFunction(()=>!motionLab.snapshot().introActive,{},{timeout:6000});
    assert.equal((await state(phone)).particles,23);assert.equal(await phone.locator('.pin-spacer').count(),0);
    measurements.mobile=await state(phone);
    await capture(phone,'mobile-hero');
    await phone.locator('.ritual-chapters').scrollIntoViewIfNeeded();await phone.waitForTimeout(500);await capture(phone,'mobile-ritual');
    assert.equal(await phone.locator('.ritual-chapter').count(),3);
  });
  await check('viewports 320/390/768/820/1000/1440 sem overflow nem duplicação de pin',async()=>{
    for(const width of [320,390,768,820,1000,1440]){await phone.setViewportSize({width,height:900});await phone.waitForTimeout(350);assert.equal(await phone.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`overflow ${width}`);assert((await phone.locator('.pin-spacer').count())<=1);}
  });
  await mobile.close();
  await check('reduced-motion inicial não executa intro ou scrub',async()=>{
    const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});const p=await context.newPage();monitor(p);await ready(p);
    const m=await state(p);assert(m.reduced);assert.equal(m.introActive,false);assert.equal(m.scrollTriggers,0);assert.equal(m.activeTasks.length,0);await context.close();
  });
  await check('falha de import Three mantém SVG e demais cenas',async()=>{
    const context=await browser.newContext({viewport:{width:1440,height:960}});const p=await context.newPage();
    await p.route('**/node_modules/three/**',route=>route.abort());
    await ready(p,'?nointro=1');await p.locator('#pole-study').scrollIntoViewIfNeeded();
    await p.waitForFunction(()=>document.querySelector('#three-status').textContent.includes('indisponível'));
    assert.equal((await state(p)).webglContexts,0);assert(await p.locator('.three-fallback').isVisible());assert.equal((await state(p)).scrollTriggers,5);await context.close();
  });
  await check('falha parcial após criar renderer libera recursos Three e conserva SVG',async()=>{
    const context=await browser.newContext({viewport:{width:1440,height:960}});const p=await context.newPage();
    await p.addInitScript(()=>{const Original=window.ResizeObserver;window.ResizeObserver=class extends Original{observe(target,...args){if(target.classList.contains('pole-three'))throw new Error('falha controlada após renderer');return super.observe(target,...args);}};});
    await ready(p,'?nointro=1');await p.locator('#pole-study').scrollIntoViewIfNeeded();
    try{await p.waitForFunction(()=>document.querySelector('#three-status').textContent.includes('indisponível'));}
    catch(error){console.log('Partial-init diagnostic:',await p.evaluate(()=>({status:document.querySelector('#three-status').textContent,metrics:motionLab.snapshot()})));throw error;}
    const m=await state(p);assert.equal(m.webglContexts,0);assert.equal(m.canvases,1);assert(!m.activeTasks.some(n=>n.includes('Three')));assert(await p.locator('.three-fallback').isVisible());await context.close();
  });
  await check('falha de GSAP preserva composição estática e links',async()=>{
    const context=await browser.newContext();const p=await context.newPage();await p.route('**/node_modules/gsap/**',route=>route.abort());await ready(p);
    assert(await p.locator('#hero-title').isVisible());assert(await p.locator('.hero .booking-button').isVisible());assert.equal(await p.locator('.intro-shell').isVisible(),false);assert.equal(await p.locator('.mirror-svg').count(),1);await context.close();
  });
  await check('console normal limpo, sem API/backend/stock ou solicitações externas',async()=>{assert.deepEqual(normalErrors,[]);assert.deepEqual(unexpectedRequests,[]);});
  const buildSource=await readFile(new URL('../../scripts/build-static.mjs',import.meta.url),'utf8');
  assert(buildSource.includes('"e2e"'));
  const report={passed:results.length,results,measurements,ritualFog:ritualStates,consoleErrors:normalErrors,unexpectedRequests,generatedAt:new Date().toISOString()};
  await writeFile(artifacts+'validation.json',JSON.stringify(report,null,2)+'\n');
  console.log(`\n${results.length}/${results.length} browser checks passed. Artifacts: ${artifacts}`);
}finally{await browser?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}

// Development-only investigation: native touch inertia versus seeker convergence.
import { chromium } from '@playwright/test';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createLabServer } from './motion-lab/server.mjs';
const server=createLabServer();
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const results=[];
let browser;
try {
  browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:820,height:1180},hasTouch:true});
  await page.route('**/*',async route=>{
    const url=route.request().url();
    if(!url.startsWith(origin))return route.fulfill({json:[]});
    if(/\/services\/?(?:\?|$)/.test(url)||/\/appointments\/avaliacoes/.test(url))return route.fulfill({json:[]});
    if(/\/informacoes\//.test(url))return route.fulfill({json:{endereco:'Local de teste',telefone:'11999990000'}});
    if(url.endsWith('installation-config.mjs'))return route.fulfill({contentType:'text/javascript',body:(await readFile(new URL('../assets/js/installation-config.mjs',import.meta.url),'utf8')).replace('estrelinhaWidget: true','estrelinhaWidget: false')});
    return route.continue();
  });
  await page.addInitScript(()=>sessionStorage.setItem('barbearia.home.intro.v1','seen'));
  await page.goto(origin+'/frontend/pages/index.html');
  await page.waitForFunction(()=>window.homeExperience?.snapshot().ritualVideo);
  await page.evaluate(await readFile(new URL('./ritual-diagnostics.js',import.meta.url),'utf8'));
  const seek=()=>page.evaluate(()=>{
    const t=ScrollTrigger.getById('lab-ritual-mobile');
    scrollTo({top:t.start+(t.end-t.start)*.25,behavior:'instant'});ScrollTrigger.update();
  });
  await seek();
  await page.waitForFunction(()=>document.querySelector('#ritual-video').readyState>=2);
  await page.waitForTimeout(700);
  const cdp=await page.context().newCDPSession(page);
  for(let round=0;round<12;round++) {
    await seek();await page.waitForTimeout(500);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:656,y:944}]});
    for(let i=1;i<=10;i++) {
      await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:656,y:1180*(.8-i*.045)}]});
      await page.waitForTimeout(20);
    }
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await page.waitForTimeout(300);
    await seek();
    const samples=[];
    for(const delay of [0,100,200,300,400,500]) {
      await page.waitForTimeout(delay);
      samples.push(await page.evaluate(()=>({ms:performance.now(),scrollY,progress:ScrollTrigger.getById('lab-ritual-mobile').progress,...homeExperience.snapshot().ritualVideo})));
    }
    results.push({round,samples});
    console.log(JSON.stringify({round,samples:samples.map(s=>({ms:s.ms,y:s.scrollY,p:s.progress,target:s.desiredTime,time:s.currentTime,presented:s.presentedTime,seeking:s.seeking}))}));
  }
  const diagnostic=await page.evaluate(()=>ritualDiagnostics.stop());
  await mkdir('test-results',{recursive:true});
  await writeFile('test-results/ritual-touch-probe.json',JSON.stringify({results,diagnostic},null,2));
} finally {
  await browser?.close();server.closeAllConnections();await new Promise(resolve=>server.close(resolve));
}

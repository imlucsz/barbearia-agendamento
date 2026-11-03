// Isolated static HOME probe. Fictitious API data; no backend/database.
import { chromium } from '@playwright/test';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createLabServer } from './motion-lab/server.mjs';
const server = createLabServer();
await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const snippet = await readFile(new URL('./ritual-diagnostics.js',import.meta.url),'utf8');
const results = [];
try {
  for (const channel of ['chrome','msedge']) {
    let browser;
    try {
      browser = await chromium.launch({ channel, headless: true });
      const system = await browser.newBrowserCDPSession();
      const gpu = await system.send('SystemInfo.getInfo');
      for (const viewport of [{width:1440,height:900},{width:1440,height:640}]) {
        const page = await browser.newPage({viewport});
        await page.route('**/*',async route => {
          const url = route.request().url();
          if (!url.startsWith(origin)) return route.fulfill({json:[]});
          if (/\/services\/?(?:\?|$)/.test(url) || /\/appointments\/avaliacoes/.test(url)) return route.fulfill({json:[]});
          if (/\/informacoes\//.test(url)) return route.fulfill({json:{endereco:'Local de teste',telefone:'11999990000'}});
          return route.continue();
        });
        const media = [], errors = [], responses = [];
        page.on('pageerror',e=>errors.push(e.message));
        page.on('response',r=>{if(r.url().endsWith('ritual-scrub.webm')) responses.push({status:r.status(),headers:r.headers()});});
        const cdp = await page.context().newCDPSession(page);
        await cdp.send('Media.enable'); await cdp.send('Performance.enable');
        cdp.on('Media.playerPropertiesChanged',e=>media.push(e));
        await page.addInitScript(()=>sessionStorage.setItem('barbearia.home.intro.v1','seen'));
        await page.goto(origin+'/frontend/pages/index.html');
        await page.waitForFunction(()=>window.homeExperience?.snapshot().ritualVideo);
        await page.evaluate(snippet);
        await page.evaluate(()=>document.querySelector('#ritual').scrollIntoView());
        await page.waitForFunction(()=>document.querySelector('#ritual-video').readyState>=2);
        await page.waitForTimeout(500);
        const before = await cdp.send('Performance.getMetrics');
        // Identical scroll path and timing, forwards then backwards, both engines.
        await page.evaluate(async()=>{
          const trigger = ScrollTrigger.getById('lab-ritual') || ScrollTrigger.getById('lab-ritual-mobile');
          for (const reverse of [false,true]) for(let i=0;i<=120;i++) {
            const p=reverse?1-i/120:i/120;
            window.scrollTo({top:trigger.start+(trigger.end-trigger.start)*p,behavior:'instant'});
            ScrollTrigger.update(); await new Promise(resolve=>setTimeout(resolve,33));
          }
        });
        await page.waitForTimeout(700);
        const after = await cdp.send('Performance.getMetrics');
        const diagnostic = await page.evaluate(()=>ritualDiagnostics.stop());
        results.push({channel,version:browser.version(),viewport,diagnostic,media,errors,responses,before,after,
          gpu:{devices:gpu.gpu.devices,featureStatus:gpu.gpu.featureStatus}});
        console.log(JSON.stringify({channel,viewport,mode:diagnostic.snapshot.mode,counts:diagnostic.counts,quality:diagnostic.finalQuality}));
        await page.close();
      }
    } catch (error) {results.push({channel,error:error.message});console.error(channel,error.message);}
    finally {await browser?.close();}
  }
} finally {
  server.closeAllConnections(); await new Promise(resolve=>server.close(resolve));
  await mkdir('test-results',{recursive:true});
  await writeFile('test-results/ritual-diagnostics.json',JSON.stringify(results,null,2));
}
if (results.some(r=>r.error)) process.exitCode=1;

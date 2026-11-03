import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const service = { id: 71, nome: 'Corte de teste', descricao: 'Acabamento de teste', preco: 45, duracao_minutos: 35 };
test('Ritual universal: tempos intermediários, apresentação, reverse, resize e reduced', async ({ page }, testInfo) => {
  await page.addInitScript(() => sessionStorage.setItem('barbearia.home.intro.v1','seen'));
  await page.goto('/pages/index.html');
  await page.waitForFunction(() => window.homeExperience?.snapshot().ritualVideo);
  await expect.poll(() => page.evaluate(() => homeExperience.snapshot().ritualVideo.mode)).toBe('continuous-scrub');
  await page.evaluate(await readFile(new URL('./ritual-diagnostics.js',import.meta.url),'utf8'));
  const settleLayout=()=>page.evaluate(()=>new Promise(resolve=>{
    let previous='',stableSince=performance.now();
    function sample(now){
      const t=ScrollTrigger.getById('lab-ritual')||ScrollTrigger.getById('lab-ritual-mobile');
      const state=JSON.stringify([innerWidth,innerHeight,scrollY,t?.start,t?.end]);
      if(state!==previous){previous=state;stableSince=now;}
      if(now-stableSince>=250)resolve();else requestAnimationFrame(sample);
    }
    requestAnimationFrame(sample);
  }));
  await page.evaluate(async()=>{
    await document.fonts.ready;
    ScrollTrigger.refresh();
    const t=ScrollTrigger.getById('lab-ritual')||ScrollTrigger.getById('lab-ritual-mobile');
    scrollTo({top:t.start+(t.end-t.start)*.5,behavior:'instant'});ScrollTrigger.update();
  });
  await page.waitForFunction(()=>{
    const s=homeExperience.snapshot().ritualVideo;
    return s.failed||(s.visible&&s.readyState>=2&&!s.seeking);
  });
  const media=await page.evaluate(()=>({supported:document.querySelector('#ritual-video').canPlayType('video/webm; codecs="vp9"'),...homeExperience.snapshot().ritualVideo}));
  await testInfo.attach('media-support',{body:JSON.stringify(media),contentType:'application/json'});
  expect(media.failed,`media failure: ${media.failureReason}; canPlayType=${media.supported}`).toBe(false);
  await settleLayout();
  const seek = async p => {
    await page.evaluate(p => {
      const t=ScrollTrigger.getById('lab-ritual') || ScrollTrigger.getById('lab-ritual-mobile');
      window.scrollTo({top:t.start+(t.end-t.start)*p,behavior:'instant'}); ScrollTrigger.update();
    },p);
    const time=Math.min(239/24,Math.round(p*240)/24);
    try {
      await expect.poll(() => page.locator('#ritual-video').evaluate((v,time)=>v.seeking?100:Math.abs(v.currentTime-time),time)).toBeLessThan(.15);
    await expect.poll(() => page.evaluate(time => {
      const rows=ritualDiagnostics.report().rows;
      return rows.some(r=>r.type==='frame' && Math.abs(r.mediaTime-time)<.15);
    },time)).toBe(true);
    } catch(error) {
      const evidence={requestedProgress:p,...await page.evaluate(()=>ritualDiagnostics.report())};
      await testInfo.attach('convergence-failure',{body:JSON.stringify(evidence),contentType:'application/json'});
      throw error;
    }
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
    if ([.12,.5,.88].includes(p)) {
      await page.waitForTimeout(350);
      const bounds=await page.evaluate(()=>{
        const chapter=document.querySelector(`.ritual-chapter[data-chapter="${document.documentElement.dataset.ritualStage}"]`);
        return {label:chapter.querySelector('.eyebrow').getBoundingClientRect().top,
          textBottom:chapter.querySelector('p').getBoundingClientRect().bottom,
          headerBottom:document.querySelector('.site-header').getBoundingClientRect().bottom,
          railTop:document.querySelector('.ritual-progress').getBoundingClientRect().top};
      });
      expect(bounds.label).toBeGreaterThanOrEqual(bounds.headerBottom);
      expect(bounds.textBottom).toBeLessThan(bounds.railTop);
      const {width,height}=page.viewportSize();
      await page.screenshot({path:testInfo.outputPath(`ritual-${width}x${height}-${p}.png`)});
    }
  };
  // Includes non-chapter times; cannot pass by rendering only three stills.
  for(const p of [0,.12,.25,.38,.5,.63,.75,.88,1,.63,.25]) await seek(p);
  if(testInfo.project.use.hasTouch) {
    const session=await page.context().newCDPSession(page);
    const y=await page.evaluate(()=>scrollY), {width,height}=page.viewportSize();
    await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:width*.8,y:height*.8}]});
    for(let i=1;i<=10;i++) {
      await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:width*.8,y:height*(.8-i*.045)}]});
      await page.waitForTimeout(20);
    }
    await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await expect.poll(()=>page.evaluate(()=>scrollY)).toBeGreaterThan(y+20);
    // Native fling can continue after touchEnd. Wait for actual scroll stability,
    // then assert convergence to the resulting scroll target before repositioning.
    await settleLayout();
    await expect.poll(()=>page.evaluate(()=>{
      const s=homeExperience.snapshot().ritualVideo;
      return s.seeking?100:Math.abs(s.currentTime-s.desiredTime);
    })).toBeLessThan(.15);
    await testInfo.attach('touch-settled',{body:JSON.stringify(await page.evaluate(()=>({scrollY,...homeExperience.snapshot().ritualVideo}))),contentType:'application/json'});
    await seek(.25);
  }
  await page.waitForTimeout(400);
  await expect(page.locator('.ritual-chapter[data-chapter="1"]')).toBeVisible();
  const stage=await page.locator('.ritual-stage').boundingBox();
  const video=await page.locator('#ritual-video').boundingBox();
  // Approved animated mask can inset the film by up to 3% on each side.
  expect(video.width).toBeGreaterThanOrEqual(stage.width*.94);
  await page.screenshot({path:testInfo.outputPath('ritual.png')});
  await page.setViewportSize({width:600,height:700});
  await settleLayout();
  await seek(.5);
  await page.setViewportSize({width:1440,height:900});
  await settleLayout();
  await seek(.63);
  expect(await page.locator('.pin-spacer').count()).toBe(1);
  const before=await page.evaluate(()=>ritualDiagnostics.stop());
  expect(before.counts.writesWhileSeeking).toBe(0);
  expect(before.counts.seeked).toBeGreaterThan(6);
  expect(new Set(before.rows.filter(r=>r.type==='frame').map(r=>r.mediaTime)).size).toBeGreaterThan(6);
  await testInfo.attach('diagnostics',{body:JSON.stringify(before),contentType:'application/json'});
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(page.locator('#ritual')).toHaveClass(/ritual-static/);
  expect(await page.locator('#ritual-video').getAttribute('src')).toBeNull();
  for(const c of await page.locator('.ritual-chapter').all()) await expect(c).toBeVisible();
  expect(await page.locator('.pin-spacer').count()).toBe(0);
  await page.emulateMedia({reducedMotion:'no-preference'});
  await expect.poll(()=>page.evaluate(()=>homeExperience.snapshot().ritualVideo.mode)).toBe('continuous-scrub');
  await page.locator('#business-info').scrollIntoViewIfNeeded();
  await expect(page.locator('#business-info')).toBeInViewport();
});
test.beforeEach(async ({ page }) => {
  // Keep existing mascot out of presentation tests; its implementation is unchanged.
  await page.route('**/assets/js/installation-config.mjs', async route => {
    const source = await readFile(new URL('../assets/js/installation-config.mjs', import.meta.url), 'utf8');
    await route.fulfill({ status: 200, contentType: 'text/javascript', body: source.replace('estrelinhaWidget: true', 'estrelinhaWidget: false') });
  });
  await page.route('**/services/', route => route.fulfill({ json: [service] }));
  await page.route('**/informacoes/', route => route.fulfill({ json: {
    endereco: 'Rua de Teste, 10', telefone: '(11) 99999-0000', email: 'teste@example.test',
    dias_atendimento: 'Todos os dias', horario_funcionamento: '09:00 às 18:00',
    endereco_maps: 'https://www.google.com/maps/place/Teste',
  } }));
  await page.route('**/appointments/avaliacoes', route => route.fulfill({ json: [
    { nota: 4, comentario: 'Comentário fictício visível', oculta: false },
    { nota: 1, comentario: 'Comentário fictício oculto', oculta: true },
  ] }));
});

test('estrutura editorial preserva dados reais, hooks e destinos', async ({ page }) => {
  await page.goto('/pages/index.html');
  await expect(page.locator('#hero-title')).toHaveText('O clássico nunca sai de cena.');
  await expect(page.locator('#services-list')).toContainText(service.nome);
  await expect(page.locator('#services-list')).toContainText('35 min');
  await expect(page.locator('.service-book')).toHaveAttribute('href', 'client-services.html?service_id=71');
  await expect(page.locator('#ritual article')).toHaveCount(3);
  await expect(page.getByRole('link', { name: 'Agendar meu horário' })).toHaveAttribute('href', 'client-services.html');
  await expect(page.locator('#review-average')).toHaveText('4.0 / 5 · 1 avaliação');
  await expect(page.locator('#reviews-list')).not.toContainText('oculto');
  await expect(page.locator('#address a')).toHaveAttribute('href', 'https://www.google.com/maps/place/Teste');
  await expect(page.locator('#phone a')).toHaveAttribute('href', 'https://wa.me/5511999990000');
  expect(await page.locator('[id]').evaluateAll(nodes => new Set(nodes.map(n => n.id)).size === nodes.length)).toBe(true);
});

test('área de autenticação mantém o destino correto para o papel autenticado', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'test-only-token');
    localStorage.setItem('user', JSON.stringify({ role: 'admin' }));
  });
  await page.goto('/pages/index.html');
  await expect(page.locator('#auth-area a')).toHaveAttribute('href', 'admin.html');
  await expect(page.locator('#auth-area button')).toHaveText('Sair');
});

test('composição cabe na viewport e ação precede a arte no mobile', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => sessionStorage.setItem('barbearia.home.intro.v1', 'seen'));
  await page.goto('/pages/index.html');
  await page.waitForFunction(() => window.homeExperience?.snapshot());
  if (page.viewportSize().width <= 680) {
    const action = await page.locator('#btn-agendar-hero').boundingBox();
    const art = await page.locator('.hero-art').boundingBox();
    expect(action.y + action.height).toBeLessThan(art.y);
  }
  await page.locator('#ritual').scrollIntoViewIfNeeded();
  const mobile = page.viewportSize().width < 1000 || page.viewportSize().height < 650;
  const triggerId = mobile ? 'lab-ritual-mobile' : 'lab-ritual';
  await page.waitForFunction(id => window.ScrollTrigger?.getById(id), triggerId);
  await page.evaluate(id => {
    const trigger = window.ScrollTrigger.getById(id);
    window.scrollTo({ top: trigger.start + 1, behavior: 'instant' });
    window.ScrollTrigger.update();
  }, triggerId);
  await page.waitForFunction(id => window.ScrollTrigger.getById(id)?.isActive, triggerId);
  const firstChapterButton = page.locator('#ritual [data-stage="0"]');
  await firstChapterButton.click();
  await page.waitForFunction(id => window.ScrollTrigger?.getById(id)?.isActive, triggerId);
  await expect.poll(() => page.locator('#ritual-video').evaluate(video => video.readyState)).toBeGreaterThanOrEqual(2);
  await expect(page.locator('.ritual-film')).toHaveClass(/has-video-frame/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  const stage = await page.locator('.ritual-film').boundingBox();
  const copy = await page.locator('.ritual-chapter[data-chapter="0"]').boundingBox();
  expect(stage).not.toBeNull();
  expect(copy).not.toBeNull();
  expect(stage.width).toBeGreaterThanOrEqual(page.viewportSize().width * (mobile ? .95 : .998));
  expect(stage.height).toBeGreaterThan(page.viewportSize().height * .9);
  expect(copy.x + copy.width).toBeGreaterThan(stage.x);
  expect(copy.x).toBeLessThan(stage.x + stage.width);
  expect(copy.y + copy.height).toBeGreaterThan(stage.y);
  expect(copy.y).toBeLessThan(stage.y + stage.height);
  await expect(page.locator('.ritual-film')).toBeVisible();
  expect(errors).toEqual([]);
});

test('movimento reduzido usa poster e mantém todos os capítulos legíveis', async ({ page }) => {
  await page.goto('/pages/index.html');
  await expect(page.locator('html')).toHaveClass(/experience-ready/);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(page.locator('#ritual')).toHaveClass(/ritual-static/);
  await expect(page.locator('html')).not.toHaveClass(/experience-ready/);
  for (const chapter of await page.locator('.ritual-chapter').all()) await expect(chapter).toBeVisible();
  await expect(page.locator('.ritual-poster')).toBeVisible();
  expect(await page.locator('#ritual-video').evaluate(n => getComputedStyle(n).display)).toBe('none');
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior)).toBe('auto');
});

test('sem observer ou com falha do módulo, conteúdo continua disponível', async ({ page }) => {
  await page.addInitScript(() => { window.IntersectionObserver = undefined; });
  await page.goto('/pages/index.html');
  await expect(page.locator('#services-list')).toContainText(service.nome);
  await expect(page.getByRole('heading', { name: /A arte está no processo/ })).toHaveCount(1);
  await page.route('**/home-experience.mjs', route => route.abort());
  await page.reload();
  await expect(page.locator('#btn-agendar-hero')).toBeVisible();
  await expect(page.locator('#ritual article')).toHaveCount(3);
  await expect(page.getByRole('link', { name: 'Agendar meu horário' })).toBeVisible();
});

test('falha do WebM mantém poster e narrativa do Ritual disponíveis', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('barbearia.home.intro.v1', 'seen'));
  await page.route('**/ritual-scrub.webm', route => route.abort());
  await page.goto('/pages/index.html');
  await page.locator('#ritual').scrollIntoViewIfNeeded();
  await expect(page.locator('#ritual')).toHaveClass(/video-error/);
  await expect(page.locator('.ritual-poster')).toBeVisible();
  for (const chapter of await page.locator('.ritual-chapter').all()) await expect(chapter).toBeVisible();
});

test('skeleton termina em erro, retry recupera catálogo sem atrasar agendamento', async ({ page }) => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  await page.route('**/services/', route => release(route));
  await page.goto('/pages/index.html');
  const route = await pending;
  await expect(page.locator('#services-skeleton .skeleton-loading')).toHaveCount(3);
  await expect(page.locator('#btn-agendar-hero')).toBeVisible();
  await route.fulfill({ status: 503, json: { detail: 'Indisponível no teste' } });
  await expect(page.locator('#services-error')).toBeVisible();
  await expect(page.locator('#services-skeleton .skeleton-loading')).toHaveCount(0);
  await page.route('**/services/', route => route.fulfill({ json: [service] }));
  await page.locator('#btn-retry-services').click();
  await expect(page.locator('#services-list .service-card')).toHaveCount(1);
  await expect(page.locator('#services-error')).toBeHidden();
});

test('menu, teclado e âncoras mantêm acesso ao agendamento', async ({ page }) => {
  await page.goto('/pages/index.html');
  if (page.viewportSize().width <= 860) {
    await page.getByRole('button', { name: 'Abrir menu', exact: true }).click();
    await page.locator('#main-nav a[href="#services"]').click();
    await expect(page.locator('#nav-toggle')).toHaveAttribute('aria-expanded', 'false');
    await expect.poll(() => page.evaluate(() => document.getElementById('services').getBoundingClientRect().top >= document.querySelector('.site-header').getBoundingClientRect().bottom - 1)).toBe(true);
  }
  const action = page.locator('#btn-agendar-hero');
  await action.focus();
  await expect(action).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Explorar serviços' })).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(action).toBeFocused();
  expect(await action.evaluate(n => getComputedStyle(n).outlineStyle)).not.toBe('none');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/client-services\.html$/);
});

test('filme ocupa o palco, texto sobrepõe a cena e scrub avança/reverte', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('barbearia.home.intro.v1', 'seen'));
  await page.goto('/pages/index.html');
  if (page.viewportSize().width >= 1000) {
    await expect(page.locator('html')).toHaveClass(/ritual-is-pinned/);
    const viewport = page.viewportSize();
    await page.locator('#ritual').scrollIntoViewIfNeeded();
    const film = await page.locator('.ritual-film').boundingBox();
    expect(film.width).toBeGreaterThanOrEqual(viewport.width - 2);
    expect(film.height).toBeGreaterThanOrEqual(viewport.height - 2);
    const text = await page.locator('.ritual-chapter').first().boundingBox();
    expect(text.x + text.width).toBeLessThan(film.x + film.width);
    expect(text.y + text.height).toBeGreaterThan(film.y);
    await expect.poll(() => page.locator('#ritual-video').evaluate(video => video.readyState)).toBeGreaterThanOrEqual(2);
    await expect(page.locator('.ritual-film')).toHaveClass(/has-video-frame/);
    await expect.poll(() => page.evaluate(() => window.homeExperience?.snapshot().ritualVideo?.duration)).toBe(10);
    const range = await page.request.get('/assets/media/home/ritual-scrub.webm', { headers: { Range: 'bytes=0-1023' } });
    expect(range.status()).toBe(206);
    expect(range.headers()['content-range']).toMatch(/^bytes 0-1023\//);

    const triggerProgress = async progress => page.evaluate(value => {
      const trigger = window.ScrollTrigger?.getById('lab-ritual');
      if (!trigger) throw new Error('Ritual ScrollTrigger is unavailable');
      window.scrollTo({ top: trigger.start + (trigger.end - trigger.start) * value, behavior: 'instant' });
      window.ScrollTrigger.update();
    }, progress);
    await triggerProgress(.5);
    await expect(page.locator('html')).toHaveAttribute('data-ritual-stage', '1');
    await triggerProgress(.12);
    await expect(page.locator('html')).toHaveAttribute('data-ritual-stage', '0');
    await triggerProgress(.9);
    await expect(page.locator('html')).toHaveAttribute('data-ritual-stage', '2');
    const technique = page.locator('#ritual [data-stage="1"]');
    await technique.focus();
    await expect(technique).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('html')).toHaveAttribute('data-ritual-stage', '1');
    await expect(technique).toHaveAttribute('aria-current', 'step');
    const finish = page.locator('#ritual [data-stage="2"]');
    await finish.focus();
    await expect(finish).toBeFocused();
    await page.keyboard.press('Space');
    await expect(page.locator('html')).toHaveAttribute('data-ritual-stage', '2');
    await expect(finish).toHaveAttribute('aria-current', 'step');
    const metrics = await page.evaluate(() => window.homeExperience.snapshot());
    expect(metrics.ritualVideo.additionalRAFLoops).toBe(0);
    expect(metrics.scrollTriggers).toBeGreaterThan(0);
    await page.setViewportSize({ width: 600, height: 800 });
    await expect(page.locator('html')).not.toHaveClass(/ritual-is-pinned/);
    await expect(page.locator('#ritual')).toHaveClass(/ritual-mobile/);
  }
  if (page.viewportSize().width < 1000) {
    await page.locator('#ritual').scrollIntoViewIfNeeded();
    const mobileTrigger = 'lab-ritual-mobile';
    await page.waitForFunction(id => window.ScrollTrigger?.getById(id), mobileTrigger);
    await page.evaluate(id => {
      const trigger = window.ScrollTrigger.getById(id);
      window.scrollTo({ top: trigger.start + 1, behavior: 'instant' });
      window.ScrollTrigger.update();
    }, mobileTrigger);
    await page.waitForFunction(id => window.ScrollTrigger.getById(id)?.isActive, mobileTrigger);
    await expect.poll(() => page.locator('#ritual-video').evaluate(video => video.readyState)).toBeGreaterThanOrEqual(2);
    await expect(page.locator('.ritual-film')).toHaveClass(/has-video-frame/);
    const technique = page.locator('#ritual [data-stage="1"]');
    await technique.focus();
    await expect(technique).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('html')).toHaveAttribute('data-ritual-stage', '1');
    const finish = page.locator('#ritual [data-stage="2"]');
    await finish.focus();
    await expect(finish).toBeFocused();
    await page.keyboard.press('Space');
    await expect(page.locator('html')).toHaveAttribute('data-ritual-stage', '2');
  }
  await expect(page.locator('.ritual-chapter')).toHaveCount(3);
  const activeStage = await page.locator('html').getAttribute('data-ritual-stage');
  await expect(page.locator(`.ritual-chapter[data-chapter="${activeStage}"]`)).toBeVisible();
});

test('preferência reduzida inicial e APIs indisponíveis mantêm a leitura', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/pages/index.html');
  await expect(page.locator('html')).not.toHaveClass(/experience-ready|ritual-enhanced/);
  await expect(page.locator('#btn-agendar-hero')).toBeVisible();
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.addInitScript(() => {
    window.IntersectionObserver = class { constructor() { throw new Error('Observer indisponível no teste'); } };
    Element.prototype.animate = () => { throw new Error('Animação indisponível no teste'); };
  });
  await page.reload();
  await expect(page.locator('#services-list')).toContainText(service.nome);
  await expect(page.locator('html')).not.toHaveClass(/ritual-enhanced/);
  await expect(page.getByRole('heading', { name: /A arte está no processo/ })).toHaveCount(1);
});

test('mapa permanece interativo e sem ancestrais transformados', async ({ page }) => {
  await page.route('https://www.google.com/maps/embed**', route => route.fulfill({ contentType: 'text/html', body: '<p>Mapa fictício</p>' }));
  await page.route('**/informacoes/', route => route.fulfill({ json: {
    endereco: 'Rua de Teste, 10', dias_atendimento: 'Todos os dias', horario_funcionamento: '09:00 às 18:00',
    endereco_maps: 'https://www.google.com/maps/embed?pb=teste',
  } }));
  await page.goto('/pages/index.html');
  const map = page.locator('#map-container iframe');
  await expect(map).toHaveAttribute('title', 'Mapa da barbearia');
  await expect(map).toHaveAttribute('loading', 'lazy');
  expect(await map.evaluate(n => {
    for (let parent = n; parent; parent = parent.parentElement) {
      if (getComputedStyle(parent).transform !== 'none') return false;
    }
    return true;
  })).toBe(true);
});

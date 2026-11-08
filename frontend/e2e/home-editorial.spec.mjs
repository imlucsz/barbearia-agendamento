import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const malicious = '<img src=x onerror=alert(1)> Corte';
const services = [
  { id: 71, nome: 'Corte de teste', descricao: 'Acabamento de teste', preco: 45, duracao_minutos: 35 },
  { id: 72, nome: 'Barba de teste', descricao: 'Cuidado de teste', preco: 30, duracao_minutos: 20 },
  { id: 73, nome: malicious, descricao: 'Descrição longa '.repeat(30), preco: 80, duracao_minutos: 90 },
];
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/services/') return route.fulfill({ json: services });
    if (url.pathname === '/informacoes/') return route.fulfill({ json: { endereco: 'Rua de Teste, 10', dias_atendimento: 'Segunda a sexta', horario_funcionamento: '09:00 às 18:00' } });
    if (url.pathname === '/appointments/avaliacoes') return route.fulfill({ json: [] });
    if (url.pathname.endsWith('/installation-config.mjs')) {
      const body = await readFile(new URL('../assets/js/installation-config.mjs', import.meta.url), 'utf8');
      return route.fulfill({ contentType: 'text/javascript', body: body.replace('estrelinhaWidget: true', 'estrelinhaWidget: false') });
    }
    if (url.origin === 'http://127.0.0.1:4186' && /^\/(pages|assets)\//.test(url.pathname)) return route.continue();
    return route.abort();
  });
});

test('HOME aprovada integra fontes locais, arte livre e dados de serviço', async ({ page }, info) => {
  await page.addInitScript(() => sessionStorage.setItem('barbearia.home.intro.v1', 'seen'));
  await page.goto('/pages/index.html');
  await page.waitForFunction(() => window.homeExperience);
  await page.evaluate(() => document.fonts.ready);
  expect(await page.locator('h1').evaluate(e => getComputedStyle(e).fontFamily)).toContain('Fraunces');
  await expect(page.locator('#services-list .service-card')).toHaveCount(3);
  await expect(page.locator('#services-list')).toContainText(malicious);
  await expect(page.locator('#services-list img')).toHaveCount(0);
  await expect(page.locator('.service-book').first()).toHaveAttribute('href', 'client-services.html?service_id=71');
  await expect(page.locator('#services-list')).toContainText('35 min');
  await expect(page.locator('#services-list')).toContainText('R$ 45,00');
  const geometry = await page.evaluate(() => {
    const r = s => document.querySelector(s).getBoundingClientRect();
    const pole = r('.hero-pole'), tool = r('.hero-tool'), copy = r('.hero-copy');
    const overlaps = (a,b) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    return { clear: !overlaps(pole,copy) && !overlaps(tool,copy), overlap: overlaps(pole,tool), vertical: pole.height > pole.width * 2, overflow: document.documentElement.scrollWidth > innerWidth };
  });
  expect(geometry).toEqual({clear:true, overlap:true, vertical:true, overflow:false});
  await page.locator('.hero').screenshot({ path: info.outputPath('hero-approved.png') });
  await page.locator('#services').screenshot({ path: info.outputPath('catalog-approved.png') });
  await page.locator('.service-book').first().click();
  await expect(page).toHaveURL(/client-services\.html\?service_id=71$/);
});

test('intro aprovada tem duração curta e não repete ao navegar ou voltar', async ({ page }) => {
  await page.goto('/pages/index.html');
  await page.waitForFunction(() => window.homeExperience);
  expect(await page.evaluate(() => homeExperience.snapshot().intro?.duration)).toBe(page.viewportSize().width <= 700 ? 1.7 : 2.2);
  await expect(page.locator('html')).toHaveAttribute('data-intro', 'complete');
  await page.locator('#btn-agendar-hero').click();
  await expect(page).toHaveURL(/client-services\.html$/);
  await page.goBack();
  await expect(page.locator('#skip-intro')).toBeHidden();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-intro-reason', 'seen');
});

test('pular, reduced motion e falha de GSAP deixam a HOME utilizável', async ({ page }) => {
  await page.goto('/pages/index.html');
  await page.locator('#skip-intro').click();
  await expect(page.locator('#hero-title')).toBeFocused();
  await expect(page.locator('.intro-shell')).toBeHidden();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.reload();
  await expect(page.locator('#skip-intro')).toBeHidden();
  await expect(page.locator('#ritual')).toHaveClass(/ritual-static/);
  await page.route('**/gsap.min.js', route => route.abort());
  await page.reload();
  await expect(page.locator('.hero-pole svg')).toBeVisible();
  await expect(page.locator('#btn-agendar-hero')).toBeVisible();
  await expect(page.locator('.intro-shell')).toBeHidden();
});

test('catálogo vazio, erro e retry mantêm o caminho de agendamento', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.route('**/services/', route => route.fulfill({status:503,json:{detail:'Indisponível'}}));
  await page.goto('/pages/index.html');
  await expect(page.locator('#services-error')).toBeVisible();
  await expect(page.locator('#services-skeleton')).toBeHidden();
  await page.route('**/services/', route => route.fulfill({json:[]}));
  await page.locator('#btn-retry-services').click();
  await expect(page.locator('.service-empty')).toHaveText('Nenhum serviço disponível no momento.');
  await expect(page.locator('#btn-agendar-hero')).toHaveAttribute('href','client-services.html');
});

test('tamanhos intermediários preservam a composição sem overflow', async ({page}) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/pages/index.html');
  await page.waitForFunction(()=>window.homeExperience);
  await page.evaluate(()=>document.fonts.ready);
  for(const width of [320,360,700,768,860,861,900,1000,1100]) {
    await page.setViewportSize({width,height:900});
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
});

test('marca e título personalizados preservam o logo na abertura', async ({page}) => {
  await page.route('**/installation-config.mjs', async route => {
    const source=await readFile(new URL('../assets/js/installation-config.mjs',import.meta.url),'utf8');
    const body=source.replace('estrelinhaWidget: true','estrelinhaWidget: false')
      .replace('logoUrl: ""','logoUrl: "../assets/branding/editorial-test.png"')
      .replace('homeHeroTitleLead: "O clássico nunca sai de"','homeHeroTitleLead: "Seu estilo ganha"')
      .replace('homeHeroTitleAccent: "cena."','homeHeroTitleAccent: "novas histórias."');
    await route.fulfill({contentType:'text/javascript',body});
  });
  await page.route('**/editorial-test.png', async route => route.fulfill({
    contentType:'image/png',body:await readFile(new URL('../assets/images/barbershopPole-primeiro-frame.png',import.meta.url))
  }));
  await page.goto('/pages/index.html');
  await expect(page.locator('.intro-mark img')).toHaveCount(1);
  await expect(page.locator('h1')).toHaveText('Seu estilo ganha novas histórias.');
});

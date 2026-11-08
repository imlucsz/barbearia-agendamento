// Playwright MCP runner for environments without the @playwright/test CLI.
async (page) => {
  const browser = page.context().browser(), origin = 'http://127.0.0.1:4186';
  const results = [], errors = [];
  const check = (name, pass) => results.push({name, pass:Boolean(pass)});
  const hostile = '<img src=x onerror=alert(1)> Corte';
  const services = [
    {id:71,nome:'Corte de teste',descricao:'Acabamento de teste',preco:45,duracao_minutos:35},
    {id:72,nome:'Barba de teste',descricao:'Cuidado de teste',preco:30,duracao_minutos:20},
    {id:73,nome:hostile,descricao:'Descrição longa '.repeat(30),preco:80,duracao_minutos:90},
  ];
  async function setup(options = {}, init) {
    const c = await browser.newContext(options), p = await c.newPage();
    p.on('pageerror', error => errors.push(error.message));
    if (init) await p.addInitScript(init);
    await p.route('**/*', async route => {
      const u = new URL(route.request().url());
      if (u.pathname === '/services/') return route.fulfill({json:services});
      if (u.pathname === '/informacoes/') return route.fulfill({json:{endereco:'Rua de Teste, 10',telefone:'(11) 99999-0000',dias_atendimento:'Todos os dias',horario_funcionamento:'09:00 às 18:00'}});
      if (u.pathname === '/appointments/avaliacoes') return route.fulfill({json:[{nota:4,comentario:'Avaliação fictícia',oculta:false},{nota:1,comentario:'Oculta',oculta:true}]});
      if (u.pathname.endsWith('/installation-config.mjs')) {
        const response = await route.fetch();
        return route.fulfill({response,body:(await response.text()).replace('estrelinhaWidget: true','estrelinhaWidget: false')});
      }
      if (u.origin === origin && /^\/(pages|assets)\//.test(u.pathname)) return route.continue();
      return route.abort(); // No published APIs, CDN or real client data.
    });
    return {c,p};
  }
  const open = async p => {await p.goto(origin+'/pages/index.html');await p.waitForFunction(()=>window.homeExperience);};
  for (const [name,width,height] of [['desktop',1440,1000],['tablet',820,1180],['mobile',390,844],['small',320,568]]) {
    const {c,p} = await setup({viewport:{width,height}});
    try {
      await open(p);
      check(name+': intro starts', await p.evaluate(()=>document.documentElement.dataset.intro==='playing'));
      check(name+': approved duration', await p.evaluate(()=>homeExperience.snapshot().intro.duration)===(width<=700?1.7:2.2));
      await p.waitForFunction(()=>document.documentElement.dataset.intro==='complete');
      await p.evaluate(()=>document.fonts.ready);
      check(name+': local editorial font',await p.locator('h1').evaluate(e=>getComputedStyle(e).fontFamily.includes('Fraunces')));
      const geo=await p.evaluate(()=>{
        const rect=s=>document.querySelector(s).getBoundingClientRect(),pole=rect('.hero-pole'),tool=rect('.hero-tool'),copy=rect('.hero-copy');
        const overlap=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
        return {clear:!overlap(pole,copy)&&!overlap(tool,copy),overlap:overlap(pole,tool),vertical:pole.height>pole.width*2,overflow:document.documentElement.scrollWidth>innerWidth};
      });
      check(name+': restored composition and no overflow',geo.clear&&geo.overlap&&geo.vertical&&!geo.overflow);
      check(name+': all real service fields',await p.locator('#services-list').textContent().then(t=>t.includes('Corte de teste')&&t.includes('35 min')&&t.includes('45,00')));
      check(name+': hostile service stays text',await p.locator('#services-list').textContent().then(t=>t.includes(hostile))&&await p.locator('#services-list img').count()===0);
      check(name+': hidden reviews excluded',await p.locator('#review-average').textContent().then(t=>t.includes('4.0 / 5'))&&!await p.locator('#reviews-list').textContent().then(t=>t.includes('Oculta')));
      check(name+': contact link preserved',await p.locator('#phone a').getAttribute('href')==='https://wa.me/5511999990000');
      if(width<=860){
        await p.locator('#nav-toggle').click();check(name+': menu expands',await p.locator('#nav-toggle').getAttribute('aria-expanded')==='true');
        await p.locator('#main-nav a').first().focus();await p.keyboard.press('Escape');check(name+': menu Escape restores focus',await p.locator('#nav-toggle').evaluate(e=>e===document.activeElement)&&await p.locator('#nav-toggle').getAttribute('aria-expanded')==='false');
      }
      await p.locator('.service-book').first().click();
      check(name+': service booking destination',p.url().endsWith('client-services.html?service_id=71'));
      await p.goBack();await p.waitForFunction(()=>window.homeExperience);
      check(name+': return does not replay',await p.locator('#skip-intro').isHidden());
      await p.reload();await p.waitForFunction(()=>window.homeExperience);
      check(name+': reload does not replay',await p.evaluate(()=>document.documentElement.dataset.introReason==='seen'));
      // Actual video frames: non-chapter positions and reverse.
      await p.evaluate(async()=>{await document.fonts.ready;ScrollTrigger.refresh();});
      for(const progress of [.38,.66,.29]){
        await p.evaluate(v=>{const t=ScrollTrigger.getById('lab-ritual')||ScrollTrigger.getById('lab-ritual-mobile');scrollTo({top:t.start+(t.end-t.start)*v,behavior:'instant'});ScrollTrigger.update();},progress);
        await p.waitForFunction(v=>{const s=homeExperience.snapshot().ritualVideo;return s.failed||(s.readyState>=2&&!s.seeking&&Math.abs(s.presentedTime-v*10)<.2);},progress,{timeout:10000});
        check(name+': Ritual actual frame '+progress,await p.evaluate(()=>!homeExperience.snapshot().ritualVideo.failed));
      }
      const spacing=await p.evaluate(()=>{
        const active=document.querySelector(`.ritual-chapter[data-chapter="${document.documentElement.dataset.ritualStage}"]`);
        const rail=document.querySelector('.ritual-rail').getBoundingClientRect(),skip=document.querySelector('.home-skip-ritual').getBoundingClientRect();
        return {clear:!(rail.left<skip.right&&rail.right>skip.left&&rail.top<skip.bottom&&rail.bottom>skip.top),textClear:active.querySelector('.eyebrow').getBoundingClientRect().top>=document.querySelector('.site-header').getBoundingClientRect().bottom};
      });
      check(name+': Ritual controls and header clear',spacing.clear&&spacing.textClear);
      await p.locator('.home-skip-ritual').click();
      check(name+': Ritual exit reaches booking steps',p.url().endsWith('#how-it-works'));
    } catch(error) {check(name+': execution completed',false);results.push({name:name+': diagnostic',pass:false,detail:error.message.slice(0,350)});} finally {await c.close();}
  }
  for(const action of ['skip','Escape','Tab','scroll','resize','reduced']){
    const {c,p}=await setup({viewport:{width:1440,height:900}});
    try{
      await open(p);
      if(action==='skip')await p.locator('#skip-intro').click();
      else if(['Escape','Tab'].includes(action))await p.keyboard.press(action);
      else if(action==='scroll')await p.mouse.wheel(0,100);
      else if(action==='resize')await p.setViewportSize({width:390,height:844});
      else await p.emulateMedia({reducedMotion:'reduce'});
      await p.waitForFunction(()=>document.documentElement.dataset.intro==='complete');
      check(action+': intro settles',await p.locator('.intro-shell').isHidden()&&await p.locator('.hero-tool').evaluate(e=>getComputedStyle(e).opacity==='1'));
      if(action==='skip')check('skip: focus restored',await p.locator('h1').evaluate(e=>e===document.activeElement));
    }finally{await c.close();}
  }
  const {c,p}=await setup({viewport:{width:390,height:844},reducedMotion:'reduce'});
  try{
    await p.route('**/services/',r=>r.fulfill({status:503,json:{detail:'Indisponível'}}));await open(p);
    check('reduced: intro and video disabled',await p.locator('#skip-intro').isHidden()&&await p.locator('#ritual').evaluate(e=>e.classList.contains('ritual-static'))&&await p.locator('#ritual-video').getAttribute('src')===null);
    await p.locator('#services-error').waitFor({state:'visible'});check('catalog error and no skeleton',await p.locator('#services-skeleton').isHidden());
    await p.route('**/services/',r=>r.fulfill({json:[]}));await p.locator('#btn-retry-services').click();await p.locator('.service-empty').waitFor();check('retry to empty',await p.locator('.service-empty').textContent()==='Nenhum serviço disponível no momento.');
    await p.route('**/gsap.min.js',r=>r.abort());await p.reload();await p.locator('.hero-pole svg').waitFor();
    check('GSAP failure: artwork and content visible',await p.locator('.intro-shell').isHidden()&&await p.locator('#btn-agendar-hero').isVisible());
  }finally{await c.close();}
  for(const role of ['admin','cliente']){
    const {c,p}=await setup({},`localStorage.setItem('token','test-only-token');localStorage.setItem('user',JSON.stringify({role:'${role}'}));sessionStorage.setItem('barbearia.home.intro.v1','seen');`);
    try{await open(p);check(role+': existing account destination',await p.locator('#auth-area a').getAttribute('href')===(role==='admin'?'admin.html':'client-dashboard.html'));}finally{await c.close();}
  }
  const edge = await setup({reducedMotion:'reduce'});
  try {
    await open(edge.p); await edge.p.evaluate(()=>document.fonts.ready);
    for (const width of [320,360,700,768,860,861,900,1000,1100]) {
      await edge.p.setViewportSize({width,height:900});
      await edge.p.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      check('breakpoint '+width+': no overflow',await edge.p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    }
    check('font files decoded',await edge.p.evaluate(()=>document.fonts.check('16px Fraunces')&&document.fonts.check('16px HomeSpace')));
  } finally {await edge.c.close();}
  const branded=await setup({viewport:{width:390,height:844}});
  try {
    await branded.p.route('**/installation-config.mjs',async r=>{
      const response=await r.fetch();
      const body=(await response.text()).replace('estrelinhaWidget: true','estrelinhaWidget: false')
        .replace('name: "Barbearia"','name: "Ateliê do Bairro"').replace('mark: "B."','mark: "A."')
        .replace('logoUrl: ""','logoUrl: "../assets/branding/editorial-test.png"')
        .replace('homeHeroTitleLead: "O clássico nunca sai de"','homeHeroTitleLead: "Seu estilo ganha"')
        .replace('homeHeroTitleAccent: "cena."','homeHeroTitleAccent: "novas histórias."');
      return r.fulfill({response,body});
    });
    await branded.p.route('**/editorial-test.png',async r=>r.fulfill({response:await r.fetch({url:origin+'/assets/images/barbershopPole-primeiro-frame.png'})}));
    await open(branded.p);
    check('configured logo copied to opening',await branded.p.locator('.intro-mark img').count()===1);
    check('configured title preserved',await branded.p.locator('h1').textContent()==='Seu estilo ganha novas histórias.');
    await branded.p.keyboard.press('Escape');
    check('configured branding remains responsive',await branded.p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await branded.p.route('**/editorial-test.png',r=>r.abort());
    await branded.p.reload();await branded.p.waitForFunction(()=>window.homeExperience);
    await branded.p.waitForFunction(()=>document.querySelector('.intro-mark > span').textContent==='A.');
    check('failed logo uses configured mark',true);
  }finally{await branded.c.close();}
  check('no JavaScript errors',errors.length===0);
  return {browser:browser.version(),passed:results.filter(r=>r.pass).length,failed:results.filter(r=>!r.pass),total:results.length,errors};
}

# HOME Motion Integration — Contract Map

This document records the production HOME contracts before the motion integration. The motion layer must consume and decorate the existing DOM; business data, auth, links, and API behavior remain owned by their current modules.

## Page loading and ownership

`frontend/pages/index.html` loads `style.css`, `home.css`, and `home-experience.css`, then the ES modules `home.js`, `optional-features.mjs`, and `home-experience.mjs`.

- `home.js`: services, installation/business data, reviews, authentication, and functional UI behavior.
- `optional-features.mjs`: optional enhancement mounts, including the barber pole/Estrelinha feature hooks.
- `home-experience.mjs`: presentation-only reveals and ritual visual behavior. It must not replace business data or booking behavior.
- `home-experience.css`: presentation layer; must preserve existing IDs/classes used by modules and tests.

## DOM/API contracts to preserve

| Area | Contract | Behavior owner / notes |
|---|---|---|
| Navigation | `#nav-toggle`, `#main-nav`, `.main-nav--open` | Accessible mobile toggle; `aria-expanded` tracks state; links target real section anchors. |
| Authentication | `#auth-area` | `home.js` renders the current session/role actions here. |
| Hero | `#btn-agendar-hero`, `data-installation-copy` | Booking link remains `client-services.html`; installation copy stays configurable. |
| Hero decoration | `[data-barber-pole]`, `[data-estrelinha-barbeiro]` | Optional feature hooks; keep reduced-motion/fallback handling. |
| Services | `#services`, `#services-list`, `#services-skeleton`, `#services-error`, `#btn-retry-services` | Dynamic API data, skeleton, empty/error/retry states remain intact. |
| Service filters | `.filter-btn`, `[data-filter]`, `[aria-pressed]` | Preserve currently available filters and their pressed state; do not invent categories. |
| Service card | `.service-card`, `.service-book` | Keep real name, price, duration and per-service booking href (`client-services.html?service_id=<id>`). |
| Booking guide | `#how-it-works` | Existing anchor and explanatory content remain navigable. |
| Ritual | `#ritual`, `#ritual-title`, three `article` chapter elements | New video-led presentation is decorative/presentational; chapter text stays real DOM and accessible. Preserve an agreed visual hook (`.ritual-visual` or video-stage hook) for progressive enhancement and tests. |
| Business info | `#business-info`, `#address`, `#phone`, `#email`, `#operating-days` | `home.js` fills values from installation data. |
| Schedule | `#mon`, `#tue`, `#wed`, `#thu`, `#fri`, `#sat`, `#sun` | Keep weekday rows and values populated from business data. |
| Map | `#map-container`, `#map-link` | Preserve map fallback and safe external route link (`target=_blank`, `rel=noopener noreferrer`). |
| Reviews | `#reviews`, `#reviews-list`, `#review-average` | Render only real API reviews, average, loading/empty/error states; do not hardcode lab fixtures. |
| Footer/config | `#current-year`, `data-installation-copy` | Preserve year and installation-specific copy. |

## Existing verification coverage

`frontend/e2e/home-experience.spec.mjs` uses a local static server and intercepted fictitious API responses. It verifies dynamic service metadata and booking URL, real review rendering/average, map and WhatsApp links, unique IDs, mobile nav/anchors, reduced-motion visibility, no-IntersectionObserver fallback, skeleton/retry/error, and visual overflow/reveal behavior. Legacy ritual assertions that only describe the mirror implementation may be replaced by assertions for the approved video stage, but the three accessible chapter contents and fallback behavior remain required.

`frontend/e2e/essential-flows.spec.mjs` and `responsive-a11y.spec.mjs` also cover production-facing business flows and must remain compatible.

## Integration boundary

The motion module may add classes, wrappers, data attributes, and an accessible ritual media stage. It must not own service/review/business/auth data, rewrite booking destinations, remove the section IDs above, or make content depend on animation completion. Reduced motion and media failure must leave a complete, navigable page.

## Implemented composition

The production entry now uses local GSAP3.15.0 UMD resources under
assets/js/vendor/gsap (124645 bytes total, original license headers retained).
No production imports point into e2e or node_modules. No new npm installation.
home-experience.mjs owns the approved articulated-scissor intro, shared dust
ticker, SVG pole, section transitions, and lifecycle. Data/auth remain in the
unchanged home.js. Production copies of approved Ritual helpers live under
assets/js/home-motion; only the media URL changes. The WebM and poster in
assets/media/home are byte-identical to the approved Lab resources.

Dynamic service/review/business section size changes request a debounced
ScrollTrigger refresh via ResizeObserver; it disconnects on destroy.
Ritual chapter buttons delegate to the current responsive controller. Mobile
titles are offset below the real product header; desktop preserves the film
stage and left typography. Reduced motion keeps the poster and all three texts.

The added runtime reports its own consumers only. Existing Estrelinha WebGL and
RAF work is independent and must not be mistaken for the cinematic subsystem's
counts. No new Three.js context is introduced by this integration. The previous
barber-pole/Estrelinha hooks remain present.

Preexisting HOME presentation files were backed up under
frontend/e2e/motion-lab/artifacts/home-before before adaptation. No reset, commit,
push or deploy. Browser screenshots with fictitious API fixtures are saved under
frontend/e2e/motion-lab/artifacts/integration-desktop-* and integration-mobile-*;
fixtures are not embedded in production. The implementation does not change
Python/API/database code. Existing frontend E2E flows also ran against their
own migrated temporary SQLite database and isolated test API; no development
or production database was used. Python unit suites were not needed for this
presentation-only implementation.

## Final validation

- Baseline: Node26/26 and original HOME desktop9/9 before production adaptation.
- Final Node suite:26/26. Final HOME experience suite:44/44 across desktop,
  tablet, mobile and small, including Enter/Space on touch-emulated profiles.
- The base stylesheet's smooth scroll conflicted with ScrollTrigger's native
  setters/focus. `html.experience-ready` now uses `scroll-behavior:auto`. The
  legacy essential-flow assertion for smooth scrolling was updated accordingly;
  menu, anchor placement, reduced-motion and contact assertions were preserved.
- Full existing frontend E2E attempt:59/63 passed. One obsolete smooth-scroll
  expectation was corrected and its mobile test then passed1/1. The remaining
  three Firefox cases crashed at `browserContext.newPage`, before application
  code. A standalone Firefox `about:blank` probe reproduced `Target crashed`.
  Chromium and WebKit responsive/accessibility cases passed. This environment
  cannot establish Firefox compatibility; no browser dependencies were changed.
- Twelve target viewport sizes were checked without document horizontal
  overflow/pageerrors; JSON evidence: test-results/home-motion-viewport-matrix.json.
- `git diff --check`: only preexisting AGENTS.md:29 trailing whitespace.
  NO_COLOR/FORCE_COLOR runner warnings are unrelated to browser functionality.
- Final isolated Lab regressions: video-checks.mjs18/18; checks.mjs17/17.
- Final manual matrix repeated all12 requested sizes, activating TÉCNICA through
  the actual chapter control; no document overflow. Updated screenshots were
  inspected for hero, all three Ritual states and mobile composition. The
  browser console on that normal navigation reported0 errors and0 warnings.

## Resultado

**B — INTEGRADA COM RESSALVAS.** A integração está implementada e os testes da
HOME, Node, Chromium/WebKit e Motion Lab não demonstraram regressão funcional
remanescente. A ressalva é a validação Firefox, indisponível neste ambiente:
o navegador também falhou ao abrir about:blank. Não houve commit, push ou deploy.

Capturas finais (dados fictícios apenas nas rotas de teste):

- Hero: `frontend/e2e/motion-lab/artifacts/integration-desktop-hero.png`.
- Serviços/como agendar/localização/avaliações/CTA/footer: mesmo diretório,
  `integration-desktop-{services,how,business,reviews,cta,footer}.png`.
- Ritual PREPARO/TÉCNICA/ACABAMENTO: `integration-desktop-ritual-{0,1,2}.png`.
- Mobile: `integration-mobile-{hero,services,ritual,cta}.png`.
- Desktop capturado em1440×900; mobile em390×844. A matriz também cobriu
  1920×1080,1600×900,1366×768,1280×720,393×873,412×915,360×800,
  768×1024,820×1180 e1024×768. Não houve teste em aparelhos físicos.

## Ritual contínuo universal — 2026-11-03

A causa confirmada pelo usuário era a seleção responsiva dos três stills,
inclusive por altura abaixo de 650px. `ritual-video.mjs:synchronize()` agora
envia `timeline.progress()` a `seeker.seekProgress()` em qualquer layout.
`snapshot().mode` retorna `continuous-scrub` com movimento normal e `poster`
com reduced-motion. Não existe escolha de semântica por UA, largura ou altura.
Falhas reais de mídia preservam a recuperação estática existente.

Fluxo: scroll → ScrollTrigger → timeline (scrub .16 no pin desktop, direto no
sticky compacto) → progresso 0..1 → `progressToTime()` (24fps, último frame em
9,958s) → fila de último destino do seeker → `currentTime` quando não há seek
em curso → seeked/rVFC → frame apresentado e capítulo HTML correspondente.
O seeker, seus timeouts/cleanup e o asset permanecem intactos. O WebM da HOME
continua idêntico ao do Lab (SHA256
`D0D4C23E395A11B7E90D905255AFE993C408440AB6CB3B024D4D802489723BA4`).
São VP9/1280×720/24fps/10s, GOP6, 40 keyframes; não houve recodificação.

Largura ≥1000px e altura ≥650px ainda escolhem **apresentação** com pin GSAP;
as demais usam palco CSS sticky e corredor de 310svh (310vh como fallback),
aproximadamente 210svh de percurso. Portrait preserva crop, máscara e textos
aprovados. Landscape curto reserva espaço para o header, enquadra o filme
completo na área disponível e separa texto da régua. As coordenadas dos cortes
2,5s/7,75s e destinos dos botões 1,25s/5,25s/9,25s não mudaram; esses destinos
são atalhos de navegação, não quantização do scrub. Reduced-motion continua
sem src de vídeo, sem pin/corredor, com poster e todos os capítulos legíveis.

### Investigação touch e testes

- Os dois casos 390×844 que falhavam por uma asserção de largura passaram
  após considerar a máscara aprovada, em Chrome e Edge.
- Edge tablet: uma repetição isolada e depois cinco repetições passaram. Um
  lote anterior teve 4/5 por ausência de callback do primeiro frame; preparação
  agora espera mídia/visibilidade e estabilização inicial de layout.
- `node frontend/e2e/ritual-touch-probe.mjs`: 12 gestos nativos, todos terminaram
  em target/current/presented = 2,5s. Um seek ainda estava em curso na primeira
  amostra e concluiu cerca de 120ms depois. Zero writes durante seeking.
- O desvio histórico de ~0,33s após touch não foi reproduzido como divergência
  persistente do seeker. Inércia é uma hipótese para esse registro antigo,
  não causa comprovada. O teste agora espera estabilidade do scroll e verifica
  currentTime versus alvo real antes de reposicionar.
- Uma corrida de resize foi comprovada: o teste calculou 50% antes do refresh,
  mas o layout final solicitou ~73,1%; vídeo/current/presented convergiram
  corretamente para 7,333s. Ajustado somente o teste, esperando limites de
  ScrollTrigger/viewport/scrollY estáveis. Nenhuma mudança no seeker.
- Matriz com touch/mobile: 22/22 Chrome/Edge aprovados novamente após o ajuste
  visual final de landscape (`ritual-final-verified/`). Tempos
  0/12/25/38/50/63/75/88/100%, tolerância 0,15s,
  eventos rVFC, reverso, resize, reduced-motion, saída e zero writes concorrentes.
  Dimensões: 1440×900,1366×768,1440×640,1366×640,1280×600,820×1180,
  390×844,375×812,360×800,320×568,844×390 em ambos os canais instalados.
- Firefox: ambos os cenários falham em `newPage: Target crashed`. Reproduzido
  com uma página about:blank, sem aplicação. Compatibilidade não demonstrada.
- WebKit Windows: ambos os cenários falham antes de scrub com media-error-4,
  readyState0 e duração NaN. Reproduzido com o mesmo asset em um elemento video
  isolado, sem GSAP/HOME, embora canPlayType declare `probably`. Não se alterou
  codec nem se ignoraram os testes. Esse ambiente não valida Safari real.
- WebKit fallback/reduced-motion: 4/4 aprovados em 1440×900 e 390×844. Isso
  confirma poster e capítulos acessíveis, não suporte ao scrub do asset.
- Node frontend: 27/27 aprovados. Testes Python/SQLite/PostgreSQL não executados:
  mudança exclusiva de apresentação, servidores estáticos e API fictícia
  interceptada; nenhum banco iniciado ou alterado.
- HOME existente (`--grep-invert "Ritual universal"`): 44/44 aprovados. Revisão
  compacta posterior ao ajuste visual, em 1440×640/1280×600/844×390 Chrome/Edge:
  6/6, com asserções de etiqueta abaixo do header e parágrafo acima da régua.
- Probe final Chrome/Edge, 1440×900/640: writes/seeked 312/312,241/241,
  335/335,241/241; rVFC 307,241,327,241. Zero writes durante seeking, zero
  dropped/corrupted reportados, nenhum pageerror; D3D11VideoDecoder de plataforma.
  Lacunas entre callbacks não são contadas como dropped frames. Esses números
  são de automação local, não benchmark de FPS ou prova de performance mobile.

### Arquivos e reprodução

- Runtime: `frontend/assets/js/home-motion/ritual-video.mjs` e
  `frontend/assets/css/home-ritual.css`.
- Testes: `frontend/e2e/home-experience.spec.mjs`,
  `frontend/e2e/ritual-continuous.config.mjs` e novo
  `frontend/e2e/ritual-touch-probe.mjs`. Os dois arquivos `ritual-diagnostics.*`
  da etapa diagnóstica continuam preservados.
- Contratos/documentação: `specs/home-experience.md`, este relatório,
  `docs/RITUAL_CROSS_BROWSER_DIAGNOSTICO.md`, `docs/REQUISITOS_STATUS.md`,
  `docs/superpowers/plans/2026-11-02-ritual-continuo.md` e `README.md`.
- Grafo: artefatos de `graphify-out/` atualizados por AST, sem LLM/API.
  11.385 nós, 23.311 arestas, 601 comunidades; HTML agregado. O CLI alertou
  sobre 22 arquivos sem símbolos e nomes de comunidades desatualizados;
  não se acionou rotulação semântica paga nem se reconstruiu documentação via LLM.

Comandos executados a partir da raiz (prefixo operacional local `rtk proxy`):

```powershell
node --test "frontend/tests/*.test.mjs"
node node_modules/@playwright/test/cli.js test --config=frontend/e2e/home-experience.config.mjs --grep-invert "Ritual universal" --output=test-results/home-experience-final
node node_modules/@playwright/test/cli.js test --config=frontend/e2e/ritual-continuous.config.mjs --project="chrome-*" --project="msedge-*" --output=test-results/ritual-final-verified
node frontend/e2e/ritual-touch-probe.mjs
node frontend/e2e/ritual-diagnostics.mjs
node node_modules/@playwright/test/cli.js test --config=test-results/ritual-webkit-fallback.config.mjs
git diff --check
graphify update .
```

A tentativa sem filtro de projetos executou os 26 cenários e retornou código1
pelas quatro falhas ambientais Firefox/WebKit descritas acima. Não foi registrada
como aprovação cross-browser completa. Syntax checks Node e whitespace dos
arquivos novos também foram conferidos. A revisão visual cobriu desktop, baixo,
portrait 390/320 e landscape, nos três capítulos; sem overflow nem texto sobre
header/régua após a adaptação compacta.
O config auxiliar de WebKit em `test-results/` troca somente o filtro de testes
para reduced-motion/falha de mídia; não integra o build ou o código de produção.

Evidências locais: `test-results/ritual-final/`, `ritual-touch-final/`,
`ritual-touch-probe.json` e `ritual-diagnostics.json`. Capturas incluem a viewport
no nome para não serem sobrescritas pelo resize. Instrumentação e probes ficam
somente em `frontend/e2e/`, sem importação pela HOME ou inclusão no build estático.
Dispositivos físicos, barras móveis dinâmicas e aceleração on/off permanecem
fora da evidência automatizada. Não houve commit, push ou deploy.

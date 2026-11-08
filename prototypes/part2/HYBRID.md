# A híbrida — a identidade permanece, a composição evolui

**Atualização:** direção aprovada pelo usuário e integrada localmente à HOME funcional. [Relatório da integração](../../docs/HOME_EDITORIAL_INTEGRATION.md). O restante deste documento registra a validação histórica do protótipo, que permanece disponível para comparação.

Pedido de 7 de novembro de 2026: combinar a direção A com a identidade tradicional já construída e a animação de scroll. **Prévia para nova avaliação visual; não é integração definitiva.**

Abra [a-hybrid.html](http://127.0.0.1:4194/a-hybrid.html) depois de executar `rtk proxy python -u prototypes/part2/serve.py` neste worktree. A galeria no mesmo endereço oferece acesso à híbrida e às três alternativas originais.

## O que foi preservado

- Marca B., “Estilo com atitude”, frase “O clássico nunca sai de cena” e textos já existentes.
- Paleta real de `frontend/assets/css/installation.css`: fundo quente escuro, texto marfim e acento dourado. Nesta direção, a paleta tem continuidade com a identidade que o usuário confirmou querer preservar.
- Ilustrações SVG originais, sem moldura: poste vertical grande à direita e tesoura diagonal sobre a parte inferior, com transparência, proporções, gradientes e articulação preservados.
- Ritual: mesmo WebM, poster, `createVideoRitual`, `createVideoSeeker`, GSAP e pontos narrativos PREPARO / TÉCNICA / ACABAMENTO. Avanço **contínuo e reversível**, também no mobile. Não substituído por três imagens.
- Estrelinha original em um cameo decorativo após a hero, sem chatbot, controles ou bloqueio de navegação.

## O que veio de Entrelinhas

- Tipografia Fraunces e relação de escala entre título, legenda e texto funcional.
- Tipografia, espaçamento, cores, botões e hierarquia editorial da Hero.
- Catálogo assimétrico numa seção clara de papel quente; alternância intencional com a abertura escura e o Ritual cinematográfico.
- CTA direto e saída “Ir para o agendamento” no Ritual, evitando obrigar o visitante a concluir a narrativa.

Não se carregam catálogo, dados institucionais ou avaliações reais. Os serviços são amostras identificadas e os CTAs encerram no modal de prévia. A intro original foi recuperada e adaptada ao DOM desta comparação; o código da aplicação permanece intacto.

## Restauração da Hero e da intro

Referência recuperada do Git: **`3aa7a80`**, `frontend/assets/js/home-experience.mjs` e `frontend/assets/css/home-experience.css`. A moldura retangular e o arco pertenciam à prévia híbrida, não à composição original. A prévia inicial reutilizava apenas o controlador do Ritual; não inicializava a intro, cujo controlador completo depende de outros elementos da HOME. Não foi encontrada uma regressão no código de produção.

`assets/hero-intro.mjs` adapta somente a abertura ao DOM da prévia, reutilizando o GSAP existente. Tesoura articulada, corte central, cortinas laterais, entrada do poste e revelação discreta das linhas: **2,2 s desktop / 1,7 s mobile**, usando transform/opacity e easing nativo. Sem nova dependência ou animação global.

A chave original **`barbearia.home.intro.v1 = seen`** permanece em `sessionStorage`, registrada no início para evitar repetição após saída rápida, retorno interno ou reload. É apenas estado de apresentação por sessão da aba, sem dados pessoais. Links com fragmento e posição de scroll restaurada não recebem abertura. Se o navegador bloquear armazenamento, a página funciona, mas não há garantia de persistência dessa preferência entre documentos.

“Pular abertura”, Escape, Tab, interação, scroll, resize, aba oculta e ativação de reduced motion encerram a sequência e restauram a pose final. O foco em “Pular” retorna ao título quando o botão é acionado. `prefers-reduced-motion` inicial evita a intro; falha do GSAP deixa conteúdo e ilustrações visíveis. Um limite de 3 s evita que uma animação interrompida retenha a cortina.

Validação direcionada reproduzível em `tests/hero-intro.browser.js`: antes da mudança, **5 verificações passaram e 10 falharam** (intro ausente); depois, **49/49 aprovadas**, sem erros JavaScript. Inclui primeira visita desktop/mobile, geometria e sobreposição das ilustrações, CTA livre, larguras 320/390/768/844/1440, navegação/reload, cancelamento, foco, reduced motion, âncora e falha da dependência. A suíte existente `tests/hybrid.browser.js` continua **39/39**, incluindo scrub contínuo/reversível, menu/modal e fallback. Node **6/6**; syntax checks dos dois módulos e `git diff --check` aprovados. Nenhum teste ignorado nessas execuções.

Capturas reais da composição restaurada: [desktop](screenshots/hybrid-restored-desktop-hero.png), [mobile](screenshots/hybrid-restored-mobile-hero.png) e [abertura em andamento](screenshots/hybrid-restored-intro.png). As capturas anteriores abaixo são preservadas para comparação.

## Reutilização e isolamento

O servidor `serve.py` vincula somente `127.0.0.1:4194`, aceita leitura de arquivos autorizados, não lista diretórios e não expõe API ou `.env`. Assets compartilhados são entregues sem modificar seus bytes. Não carrega configuração de banco nem backend. Respostas recebem `no-store`; o vídeo suporta HTTP Range, necessário para seek confiável no Chromium.

Three.js usa o pacote **0.187.0 já instalado** no Motion Lab local, somente por leitura. A HOME existente aponta para 0.186.0 via CDN; essa diferença é específica desta prévia e não altera a dependência da aplicação. Não se instalou pacote nem se fez solicitação à CDN. Se o pacote/WebGL não estiver disponível, apenas o cameo fica ausente. Os demais elementos continuam funcionais.

CSP mantém conexões de dados e envio de formulários bloqueados. O import map estático tem hash SHA-256; scripts, fontes, imagens e vídeo são locais. A página reutiliza apenas módulos de apresentação, sem `home.js`, autenticação ou chamadas à API.

## Evidências

| Captura real | Desktop 1440 × 1000 | Mobile 390 × 844 |
|---|---|---|
| Hero | [Abrir](captures/hybrid-desktop-hero.png) | [Abrir](captures/hybrid-mobile-hero.png) |
| Catálogo | [Abrir](captures/hybrid-desktop-catalog.png) | [Abrir](captures/hybrid-mobile-catalog.png) |
| Ritual — Técnica | [Abrir](captures/hybrid-desktop-ritual.png) | [Abrir](captures/hybrid-mobile-ritual.png) |

- Chromium **156.0.8078.48**: **39 verificações aprovadas**, zero falhas finais. Runner reproduzível: `tests/hybrid.browser.js` via Playwright MCP.
- Capítulos em **1,25 s / 5,25 s / 9,25 s**, seguidos de retorno ao primeiro; scroll intermediário em **38% / 66% / 29%**. Quadros apresentados acompanharam as posições dentro da tolerância de 0,2 s. Número de seeks limitado pelo teste, sem ciclo contínuo adicional no controlador de vídeo.
- Desktop/mobile, 320 px sem overflow, navegação, CTA, retorno de foco, mascot renderizada, caminho direto ao agendamento. Controles de capítulos e saída separados mesmo em 320 px.
- Reduced motion: poster, três textos legíveis e nenhum download do WebM. Falha de vídeo provocada: textos e CTA permanecem utilizáveis.
- Sem erros JavaScript ou requisições externas/API nos cenários normais.
- Node: **6 aprovados**, zero falhos/ignorados (`node --test prototypes/part2/tests/prototypes.test.mjs`).
- Python: **5 aprovados**, zero falhos/ignorados, para isolamento do servidor, métodos, integridade dos assets e respostas de Range (`python -m unittest discover -s prototypes/part2/tests -p test_preview_server.py -v`). O sandbox inicialmente bloqueou sockets locais; a execução autorizada fora dele passou.
- `node --check prototypes/part2/assets/hybrid.mjs` e `git diff --check` aprovados.

O primeiro teste do scrub revelou que o servidor estático básico não suportava Range: o vídeo recebia metadados, mas não avançava corretamente. A correção foi feita apenas no servidor da prévia; o controlador da aplicação foi preservado. As novas capturas mostram o frame e o capítulo TÉCNICA efetivamente alcançados.

Limites: navegador emulado, sem teste em aparelho físico ou Safari/Firefox; o pacote 3D local tem a diferença de versão indicada acima. Nenhum teste de produção, API, banco, calendário ou fluxo real de reserva foi realizado nesta alteração estritamente visual.

**Estado: aguardando aprovação visual da combinação.** Sem commit, push, merge, deploy ou alterações em `frontend/` e `backend/`.

# HOME editorial — integração local aprovada

Em 7 de novembro de 2026, o usuário aprovou a A híbrida e sua Hero/intro restauradas. Implementação no worktree `.worktrees/ux-art-direction-part2`, branch `design/ux-art-direction-part2`, base `19cfa2738fb30f81339f1dfc472b99b139a6b7bb`. **Aplicada à HOME funcional, ainda sem commit, publicação ou integração à main.**

## O que foi integrado

- Tipografia Fraunces/HomeSpace e composição editorial aprovada; fontes locais existentes no protótipo, com licenças OFL. Os dois arquivos somam 497.116 bytes, sem nova dependência ou requisição a provedor de fontes.
- Hero sem moldura, poste SVG vertical e tesoura articulada diagonal, mesmos assets e proporções. Botões reais de agendamento e exploração de serviços preservados.
- Intro de 2,2 s desktop / 1,7 s até 700 px, com transform/opacity, regra original `barbearia.home.intro.v1` por sessão, skip/Escape/Tab/interação, reduced motion e limite de execução. A marca configurável, inclusive logo e fallback, é reutilizada.
- Catálogo assimétrico claro alimentado por `home.js`: nomes, descrições, preços, duração e links com `service_id` continuam vindo da API. Iniciais decorativas são texto. Estados vazio, carregando, erro e retry continuam disponíveis.
- Ritual original, contínuo/reversível e com mesma mídia/controlador, mais saída direta para os passos do agendamento. Contatos, mapa, avaliações, destino da área autenticada e marca por instalação preservados. CSS restrito à HOME; demais telas e o calendário da Parte 1 não foram redesenhados.

`home-experience.mjs` passou a usar `home-motion/intro.mjs`, extraído da abertura aprovada. A montagem de SVG ocorre antes do carregamento de GSAP: falha da dependência mantém ilustrações e CTAs. O vídeo conserva seu gerenciamento de resize e de mudanças de conteúdo; retorno por bfcache mantém o controlador e recalcula o layout. Não há importação de `prototypes/` no produto.

O título padrão recebe as três linhas aprovadas após o branding. Textos diferentes configurados pela instalação são preservados, com quebra natural. Nenhum dado de usuário é interpretado como HTML nessa alteração.

## Validação efetivamente executada

| Verificação | Resultado |
|---|---|
| Chromium 156.0.8078.48, `frontend/e2e/home-editorial.browser.js` via Playwright MCP | **98 aprovadas**, zero falhas finais/ignoradas e zero erros JavaScript |
| `rtk proxy node --test frontend/tests` | **57 aprovados**, zero falhos/ignorados, incluindo calendário, sessão e empacotamento dos novos assets |
| `test_same_origin_frontend.py`, Python do venv existente, `BOOKING_TEST_BACKEND=sqlite` | **7 aprovados**, zero falhos/ignorados; SQLite temporário exclusivo |
| Syntax checks dos módulos alterados e novos; `git diff --check` | Aprovados |

Chromium: 1440×1000, 820×1180, 390×844, 320×568 e transições em 320/360/700/768/860/861/900/1000/1100 px. Dados de API fictícios interceptados; nenhuma requisição a ambiente publicado. Verificados: fonte decodificada, geometria, CTAs, conteúdo hostil renderizado como texto, catálogo real versus modal de prévia, avaliações ocultas, telefone, navegação mobile/Escape, destinos de cliente/admin, voltar/reload, intro interrompida, reduced motion, erro/vazio/retry, falha de GSAP, marca/logo customizados e fallback.

Ritual: frames efetivamente apresentados em 38%, 66% e retorno a 29%, tolerância de 0,2 s; controles e texto sem sobreposição com o header. Screenshots de Hero, catálogo, contatos, CTA final e Ritual foram capturados e inspecionados em desktop/mobile, em `test-results/home-editorial-final-*`. Captura anterior: `test-results/home-editorial-before.png`. São evidências locais ignoradas pelo Git, não requisitos do build. Os registros de apresentação contêm somente dados fictícios.

Verificação adicional da Estrelinha com a flag habilitada e **Three.js 0.186.0 original**: canvas renderizado, três pontos de aparição preservados e zero erros JavaScript. Somente os dois módulos públicos já usados pelo projeto foram carregados da CDN; APIs permaneceram interceptadas com dados fictícios. Captura: `test-results/home-editorial-mascot.png`. A transição textual do Ritual também foi conferida após estabilizar: em 50%, somente TÉCNICA está visível.

Antes da integração, as duas verificações de fonte aprovada e duração da intro falharam na HOME antiga. A inspeção adicional detectou overflow da tesoura em larguras específicas: posição e largura máxima mobile ajustadas, com regressão. A revisão independente detectou o logo customizado ausente na intro; agora ele é clonado da marca validada e recebe fallback determinístico.

O sandbox inicialmente impediu acesso do navegador ao servidor local e criação do SQLite temporário; ambos foram executados fora dele com autorização. A primeira tentativa Python teve sete erros de ambiente (`unable to open database file`), resolvidos na repetição autorizada, sem mudança de código. A CLI `@playwright/test` não está instalada; sua execução não foi alegada. `home-editorial.spec.mjs` e configuração foram persistidos para CI; o runner MCP executou a cobertura acima sem instalar pacotes. A suíte Playwright histórica completa e PostgreSQL não foram executados nesta integração de apresentação.

## Build, segurança e implantação

O teste de build comprova que HTML, CSS, módulo, fontes e licenças são copiados preservando bytes. O FastAPI já monta `/assets` inteiro; não foi necessária mudança no servidor. Headers/CSP, política de cache, origem única, autenticação, APIs, schema e Render não foram alterados. Os testes existentes confirmam publicação de arquivos públicos, métodos, isolamento e `no-store`.

Publicação ainda exige a revisão/integração Git e o rollout coordenado já documentado para origem única. Não houve commit, push, merge, PR, deploy ou mudança de configuração externa nesta tarefa. Safari/Firefox, aparelhos físicos e comportamento em ambiente publicado permanecem pendentes. Os testes locais de apresentação não equivalem a reserva real ou validação de produção.

## Arquivos

- Produto: `frontend/pages/index.html`, `frontend/assets/js/home.js`, `home-experience.mjs`, novo `home-motion/intro.mjs`, novo `frontend/assets/css/home-editorial.css`, quatro arquivos de fontes/licenças em `frontend/assets/fonts/`.
- Regressões: `frontend/e2e/home-editorial.browser.js`, `home-editorial.spec.mjs`, `home-editorial.config.mjs`, `frontend/tests/home-editorial-build.test.mjs`.
- Documentação: este relatório, README, requisitos/status e plano curto. Protótipos anteriores e arquivos locais preservados; Graphify atualizado apenas por AST neste worktree.

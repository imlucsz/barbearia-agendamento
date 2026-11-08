# Integração da HOME editorial aprovada

**Objetivo:** aplicar à HOME funcional a direção A híbrida aprovada pelo usuário, com a Hero e intro restauradas. Especificação visual: `prototypes/part2/HYBRID.md` e capturas `hybrid-restored-*`.

**Arquitetura:** HTML e CSS exclusivos da HOME, fontes locais já licenciadas no protótipo e um módulo de intro extraído da versão aprovada. Reutilizar `home.js`, dados/links do catálogo, branding por instalação, Ritual e Estrelinha. Não importar arquivos de `prototypes/` no produto. Alternativa descartada: substituir a HOME pelo HTML de demonstração, pois perderia dados e fluxos reais.

**Limites:** sem backend, contratos, autenticação, calendário, migração, dependência nova ou publicação; preservar o trabalho local. A aprovação visual autoriza a integração local, sem commit/push/deploy.

- [x] Teste de navegador antes da implementação: fonte/layout aprovados e intro 2,2/1,7 s; duas falhas esperadas confirmadas.
- [x] Integrar `frontend/pages/index.html`, CSS isolado `home-editorial.css`, fontes/licenças e `home-motion/intro.mjs`; manter seletores de `home.js` e diagnóstico `homeExperience`.
- [x] Preservar identidade configurável, estados de erro/vazio, conteúdo longo e texto hostil sem interpretação HTML, navegação interna, redução de movimento e CTAs.
- [x] Chromium 98/98; Node 57/57, incluindo build; publicação Python/SQLite temporário 7/7. Capturas inspecionadas. CLI Playwright indisponível, validado via MCP. PG não exigido: nenhuma mudança em persistência ou regras.
- [x] Revisão independente e correção do logo customizado; Graphify AST, `git diff --check`, documentação e estado Git final.

Foco de revisão: texto de instalação customizado; catálogos com 0/1/muitos serviços; retorno pelo histórico; movimento reduzido/falha de módulo; header e controles em 320 px. Testes de apresentação usam apenas respostas fictícias interceptadas e servidor local de arquivos.

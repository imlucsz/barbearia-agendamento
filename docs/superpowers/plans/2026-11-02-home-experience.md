# Home editorial com ritual visual

**Objetivo:** evoluir a apresentação da home preservando identidade, hooks, dados e agendamento.
**Arquitetura:** HTML semântico e visível por padrão; CSS específico; módulo ES independente, sem API, autenticação, Canvas ou bibliotecas. Implementação no workspace atual, em blocos conforme autorização do usuário. Sem commit/staging/deploy.
**Especificação:** pedido do usuário nesta sessão, blocos A–E e relatório de análise aprovado.

## Plano e validação

- [x] A — Inserir Ritual linear, transição e CTA real em `frontend/pages/index.html`; conferir estrutura e destinos.
- [x] B — Criar `frontend/assets/css/home-experience.css`: espelho abstrato em CSS, etapas, CTA e responsividade desde 320px; validar no navegador.
- [x] C — Criar `frontend/assets/js/home-experience.mjs`: reveals uma vez por Web Animations, sem ocultação persistente; entrada do hero em até 1200ms e luz com RAF somente sob demanda. Testar falha/ausência de APIs e preferências.
- [x] D — No desktop capaz, manter apenas o visual do Ritual sticky enquanto os três textos seguem no fluxo; observer escolhe estado. Mobile/reduced-motion permanecem lineares. Testar redimensionamento e alteração de preferência em sessão.
- [x] E — Refinar microinterações em CSS, sem tocar em `home.js`, widget ou mapa; testar catálogo/erro/retry/skeleton, contatos e avaliações com fixtures fictícias.
- [x] Fechamento — Node, Playwright em desktop/tablet/mobile e reduced-motion; revisão independente; orçamento gzip, diff, hashes protegidos, Graphify e documentação.

## Riscos de revisão

- Conteúdo dinâmico após observer: observar apenas blocos estáveis, cards usam CSS sem nova dependência.
- JavaScript ou IntersectionObserver indisponível: conteúdo e links continuam visíveis.
- Reduced-motion alterado durante sessão: cancelar animações, limpar transforms e sticky.
- Mobile baixo: texto e CTA antes da arte; nada fixo cobrindo controles.
- Mapa e widget: nenhum ancestor transformado, nenhum novo contexto gráfico, nenhum controle comercial interceptado.

## Encerramento dos blocos

A–E concluídos. Estrutura e destinos conferidos inicialmente no desktop e em 320px; camada estática seguida de movimento. Node 26/26 e Playwright 36/36 aprovados. Revisão independente sem achados críticos/importantes; possível clipping do espelho descartado por inspeção e medição em 320px. Correção da faixa vertical do observer validada pelo teste que falhou antes. Nenhuma mudança nos módulos comerciais ou widget.

## Evidência

Será registrada em `docs/REQUISITOS_STATUS.md` após execução. Testes da home usam servidor estático e interceptação dos endpoints: sem tocar em banco ou executar migrations.

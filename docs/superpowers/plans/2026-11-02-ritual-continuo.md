# Ritual contínuo em todas as viewports

Decisão aprovada pelo usuário: remover seleção de stills responsivos; somente
reduced-motion mantém alternativa estática. Sem alterações no seeker/asset.

1. Regressão E2E primeiro: tempos intermediários e frames reais em desktop baixo,
   portrait/landscape, Chrome/Edge; reduced-motion, reverse, resize e saída.
2. Enviar timeline.progress ao seeker em qualquer layout. Preservar desktop pin
   e mobile sticky/crop/textos existentes; alongar corredor compacto se necessário.
3. Rodar matriz, instrumentação de seeks e inspeção visual; ajustar só Ritual.
4. Atualizar contratos/documentação e Graphify; diff check, sem publicação/banco.

Critérios: 0/12/25/38/50/63/75/88/100% convergem ao vídeo (±0.15s), inclusive
reverso; zero writes durante seeking, múltiplos frames via rVFC; reduced sem src;
sem overflow, próximo conteúdo alcançável e resize sem pin residual.

Fechamento — 2026-11-03:

- [x] Implementação contínua universal e reduced-motion estático; seeker/asset intactos.
- [x] Regressão RED no modo segmentado antes da implementação; matriz final Chrome/Edge 22/22.
- [x] Mobile touch, reverso, tempos intermediários/rVFC, resize e saída; 12 gestos Edge isolados convergentes, zero writes concorrentes.
- [x] Revisão visual: pequeno ajuste de composição landscape/desktop baixo para header e régua; regressão compacta 6/6, HOME 44/44, Node 27/27.
- [x] Firefox/WebKit executados: 4 falhas ambientais, reproduzidas sem HOME; compatibilidade de scrub pendente nesses motores. Sem recodificação/fallback por UA.
- [x] Contratos/documentação e Graphify AST atualizados. Sem publicação ou banco.

Evidências e comandos: `docs/HOME_MOTION_INTEGRATION.md`, seção Ritual contínuo universal.

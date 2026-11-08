# Validação dos protótipos — 7 de novembro de 2026

Branch `design/ux-art-direction-part2`, base `19cfa2738fb30f81339f1dfc472b99b139a6b7bb`. Worktree exclusivo `.worktrees/ux-art-direction-part2`. Nenhuma alteração em `frontend/`, backend, migrações, configuração Render ou outros worktrees.

## Execuções reais

| Verificação | Resultado |
|---|---|
| `node --check prototypes/part2/assets/prototype.js` | Aprovado |
| `node --test prototypes/part2/tests/prototypes.test.mjs` | 5 aprovados; 0 falhos; 0 ignorados |
| `tests/qa.browser.js` via Playwright MCP | 109 verificações aprovadas; 0 falhas finais; Chromium **156.0.8078.48** |
| `git diff --check` | Sem erros |
| Inspeção visual | A/B/C em desktop 1440 × 1000 e mobile 390 × 844; seis capturas completas e galeria comparativa |
| Contraste de textos visíveis, cálculo RGB no DOM a 390 px | A: 42 elementos, B: 44, C: 40; nenhum abaixo de 4,5:1 (normal) ou 3:1 (grande) |
| Revisão independente de código, somente leitura | Sem achados concretos no isolamento, CSP, DOM e interações; não substitui as verificações de navegador do agente principal |

Os comandos acima foram executados com prefixo `rtk proxy`. O servidor estático foi iniciado no loopback, expondo somente `prototypes/part2/`. Nenhuma API ou banco foi iniciado.

## Cobertura do Chromium

- Larguras **320, 390, 768 e 1440 px** em todas as direções: sem rolagem horizontal; um `h1`; controles visíveis com altura de pelo menos 44 px.
- Todos os CTAs de agendamento abrem o modal identificado e deixam claro que não foi criada uma reserva. Escape e fechamento explícito funcionam; o foco retorna ao acionador.
- Menu mobile: Enter, Escape e navegação por âncora. Modal: ciclo de Tab e Shift+Tab.
- B: seleção por setas no rádio nativo, atualização do resumo e preservação do serviço escolhido na prévia.
- C: composição Aberta/Compacta, estado `aria-pressed` e funcionamento com `prefers-reduced-motion: reduce`; transição e scroll suave desativados nessa preferência.
- Sem erro de JavaScript/CSP, requisição externa, método de escrita, cookie ou armazenamento no contexto limpo usado pelo teste.
- Fontes locais realmente carregadas: Space Grotesk em todas as direções; Fraunces em A. Nenhuma requisição a Google Fonts em runtime.

## Problemas encontrados e corrigidos durante a verificação

1. As variáveis de cor por direção estavam no `body`, mas fundo/cor eram herdados de `:root`. Corrigido o escopo efetivo de aplicação; novas capturas confirmam as três paletas.
2. No Chromium desta execução, Tab após o último botão do modal nativo passava por `BODY`. Reproduzido, implementado ciclo explícito entre os controles e acrescentada regressão de Shift+Tab. Os três cenários passaram depois.
3. O primeiro rerun reutilizou cache de assets do contexto de pesquisa. O runner agora cria e encerra um contexto limpo próprio, sem depender da sessão ou de cookies anteriores. Resultado final: 109/109.

Uma chamada inicial ao runner também encontrou ponto-e-vírgula incompatível com a expressão de função exigida pelo MCP; corrigido no arquivo reproduzível. Isso não foi erro de navegação do produto.

## Performance e escopo

- JavaScript de interação: cerca de **2,7 kB**, sem biblioteca adicional. Fontes TTF locais somam aproximadamente **497 kB**; somente A usa as duas famílias na composição. Assets de código + fontes abaixo de 530 kB por alternativa, sem fotos ou vídeo.
- Sem loop de animação, canvas, WebGL ou observador de scroll. A escultura muda por `transform` sob comando.
- Tempos locais de DOMContentLoaded observados na amostra: A 142,1 ms; B 21,6 ms; C 21,4 ms. B/C aproveitaram cache do contexto dessa medição: **não são benchmark comparável nem previsão de produção**. Não se executou Lighthouse ou medição de Core Web Vitals em dispositivo físico.
- Os testes Node verificam links/assets locais e limites de isolamento. São complementares; comportamento foi comprovado no navegador real.
- Suítes Python/PostgreSQL e regressões integrais da Parte 1 **não foram repetidas**, pois não há alteração funcional, de persistência ou de API. Os resultados anteriores não são apresentados como novas execuções.

## Limites de aprovação

Não houve teste com usuários, leitor de tela, Safari/Firefox ou aparelho físico. O cálculo de contraste é uma verificação básica de texto visível, não uma certificação completa WCAG. O breakpoint de 320 px cobre reflow, mas não equivale a todos os cenários de zoom e fontes do sistema.

O fluxo se encerra intencionalmente na prévia. Catálogo real, carregamento/erro de rede, calendário, autenticação, confirmação de reserva e tema claro/escuro do produto serão integrados somente depois da escolha. O backend e os contratos existentes permanecem intactos.

**Entrega desta etapa: três protótipos para aprovação. Sem commit, push, merge ou deploy.**

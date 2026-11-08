# Parte 2 — identidade editorial nas telas internas

Implementação local de 7 de novembro de 2026, autorizada após aprovação da A híbrida e da HOME. Branch `design/ux-art-direction-part2`, worktree `.worktrees/ux-art-direction-part2`, base `19cfa2738fb30f81339f1dfc472b99b139a6b7bb`. Sem commit, push ou publicação. A HOME, seus assets/intro/Ritual/Estrelinha e os protótipos anteriores permanecem preservados.

## O que mudou

- **Acesso e recuperação:** composição editorial com formulário em superfície clara, campos e rótulos legíveis, títulos visíveis, links de ajuda, foco e controle de senha existentes. Sem introdução de espera ou intro nas páginas internas.
- **Serviços e profissionais:** tipografia Fraunces/Space Grotesk local, bordas retas e delicadas, hierarquia clara de nome, descrição, preço, duração e próxima ação. Dados continuam vindos da API e renderizados com as proteções existentes.
- **Reserva:** quatro etapas com `aria-current`, apenas etapas anteriores clicáveis, links locais e allowlist de parâmetros. Voltar da revisão conserva serviço/profissional e, quando aplicável, `appointment_id`. Reagendamento mantém as escolhas bloqueadas e volta à lista de reservas, sem escapar para troca de profissional.
- **Calendário:** apresentação mais ampla, serviço/profissional agrupados, dias sem expediente/bloqueados desabilitados, dia cheio distinto, seleção destacada e horários em região própria. Janela, duração, sugestões e controle de respostas antigas permanecem no componente da Parte 1.
- **Minha área:** reserva em destaque, navegação comum para agendamentos/conta, ação de agendar mesmo quando a lista está vazia, privacidade e exclusão visualmente separadas.
- **Gestão:** mantém todos os módulos e controles de perfil; tabela de atendimentos vira blocos no mobile com semântica explícita de tabela/linhas/células. Valor cobrado tem rótulo visível; o trilho revela o dia selecionado sem rolar a página. Ações perigosas se distinguem das principais e secundárias.

O CSS novo só atua em `.product-editorial`/componentes novos dessas páginas, reutiliza `installation.css`, respeita movimento reduzido e não altera o CSS global ou a HOME. Nenhuma biblioteca, fonte externa ou backend foi adicionado.

## Correções verificadas durante o trabalho

1. O listener `{ once: true }` na confirmação era removido após a primeira falha: o botão parecia disponível, mas clicar novamente não enviava a reserva. O listener agora persiste, com guarda contra envio em andamento, texto de confirmação, `aria-busy`, remoção do erro anterior e reabilitação após erro. A consulta e o payload do reagendamento permanecem os mesmos. Isso não adiciona idempotência ao servidor nem garante entrega de resposta HTTP: as regras de concorrência/duplicidade continuam pertencendo ao backend.
2. O calendário tinha um retorno para troca de profissional também no reagendamento. Agora retorna aos agendamentos nesse modo, preservando o contexto travado.
3. Inspeção de screenshots corrigiu contraste do título no cartão claro, diferenciação entre botões secundários/destrutivos e apresentação da agenda em 320/390 px.
4. O teste Python detectou o novo módulo de navegação anterior à configuração de mesma origem injetada no HTML. O módulo foi movido ao fim do documento nas 14 páginas; a configuração existente e o backend não foram alterados.

Nenhuma nova vulnerabilidade de segurança foi demonstrada. Conteúdo semelhante a HTML malicioso foi testado como texto; não houve execução. A revisão não substitui auditoria de segurança ou teste publicado.

## Arquivos desta continuação

- Páginas: `frontend/pages/login.html`, `cadastro.html`, `forgot.html`, `reset.html`, `catalog.html`, `client-services.html`, `client-profissional.html`, `client-date.html`, `client-confirm.html`, `client-dashboard.html`, `client-appointments.html`, `client-account.html`, `client-evaluate.html`, `admin.html`.
- Novo estilo: `frontend/assets/css/product-editorial.css`.
- Novo módulo: `frontend/assets/js/product-navigation.mjs`.
- Ajustes pontuais: `frontend/assets/js/schedule.js`, `booking-calendar.mjs`, `agenda_admin.js`.
- Regressões: `frontend/tests/product-navigation.test.mjs`, `schedule-date.test.mjs`, `agenda-admin.test.mjs`; `frontend/e2e/product-editorial.browser.js`, `product-editorial.spec.mjs`, `product-editorial.config.mjs`.
- Documentação: este relatório, `README.md`, `docs/REQUISITOS_STATUS.md`, `docs/superpowers/plans/2026-11-07-product-editorial.md`. Graphify atualizado localmente por AST.

Arquivos da integração anterior da HOME continuam locais, sem staging. Screenshots, scripts auxiliares e caches não fazem parte do produto.

## Validação executada

| Verificação | Resultado final |
| --- | --- |
| Runner `product-editorial.browser.js` em Chromium real via Playwright MCP | **200 verificações aprovadas**, 0 falhas/ignoradas, 0 erros JavaScript, 0 requisições fora do servidor local/fixtures declaradas |
| `rtk proxy node --test frontend/tests` | **61 aprovados**, 0 falhos/ignorados |
| `test_same_origin_frontend.py`, Python 3.14 da venv existente, SQLite temporário exclusivo | **7 aprovados**, 0 falhos/ignorados |
| Revisão independente somente leitura | Sem achados acionáveis |
| `git diff --check` | Sem erros de whitespace; avisos de normalização LF/CRLF no Windows |

Chromium: layouts em 1440, 390 e 320 px nas 14 páginas; navegação serviço → profissional → data → revisão; dias sem expediente/bloqueados/lotados, sugestões, troca de profissional e serviço longo, retry de disponibilidade, erro e nova tentativa de confirmação, proteção contra duplo envio, PUT de reagendamento preservado, edição/cancelamento de formulário de serviço, visibilidade por perfil, login com redirect de reserva, senha visível/oculta, cadastro com consentimento, recuperação, reset com fragmento e sem token, logout, avaliação, abertura/fechamento de exclusão sem DELETE, teclado, seleção por toque e reduced-motion.

A primeira rodada de navegador foi 169/175: retry de confirmação e overflow da gestão foram corrigidos. A suíte Node inicialmente detectou 10 limitações dos doubles DOM após a introdução de APIs de layout/query/remove; os doubles foram atualizados e foi adicionado teste de envio em andamento/retry. Python inicialmente teve 7 erros de permissão no SQLite do sandbox; a repetição autorizada fora dele expôs 1 falha real de ordem de scripts, corrigida antes dos 7/7 finais. Um teste novo também assumia incorretamente redirect automático após reset; foi alinhado ao comportamento existente de mensagem de sucesso, sem alterar a autenticação.

### Reprodução local

Node:

```powershell
rtk proxy node --test frontend/tests
```

Com as dependências Playwright já declaradas/instaladas pelo projeto, a suíte persistente para CI é:

```powershell
rtk proxy node node_modules/@playwright/test/cli.js test --config=frontend/e2e/product-editorial.config.mjs
```

A CLI `@playwright/test` não estava instalada neste ambiente; **esse comando não foi executado** e nenhum pacote foi instalado. Executou-se o mesmo runner pelo Playwright MCP, contra o servidor estático local `home-experience-setup.mjs` em `127.0.0.1:4186`. O runner exporta uma função renderizável `async (page, options)`; aceita `baseURL` loopback e `screenshotDir`. O wrapper de CI salva resultados e screenshots no diretório do teste. Todas as chamadas de API são interceptadas, sem credenciais reais.

Python, a partir de `backend/`, usando o executável da venv existente:

```powershell
rtk proxy <python-da-venv> -c "import os, unittest; os.environ['BOOKING_TEST_BACKEND']='sqlite'; suite=unittest.defaultTestLoader.discover('tests', pattern='test_same_origin_frontend.py'); result=unittest.TextTestRunner(verbosity=1).run(suite); raise SystemExit(not result.wasSuccessful())"
```

### Evidências visuais

Capturas locais ignoradas pelo Git em `test-results/product-*.png`, incluindo login, calendário, dashboard, agendamentos e conta em desktop/mobile, e gestão nos dois tamanhos. Comparação anterior do login em `product-before-login.png`; demais capturas representam o resultado atual. Inspeção visual efetiva detectou e corrigiu problemas que os testes funcionais não identificaram. Dados exibidos nessas imagens são fictícios.

## Limites e pendências

- Integração do navegador usa API fictícia; não equivale a reservar horários em um backend publicado. Testes Python usam banco temporário. PostgreSQL não executado nesta continuação, pois não houve mudança de persistência, schema ou regras do backend.
- Não executados: suíte histórica completa Playwright, auditoria completa, validação em aparelhos físicos/Safari/Firefox ou produção. Não foi observada a falha histórica de `response.json()` durante navegação nesta suíte.
- Antes da publicação: revisar o diff conjunto com a HOME, testar a jornada com a API no ambiente apropriado e coordenar a integração/publicação separadamente. Nada foi commitado, enviado, integrado ou implantado.

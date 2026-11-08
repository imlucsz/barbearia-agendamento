# Painéis da equipe — plano de UX implementado

Implementação local de 7 de novembro de 2026 na branch `design/ux-art-direction-part2`, worktree `.worktrees/ux-art-direction-part2`, base `19cfa2738fb30f81339f1dfc472b99b139a6b7bb`. Preserva a HOME e as telas internas aprovadas. Sem commit, push ou deploy.

## Comportamento

- **Administrador:** seis áreas — Agenda, Clientes, Equipe e horários, Serviços, Financeiro e Configurações. Uma seção visível por vez, subtarefas próximas do título, indicação da área atual, links diretos por hash e histórico do navegador preservados.
- **Barbeiro:** Minha agenda, com texto e navegação próprios. Áreas administrativas permanecem ocultas antes da resolução de `/auth/me` e para esse perfil; hashes administrativos não expõem essas áreas. A autorização continua no backend. Agendamento manual permanece exclusivo do administrador na interface atual; não foi ampliado o acesso permitido pela API.
- **Agenda:** Hoje, consulta direta de data, atualização explícita e trilho semanal. Resumo da resposta existente: reservas, pendentes de conclusão, concluídos e próximo horário reservado na data. Horário de referência em `America/Sao_Paulo`. Lista vazia não é apresentada como prova de expediente ou disponibilidade livre.
- **Ações:** concluir atendimento, marcar ausência e cancelar abrem diálogo com cliente, serviço, data e horário. Conclusão solicita o valor cobrado. Cancelar o diálogo não envia requisição. Durante o envio há bloqueio de repetição/fechamento; erro conserva valor e lista e permite tentar novamente. Mudança de data invalida uma confirmação antiga. Foco retorna à ação ou ao título da agenda.
- **Cadastros:** listas separadas dos editores de serviços, expediente semanal e folgas/bloqueios. Modo de edição explícito, cancelamento e erros preservando os campos. Profissional selecionado continua visível fora do editor e é preservado após salvar. Os controles externos permanecem associados ao formulário por `form`.
- **Financeiro:** Hoje, Últimos 7 dias e Este mês reutilizam o relatório existente. Datas ficam bloqueadas durante a consulta para não misturar períodos; o texto explica o preço da reserva como fallback e o ticket médio.
- **Apresentação:** identidade A híbrida, CSS delimitado ao painel, layout compacto, tabela adaptada ao celular, alvos de ação legíveis, rótulos, foco, títulos e mensagens de erro. Ao redimensionar, o trilho mantém o dia selecionado visível sem deslocar a página.

Nenhum endpoint, payload, permissão, schema, migração, dependência ou código de backend foi alterado. O frontend não substitui validação ou autorização da API e não adiciona idempotência ao servidor. Repetir uma operação após perda de resposta ainda depende das regras existentes do backend.

## Arquivos desta implementação

- `frontend/pages/admin.html`.
- `frontend/assets/css/staff-workspace.css`.
- Novos módulos `frontend/assets/js/staff-workspace.mjs`, `staff-summary.mjs`, `staff-action.mjs`.
- Integração em `frontend/assets/js/agenda_admin.js`, `admin_management.js`, `financeiro_admin.js`.
- Testes `frontend/tests/agenda-admin.test.mjs`, `staff-summary.test.mjs`, `staff-workspace.test.mjs`.
- Runner e configuração `frontend/e2e/staff-workspace.browser.js`, `staff-workspace.spec.mjs`, `staff-workspace.config.mjs`.
- Este relatório, `README.md`, `docs/REQUISITOS_STATUS.md` e `docs/superpowers/plans/2026-11-07-staff-workspace.md`.

Alterações anteriores da HOME, páginas do cliente, calendário e protótipos permanecem locais e preservadas. Capturas e scripts auxiliares estão em `test-results/`, ignorado pelo Git.

Graphify atualizado localmente por AST, sem extração semântica/API. Staging vazio, HEAD preservado; o worktree mantém as alterações anteriores e desta implementação para revisão.

## Validação executada

| Verificação | Resultado final |
| --- | --- |
| Runner `staff-workspace.browser.js`, Chromium 156 real via Playwright MCP | **104/104 verificações**, zero falhas, erros JavaScript ou requisições inesperadas |
| Regressão `product-editorial.browser.js`, Chromium real via Playwright MCP | **200/200 verificações**, zero falhas, erros JavaScript ou requisições inesperadas |
| `rtk proxy node --test frontend/tests` | **66 aprovados**, zero falhos/ignorados |
| Python `test_same_origin_frontend.py` e `test_authorization.py`, SQLite temporário exclusivo | **21 aprovados**, zero falhos/ignorados |
| Revisão independente somente leitura | Sem achados acionáveis |
| `node --check` no spec/config novos | Ambos aprovados |
| `git diff --check` | Sem erros; apenas avisos de normalização LF/CRLF do Windows |

O navegador usa servidor estático local e interceptação de todas as APIs com dados fictícios, rejeitando tráfego externo. Cobertura: administrador/barbeiro, perfil ainda carregando, hashes diretos/reload/voltar, 1440/390/320 px, teclado e foco, contexto/valor da confirmação, cancelamento sem PUT, envio duplicado, erro/retry, resposta antiga, agenda vazia/erro, criação manual, edição/criação de serviço, edição de horário e bloqueio, profissional preservado, períodos financeiros e conteúdo HTML exibido como texto.

As 200 verificações de regressão também cobrem login/recuperação, fluxo de reserva, reagendamento e área do cliente. No ciclo intermediário, seis verificações apontaram rótulos sem vínculo por seletores de profissional duplicados; corrigidos antes do resultado final de 200/200. Inspeção das capturas corrigiu espaço excessivo nas listas mobile, aparência do campo Motivo e visibilidade do dia selecionado ao redimensionar. Os doubles Node da agenda foram adaptados ao diálogo; os testes verificam erro sem apagar a agenda e bloqueio de contexto antigo.

Capturas reais locais, com dados fictícios:

- `test-results/staff-admin-1440.png` e `staff-admin-390.png`.
- `test-results/staff-barbeiro-1440.png` e `staff-barbeiro-390.png`.
- `test-results/staff-hours-mobile.png`.

### Reprodução

Node, na raiz deste worktree:

```powershell
rtk proxy node --test frontend/tests
```

Python, em `backend`, usando a venv existente do repositório principal apenas como interpretador:

```powershell
rtk proxy C:/Users/Aluno/Documents/barbearia-agendamento/backend/.venv/Scripts/python.exe -c "import os, unittest; os.environ['BOOKING_TEST_BACKEND']='sqlite'; suite=unittest.TestSuite(unittest.defaultTestLoader.discover('tests', pattern=p) for p in ['test_same_origin_frontend.py','test_authorization.py']); result=unittest.TextTestRunner(verbosity=1).run(suite); raise SystemExit(not result.wasSuccessful())"
```

Os testes SQLite foram executados com autorização fora do sandbox devido à restrição de criação dos arquivos temporários. Nenhum banco publicado ou de desenvolvimento foi utilizado.

Configuração persistente para CI, em `frontend`, quando o Playwright declarado pelo projeto estiver instalado:

```powershell
rtk proxy node node_modules/@playwright/test/cli.js test --config=e2e/staff-workspace.config.mjs
```

Esse comando CLI não foi executado nesta sessão: o pacote não estava disponível localmente e nenhuma instalação foi feita. O mesmo runner foi executado integralmente no Chromium via Playwright MCP, servido em `http://127.0.0.1:4186/e2e/staff-workspace.browser.js`. As configurações usam o servidor estático de testes existente, sem backend ou banco real.

## Limitações e próximos passos

- Validar a compreensão dos rótulos e a ordem das tarefas com administrador e barbeiro reais. A inspeção de usabilidade foi técnica, sem pesquisa com usuários finais.
- Navegador validado em Chromium desktop e viewports mobile; não equivale a Safari/Firefox ou aparelho físico. Nenhuma medição formal de WCAG ou performance foi realizada.
- Resumo atualiza ao consultar/recarregar a agenda, não em tempo real. Ausência de reservas não determina horários disponíveis.
- Testes de navegador usam fixtures; testes Python exercitam backend real em SQLite isolado. PostgreSQL e auditoria completa não foram repetidos, pois não houve mudança de persistência.
- Eventual abertura de agendamento manual/jornadas ao barbeiro na interface requer decisão separada; as permissões e telas atuais foram preservadas.
- Mudanças continuam prontas para revisão local, sem publicação nem validação em ambiente publicado.

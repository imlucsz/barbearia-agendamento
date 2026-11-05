# Status de auditoria dos requisitos

## UX-01 — Datas completas antes de chamadas HTTP

- Validação de formato e calendário rejeita anos 0002/0202/0020, valores parciais, dias inexistentes e datas fora de hoje até o dia 14, usando America/Sao_Paulo. Min/max preservados para o seletor nativo; input invalida horários e respostas antigas, change só consulta datas válidas; feedback com aria-invalid, aria-describedby e alert.
- Confirmação valida data/hora também antes de carregar dados e antes de criar/reagendar, respeitando instante atual até instante +14 dias na hora local do estabelecimento (o último dia não é todo liberado). Backend inalterado e definitivo; relógio incorreto do dispositivo pode causar divergência, sem reduzir proteção do servidor.
- `rtk proxy node --test frontend/tests/booking-date.test.mjs frontend/tests/schedule-date.test.mjs`: 8/8. Inclui calendários/bissexto, virada mês/ano, limites temporais, timezone diferente, nenhum HTTP para input/change inválido, resposta tardia descartada, confirmação inválida sem HTTP e criação com data/hora válidas.
- `rtk proxy node --test frontend/tests/*.test.mjs`: 51/51 aprovados.
- Na pasta backend, `rtk proxy C:/Users/Aluno/Documents/barbearia-agendamento/backend/.venv/Scripts/python.exe -m unittest discover -s tests -p test_booking*.py`: 32/32 aprovados, com SQLite temporário exclusivo. A suíte inclui exercícios de migrações históricas no banco temporário; nenhuma migração aplicada em banco de desenvolvimento/produção, nenhum arquivo de migração alterado.
- Playwright não executado: dependência ausente, tentativa detalhada em SEC-01. PostgreSQL não executado: sem banco descartável configurado. Não há comprovação browser/mobile nesta entrega; preservar seletor nativo não substitui essa validação.
- `git diff --check`: sem erros. Revisão independente sem bloqueadores. Sem alterações na agenda administrativa, recuperação de senha ou infraestrutura.

## SEC-01 — Refresh exclusivo em cookie

- Login não expõe mais refresh token no JSON nem no schema público. Cadastro já não emitia tokens; refresh já rotacionava exclusivamente no cookie. Frontend usa cookie e não dependia desse campo. Testes passaram a extrair o cookie; rotação, revogação, Origin, autorização e rate limiting preservados.
- Cookie: HttpOnly, Secure em produção, SameSite=Lax, host-only, Path=/auth, Max-Age=2592000; logout mantém atributos e zera Max-Age. Auditoria de login/reuso não recebe segredo; teste verifica logs e mensagens sem token.
- Evidência: `rtk proxy C:/Users/Aluno/Documents/barbearia-agendamento/backend/.venv/Scripts/python.exe -m unittest discover -s tests -p test_auth_sessions.py`: 13 aprovados. Mesmo comando com `-p test_auth*.py`: 31 aprovados, exclusivamente SQLite temporário. Regressão reproduzida antes da correção (1 falha de exposição); primeira execução no sandbox teve 10 erros por bloqueio do SQLite, reexecuções fora do sandbox passaram.
- Playwright: tentativa `node ../../node_modules/@playwright/test/cli.js test --config frontend/e2e/playwright.config.mjs --grep "cadastro, login|agendamento" --project desktop-1280x800` bloqueada por MODULE_NOT_FOUND; teste existente ampliado para ausência do campo JSON e atributos de cookie. Sintaxe verificada com `node --check frontend/e2e/essential-flows.spec.mjs`, sem erro. Renovação real em navegador e Render permanece não comprovada nesta entrega.
- Incompatibilidade estrutural preexistente: hosts distintos de onrender.com são cross-site (Public Suffix List); Lax impede fetch com cookie. README propõe domínio próprio compartilhado HTTPS ou proxy na mesma origem antes de implantação. Atributos e arquitetura não alterados. Access token em localStorage continua sujeito a XSS; esta correção reduz exposição do segredo de longa duração.
- PostgreSQL não executado: nenhum BOOKING_TEST_POSTGRES_URL descartável configurado. Sem schema/migração, dados reais ou publicação.

## Correção da agenda administrativa — 2026-11-04

- Branch `fix/admin-agenda-navigation`, criada de `origin/main` atualizado em
  `f565c29`. Listagem e GET/PUT de clientes por ID exigem `ativo=True`, preservando
  bloqueados ativos, anonimização e registros históricos. Sem mudança de schema,
  autenticação ou CORS.
- Agenda consultada independentemente dos catálogos auxiliares. Erros reais da
  agenda permanecem visíveis; respostas antigas de consulta/alteração não
  sobrescrevem a data selecionada. Referências tardias não redesenham a tabela
  após interação, preservando foco, valor cobrado e erros de atualização.
- Navegação semanal anterior/posterior mantém o dia da semana; seleção de datas,
  nomes acessíveis completos e estado `aria-pressed`. Teclado: Enter/Space nos
  botões; setas esquerda/direita, PageUp/PageDown e Home/End nas datas.
- Evidências executadas (com prefixo `rtk proxy`):
  - Na pasta `backend`, `.venv/Scripts/python.exe -m unittest discover -s tests -p test_authorization.py`: **14/14**.
  - Na pasta `backend`, mesmo comando com `-p test_lgpd_portability.py`: **6/6**,
    incluindo exclusão real de conta fictícia seguida de GET/PUT administrativos
    e preservação dos históricos/valores financeiros.
  - Na pasta `backend`, mesmo comando com `-p test_booking_integrity.py`: **9/9**.
  - `node --test frontend/tests/agenda-admin.test.mjs`: **9/9**.
  - `node --test frontend/tests/*.test.mjs`: **43/43**, incluindo os nove acima.
  - `node --check frontend/e2e/agenda-navigation.spec.mjs`: sem erro de sintaxe.
- Testes Python usaram exclusivamente SQLite temporário; o sandbox bloqueou a
  abertura inicial e as execuções bem-sucedidas ocorreram com permissão elevada.
  Nenhuma migração executada ou dado real acessado. PostgreSQL: **não executado**.
- Playwright preparado para desktop/mobile, porém **não executado**: CLI ausente
  e `node_modules` vazio; tentativa de npm retornou `ENOTFOUND registry.npmjs.org`.
  Instalação não repetida após orientação de retomada. Sintaxe não equivale a
  validação em navegador; interação/visual continuam pendentes dessa execução.
- Revisão independente concluída sem bloqueadores após preservar edições contra
  referências tardias. `git diff --check` sem erros; `graphify update .` concluído
  por AST, sem LLM. Sem commits locais, push, merge ou deploy.

## Fechamento dos checks do laboratório — 2026-11-03

Checks gerais 17/17 e vídeo 18/18 aprovados isoladamente após corrigir sincronização dos testes, sem alterar runtime ou assets. Justificativa em [validação do Lab](../frontend/e2e/motion-lab/VALIDACAO.md). A HOME pública não depende do Lab em runtime. Firefox/WebKit mantêm os limites registrados abaixo. Sem staging, commits, deploy ou alteração de banco.

## Ritual contínuo universal — 2026-11-03

- Removida a seleção de três stills por largura/altura. Com movimento normal,
  `timeline.progress()` alimenta o seeker em todas as viewports; breakpoints
  escolhem somente a apresentação. Preservados asset, GOP/codec, fila segura,
  storytelling, cortes narrativos e destinos dos botões. Reduced-motion mantém
  poster, capítulos completos e vídeo sem src/pin/corredor.
- Mobile usa palco sticky e 310svh de seção (fallback 310vh); composição curta
  ajustada após revisão visual para não esconder rosto/etiqueta sob o header
  nem sobrepor texto e régua. Hero/Estrelinha/Serviços/backend não alterados.
- Evidência: matriz de 11 viewports por canal instalado Chrome/Edge, 22/22;
  regressão visual compacta posterior, 6/6; HOME existente, 44/44; Node, 27/27.
  Validados tempos 0/12/25/38/50/63/75/88/100%, rVFC, reverso, touch, resize,
  reduced-motion, ausência de overflow e acesso à seção seguinte.
- Edge tablet: 12 gestos isolados convergiram em 2,5s; zero writes durante seek.
  Desvio antigo de ~0,33s não reproduzido como falha persistente. Corrida de
  resize comprovada no teste (alvo final 7,333s, vídeo convergente); ajustada
  sincronização do teste, sem alteração do seeker. Três repetições posteriores
  passaram. Probe final Chrome/Edge em 1440×900/640: centenas de frames reais,
  zero writes concorrentes e zero dropped frames reportados.
- Firefox: 2 falhas em newPage, reproduzidas também em about:blank. WebKit:
  2 falhas de mídia antes de scrub; asset isolado também retorna error4,
  readyState0/duração NaN, apesar de canPlayType=probably. Firefox/Safari real
  continuam sem compatibilidade demonstrada neste ambiente. Sem fallback por UA.
  Fallback/reduced-motion WebKit: 4/4 aprovados, sem equivaler a scrub validado.
- Comandos, arquivos, capturas e limites: [relatório atual](HOME_MOTION_INTEGRATION.md#ritual-contínuo-universal--2026-11-03).
  Testes Python/SQLite/PostgreSQL não executados; validação estática com dados
  fictícios interceptados, sem iniciar backend ou banco. Sem commit/push/deploy.

## Laboratório de motion — fase 1 — 2026-11-02

**Concluído como prova visual isolada; integração com a HOME pendente.** Direção
"Precisão que transforma" aprovada pelo usuário. Código em
`frontend/e2e/motion-lab/`, já excluído do build estático pela exclusão existente de
`e2e`. Nenhuma alteração desta rodada em index.html, backend, API, banco ou auth.

- Cenas: intro → hero de 3,5s/2,3s mobile, tesoura SVG articulada com reação Canvas,
  espelho PREPARO → TÉCNICA → ACABAMENTO em uma timeline reversível com um pin desktop,
  e CTA editorial final. Pointer move iluminação; CTA permanece estável.
- Comparação real de pole SVG/CSS versus Three procedural, independente das cenas;
  fallback SVG em falhas, inclusive perda de contexto. Preferência técnica/visual
  inicial por SVG: Three ainda não mostrou vantagem suficiente para integração.
- Dependências exclusivas do laboratório: GSAP 3.15.0 e Three.js 0.187.0, lockfile
  local, imports locais sem CDN. Não há fotos/stock, pessoas inventadas ou APIs.
- Evidência: `rtk proxy node frontend/e2e/motion-lab/checks.mjs`: **17/17 checks
  aprovados no Google Chrome**, incluindo intro, skip/Escape/Tab, pointer, scroll nos
  dois sentidos, viewports 320/390/768/820/1000/1440, reduced-motion inicial/em sessão,
  falhas de GSAP/Three, montagem parcial, perda/recuperação de WebGL e desmontagem.
  `rtk proxy node --test "frontend/tests/*.test.mjs"`: **26/26 aprovados**.
- Console da navegação normal sem erros, sem requisições a backend/API ou recursos
  externos; falhas induzidas verificadas em contextos próprios. Nenhum teste de banco
  executado. Screenshots e relatório em `frontend/e2e/motion-lab/artifacts/` (ignorado).
- Comparação lado a lado executada com o Temaki original em modo full. Referência
  permanece mais complexa em nuvem WebGL e variedade de cenas; laboratório demonstra
  causalidade e transformação visual com instrumentos/espelho, sem copiar identidade.
- Instrumentação distingue um consumidor compartilhado do ticker GSAP dos RAF
  internos de GSAP/ScrollTrigger. Até 62 partículas desktop/23 mobile, um contexto
  WebGL sob demanda, cinco ScrollTriggers, 18 listeners próprios/19 com Three.
  Canvas fora de uso param de renderizar; teardown verificado com zero contextos,
  triggers, listeners próprios e RAF pendentes.
- Fontes visuais próprias: cerca de 77 KB (23 KB gzip concatenado estimado). Módulos
  de desenvolvimento são servidos sem minificação/compressão; bytes no HUD significam
  subrecursos descomprimidos, sem o documento HTML. Não são números de bundle final.
- Revisão independente levou a correções de cleanup transacional e retry em canvas
  novo. A validação visual corrigiu stacking da intro e sobreposição mobile. Um
  timeout de teste foi resolvido encerrando contextos de navegador já concluídos;
  rodada final completa passou. Métricas de campo, Firefox/WebKit e aparelho físico
  não foram medidos. Nenhum commit, push ou deploy.

## Home editorial — 2026-11-02

Implementada a evolução da apresentação: entrada não bloqueante do hero (até 990 ms), transição editorial, etapas conectadas, Ritual cuidado → técnica → resultado e CTA final no fluxo existente. `home.js`, widget, recursos opcionais, backend e contratos permanecem intactos. Estrelas fixas do hero substituídas por ornamento, sem alegação de média.

- Camada independente: `frontend/assets/css/home-experience.css` e `frontend/assets/js/home-experience.mjs`; conteúdo visível por padrão, sem polling, Canvas, WebGL ou dependências adicionais.
- Ritual: apenas visual sticky em desktop >=1000px/altura >=650px; textos sempre lineares e disponíveis. Mobile e reduced-motion sem pinning; mudanças de preferência em sessão cancelam animações.
- Evidência: `rtk proxy node --test "frontend/tests/*.test.mjs"`: **26/26 aprovados**. `rtk proxy node node_modules/@playwright/test/cli.js test --config frontend/e2e/home-experience.config.mjs`: **36/36 aprovados**, Chromium 1440×900, 820×1180, 390×844 e 320×568. Fixtures fictícias interceptam API; nenhum banco ou migration executado.
- Cobertura: skeleton, falha/retry, catálogo, links, contatos, avaliações ocultas/média, iframe sem ancestrais transformados, menu, âncoras, teclado, overflow, reduced-motion inicial/em sessão, ausência/falha de APIs e módulo, progressão/resize do Ritual. Smoke adicional com Estrelinha habilitada e Enter: um Canvas existente e nenhum erro de console/pageerror.
- Revisão visual desktop e 320px realizada; texto do espelho cabe em 320px. Revisão independente sem achados críticos/importantes. O teste da progressão detectou e permitiu corrigir margens verticais do observer (percentuais são relativos à largura); teste de teclado ajustado para navegação real por Tab/Shift+Tab.
- Tamanho medido: JS 6.467 bytes / 2.121 gzip; CSS 7.852 bytes / 2.253 gzip. Até dois observers ativos; seis listeners; um RAF sob demanda do ponteiro, sem loop. Zero assets gráficos novos. Métricas de campo LCP/INP e Firefox/WebKit não foram medidas nesta rodada.
- O primeiro comando Node com diretório falhou por resolução do runner; comando corrigido com glob passou. `git diff --check` global mantém aviso preexistente em `AGENTS.md:29`; arquivo protegido não foi corrigido. Não houve commit, push ou deploy.

Esta evidência é de apresentação com API interceptada, não uma nova validação integral da release ou de produção.

## Parecer v1.0.0-rc.1 — 2026-11-01

**RELEASE CANDIDATE: APROVADA COM RESSALVAS**, para UAT controlado com dados fictícios/contas próprias. Não equivale a liberação irrestrita da primeira instalação comercial com dados reais.

Candidato validado: working tree sobre `main` / HEAD `218575f202e897a92f23cd4ee23091c2b1438045`, incluindo correções locais anteriores de auditoria e backup. Não é apenas o HEAD remoto. Impressão SHA-256 do recorte de 178 arquivos de app/testes/frontend/migrations/backup/manifests: `1723a723dca17bc10c6f3ee428a4d96c68e1e201d021b8dae447de0b9df691f8`. Documentação e arquivos locais alheios não entram nesse recorte; não é checksum de artefato publicado. Nenhuma tag/commit/push/deploy nesta rodada.

Contagem: **23 RF Implementados, 0 Parciais, 1 A validar (RF06); 5/5 RN Implementadas; 12 RNF Implementados e 6 Parciais (06, 09, 13, 15, 17, 18).** Implementado identifica evidência técnica no escopo existente, sem substituir aceite operacional/jurídico da instalação.

## Pendências e severidade

- **P0:** nenhum defeito demonstrado.
- **P1 — operação/requisito funcional, antes de concluir UAT de RF06:** confirmar entrega pelo transporte configurado, URL e reset completo com uma conta própria no ambiente publicado. Não enviar para terceiros nem registrar tokens.
- **P1 — operação/segurança, antes de piloto com dados reais/v1.0:** backup diário externo com ≥30 dias, chave sob custódia, monitor/alerta comprovado, responsável/suplente identificados e ensaio de recuperação representativo. RPO ≤24h/RTO ≤4h são metas, não SLA medido.
- **P1 — operação/segurança:** confirmar TLS/redirect/headers, CORS/cookie/origem e IP da borda na instalação. PostgreSQL Free declarado no YAML expira após 30 dias; requer decisão de destino durável antes de uso comercial continuado. Nenhuma infraestrutura foi contratada/alterada.
- **P1 — documentação/aceite da v1.0:** alinhar os termos normativos antigos de RNF-02 (bcrypt versus Argon2 atual), RNF-10 (limites de rollback) e RNF-12 (nome da variável); realizar smoke nas versões de marca exigidas em RNF-09. Não são regressões que autorizem rebaixar segurança ou reescrever migrations.
- **P2 — validação operacional:** investigar crash Firefox se voltar a ocorrer; ensaio de contenção de rate limit entre workers e benchmark representativo apenas quando necessários. Não reabrir requisito concluído sem evidência concreta.
- **P3:** nenhuma melhoria nova necessária para esta RC; sem features adicionais.

Render saudável, PostgreSQL 16 validado e deploy anterior funcionando são contexto confirmado pelo usuário. Esta rodada prova o candidato local; não revalida remotamente esse working tree nem presume CI/deploy verde para mudanças ainda não integradas.

## Evidências da validação formal — 2026-11-01

| Verificação | Resultado real |
|---|---|
| Backend SQLite, suíte completa | 266 executados; 259 aprovados, 7 skips condicionais; 0 falhas/erros; 294,012 s |
| Backend PostgreSQL 16 descartável, suíte completa | 266 executados; 264 aprovados, 2 skips exclusivos SQLite; 0 falhas/erros; contêiner removido |
| Migrações / integridade | Banco vazio → head, banco anterior → head, head idempotente, paridade, concorrência/double booking e preservação cobertos pelas suítes; head `20261031_01` |
| Launcher Render Free | Migra antes de liberar a fronteira Uvicorn; falha real impede startup; readiness 503 sem head e 200 em head; testes existentes aprovados |
| Auth/RBAC/recuperação/LGPD/auditoria/RF13/RF14 | Testes existentes incluídos nas duas suítes; recuperação real via e-mail continua externa |
| Node | 26/26 aprovados |
| Playwright completo | Exit 1: 60 aprovados, 3 Firefox caíram em `browserContext.newPage: Target crashed`, antes de abrir páginas |
| Repetição somente Firefox, fora da sandbox | Exit 0: 3/3 aprovados; total de 63 casos distintos aprovados, sem alterar testes/código |
| Matriz de navegadores | Chromium/Firefox/WebKit × 320×568, 390×844 e 1280×800; 27 fluxos desktop e 27 mobile, mais 9 responsivos |
| Backup/restore | 4 testes unitários aprovados; pg_dump → age → checksum/manifesto → rsync → pg_restore reais; head, 14 contagens e fixture preservados; corrupção rejeitada; restore 3,339 s / ciclo local 3,83 s |
| pip-audit | Resolução completa; 36 dependências; 0 vulnerabilidades; exit 0, com rede liberada |
| npm audit | 0 vulnerabilidades em todas severidades; exit 0, com rede liberada |
| Segurança | CORS/headers/rate limiting/XSS e RBAC cobertos por fontes/testes; scan sanitizado de 204 textos rastreados, 12 binários fora da cobertura; candidatos apenas fixtures, nenhum secret real identificado no recorte |
| Render | YAML lido/validado localmente: `plan: free`, backend rootDir, `python -m app.render_start`, health check `/ready`; nenhum acesso ao Render ou banco real |

Os skips são seleções por dialeto, não falhas ocultadas. O runner PostgreSQL usou URL efêmera apenas na memória e banco `*_test`, sem ler DATABASE_URL real. Backup usou dois contêineres e rede exclusivos, sem volumes do usuário; todos removidos. A falha inicial Firefox é ocorrência operacional P2: não reproduzida fora da sandbox, causa ambiental ainda não demonstrada. Não se declara que o primeiro comando Playwright terminou com sucesso.

Artefatos Playwright locais: `test-results/e2e/` e `test-results/rc1-firefox-diagnostic/`. Auditoria de secrets não abrange histórico Git, binários ou todos os arquivos locais não rastreados; isso não é certificação de ausência universal de segredos.

## Requisitos funcionais

| Requisito | Situação | Evidência | Limite / pendência | Próximo passo mínimo |
|---|---|---|---|---|
| RF01 | Implementado | `GET /services/`; campo `Service.descricao`/migração `20261029_05`; schemas Pydantic; `test_public_catalog.py:test_public_services_include_description_price_and_duration`; `test_schema_validation.py:test_service_description_price_duration_and_name_limits`; Playwright `essential-flows.spec.mjs:catálogo público exibe descrição, preço e duração` em desktop/mobile | Nenhuma lacuna funcional identificada nos campos e páginas públicas cobertos. | Preservar cobertura de preço, descrição e duração nas páginas públicas ao alterar catálogo ou apresentação dos serviços. |
| RF02 | Implementado | `backend/app/routers/institucional.py:get_informacoes/create_or_update_informacoes/update_informacoes`; `frontend/assets/js/admin_management.js:saveInstitutionalInfo`; `frontend/assets/js/home.js:loadBusinessInfo/renderMap`; `backend/tests/test_institutional_info.py` (persistência, leitura pública e 403); Playwright `essential-flows.spec.mjs:painel administrativo carrega e gerencia serviços...` desktop/mobile | Nenhuma lacuna identificada para edição administrativa e apresentação pública dos contatos, horário e link seguro do mapa. | Manter os testes API e E2E desktop/mobile ao alterar informações institucionais ou o mapa. |
| RF03 | Implementado | `backend/app/routers/appointments.py:get_avaliacoes` filtra `oculta=False`; `frontend/assets/js/home.js:loadReviews` calcula a média e exclui ocultas; `backend/tests/test_public_reviews.py` testa filtragem da API e lista vazia; Playwright `essential-flows.spec.mjs:nota média pública...` testa cálculo com oculta, estado sem avaliações e renderização desktop/mobile | Nenhuma lacuna identificada na média das avaliações publicamente visíveis. | Manter os testes da API e da home para média pública, avaliações ocultas e estado vazio. |
| RF04 | Implementado | `backend/app/routers/auth.py:register_user`; modelos `ConsentimentoLGPD` e `User`; `backend/tests/test_auth_sessions.py:test_registration_records_versioned_consent_and_login_issues_hashed_cookie_token` | Campos legados de `User` permanecem por compatibilidade; nenhuma lacuna da parte de consentimento especificada foi identificada. | Preservar teste de registro de versão, data/hora, IP e origem ao alterar cadastro. |
| RF05 | Implementado | `auth.py:login_user`, `refresh_session`, `logout_session`; `dependencies.py:get_current_user`; `test_auth_sessions.py`; E2E `essential-flows.spec.mjs` | Nenhuma lacuna central dos tokens e logout solicitados; access token permanece em `localStorage`, com risco XSS documentado no guia de implantação. | Manter rotação, detecção de reuso, CSRF e fluxo E2E de renovação silenciosa. |
| RF06 | A validar | `core/email.py` (Brevo HTTPS/SMTP), `test_brevo_email.py`, `test_password_reset.py`, testes de configuração e fragmento; suíte RC SQLite/PostgreSQL aprovada. Evidência anterior local: redefinição 200, senha antiga 401, nova 200 e reuso 400. | Entrega real, URL pública e redefinição com conta própria no ambiente publicado ainda não comprovadas nesta sessão; não é ausência de implementação. | Validar uma única conta de teste controlada pelo responsável, sem registrar link/token ou secrets. |
| RF07 | Implementado | `backend/app/routers/appointments.py:get_available_slots` exige CLIENTE ou ADMIN e filtra por serviço, barbeiro e data com `validate_booking_slot`; `backend/tests/test_booking_temporal.py:test_availability_filters_by_service_barber_and_date_for_client_and_admin`, `test_availability_denies_barber_role`, `test_availability_uses_local_date_and_includes_fourteenth_day`; Playwright `essential-flows.spec.mjs:disponibilidade respeita duração longa...` desktop/mobile valida horários, jornada e bloqueios | Nenhuma lacuna identificada para consulta autenticada por CLIENTE/ADMIN e filtros previstos. | Preservar autorização por perfil, janela de 14 dias, disponibilidade e cobertura Playwright desktop/mobile. |
| RF08 | Implementado | `appointments.py:create_appointment`; `booking.py:validate_booking_slot`; `backend/tests/test_booking_integrity.py`, `test_booking_temporal.py` | Nenhuma lacuna central identificada; teste E2E de reserva feliz também consta em `frontend/e2e/essential-flows.spec.mjs`. | Manter cobertura integrada da reserva, inclusive concorrência e snapshot do serviço. |
| RF09 | Implementado | `appointments.py:update_appointment`/`cancel_appointment`; `backend/tests/test_booking_temporal.py:test_cancel_requires_exactly_twenty_four_hours_or_more`; `test_authorization.py` | Nenhuma lacuna central identificada. | Preservar testes de limite temporal e autorização ao alterar cancelamento. |
| RF10 | Implementado | `appointments.py:update_appointment`; `backend/tests/test_booking_temporal.py:test_reschedule_obeys_exact_twenty_four_hour_limit_and_two_change_cap`, `test_booking_integrity.py` | Nenhuma lacuna central identificada. | Preservar testes de limite, contador e conflito ao alterar reagendamento. |
| RF11 | Implementado | `backend/app/routers/appointments.py:get_user_appointments` retorna histórico completo por padrão, ordenado por data decrescente, mantendo paginação explícita opcional; `backend/tests/test_authorization.py:test_client_history_includes_past_and_future_records_beyond_default_page` cobre mais de 100 registros, passado/futuro e isolamento; `frontend/assets/js/schedule.js:loadAppointments`; Playwright `essential-flows.spec.mjs:histórico completo...` desktop/mobile verifica exibição e ordem | Nenhuma lacuna identificada para histórico completo do próprio cliente. | Preservar ordenação, isolamento do titular e cobertura de históricos com registros passados/futuros. |
| RF12 | Implementado | `backend/app/routers/appointments.py:create_avaliacao` valida titular e status concluído, grava nota/comentário e muda estado; `Avaliacao.appointment_id` é único; schemas limitam nota a 1–5; `backend/tests/test_appointment_reviews.py` cobre sucesso, duplicidade, titular, status e nota; Playwright `essential-flows.spec.mjs:histórico e avaliação...` valida envio e remoção da ação após avaliar em desktop/mobile | Nenhuma lacuna identificada para avaliação única pelo titular após conclusão. | Preservar os testes de autorização, status, unicidade, nota e envio pela interface. |
| RF13 | Implementado | `admin.py:get_agenda_by_date/get_my_agenda_by_date`; `test_authorization.py`; E2E dedicado RF13 aprovado em desktop/mobile nesta RC. | Sem regressão demonstrada. Agenda mantém a navegação da semana atual; painel ADMIN exibe a equipe. | Preservar filtro de data e isolamento por perfil. |
| RF14 | Implementado | `booking.py:validate_appointment_status_transition`, `appointments.py:update_appointment`; `test_rf14_service_record.py`, `test_appointment_reviews.py`; matriz, tempo, perfil e valor aprovados nas suítes RC SQLite/PostgreSQL e E2E. | Sem lacuna na matriz aprovada; correções administrativas excepcionais fora do escopo. | Preservar matriz e testes. |
| RF15 | Implementado | `backend/app/routers/admin.py:create_manual_appointment` permite Admin/Barbeiro e força o barbeiro autenticado; mantém `lock_barber_for_booking`/`validate_booking_slot`; `backend/tests/test_authorization.py:test_barber_cannot_execute_admin_only_operations` cobre cliente cadastrado, avulso e tentativa de forjar outro barbeiro; `backend/tests/test_booking_temporal.py:test_public_and_admin_creation_keep_price_and_duration_snapshots` | Nenhuma lacuna funcional identificada para os perfis e casos de cliente previstos. | Preservar os testes de cadastro/avulso, identidade do barbeiro e validação de disponibilidade. |
| RF16 | Implementado | `backend/app/routers/services.py` implementa listar/criar/editar/excluir; `backend/app/schemas/service.py` limita preço, duração, nome e descrição; `backend/tests/test_services_crud.py` cobre ciclo de vida, perfil e limites; `test_schema_validation.py:test_service_description_price_duration_and_name_limits`; Playwright `essential-flows.spec.mjs:painel administrativo carrega...` cria, edita e remove serviço em desktop/mobile | Nenhuma lacuna identificada no CRUD administrativo e nos limites testados. | Preservar os testes de ciclo de vida, perfil e limites do serviço. |
| RF17 | Implementado | `backend/app/routers/barbeiro_servico.py` administra associações; `backend/tests/test_barber_service_assignments.py` verifica catálogo vazio, vínculo, disponibilidade resultante, remoção e indisponibilidade/404; Playwright `essential-flows.spec.mjs:painel administrativo carrega...` cobre vínculo e remoção no painel desktop/mobile | Nenhuma lacuna identificada para associação administrativa e reflexo na disponibilidade. | Preservar cobertura do vínculo, remoção e disponibilidade resultante. |
| RF18 | Implementado | `backend/app/routers/horario.py` oferece CRUD de jornada (remoção nova) e bloqueio; `frontend/assets/js/admin_management.js` permite criar, editar, ativar/desativar e remover; `backend/tests/test_schedule_block_lifecycle.py` valida ciclos de vida e efeito na disponibilidade para folga e feriado; `test_authorization.py:test_client_and_other_barber_cannot_access_cross_owned_schedule_or_block`; Playwright `essential-flows.spec.mjs:painel administrativo carrega...` cobre criação/edição/ativação/remoção de jornada e bloqueio feriado em desktop/mobile | Nenhuma lacuna identificada nas operações e tipos exercitados. | Preservar testes de propriedade, ciclo de vida e impacto de folgas/feriados na disponibilidade. |
| RF19 | Implementado | `backend/app/routers/users.py:update_user` bloqueia/desbloqueia cliente e revoga refresh ao bloquear; `backend/app/dependencies.py:get_current_user` nega contas bloqueadas; `frontend/assets/js/admin_management.js:toggleClient`; `frontend/assets/js/api.js`/`session.mjs` encerra sessão após resposta `Conta bloqueada`; `backend/tests/test_auth_sessions.py:test_blocking_client_revokes_refresh_tokens`; Node `frontend/tests/session.test.mjs`; Playwright `essential-flows.spec.mjs:bloqueio e desbloqueio...` confirma bloqueio imediato, logout, desbloqueio e novo login desktop/mobile | Nenhuma lacuna identificada no ciclo testado de bloquear, encerrar sessão e autenticar novamente após desbloqueio. | Preservar revogação de refresh, rejeição de conta bloqueada e E2E das telas de cliente/admin. |
| RF20 | Implementado | `backend/app/routers/institucional.py` cria/atualiza e expõe leitura pública; `backend/tests/test_institutional_info.py` verifica persistência, resposta pública e 403 de cliente; Playwright `essential-flows.spec.mjs:painel administrativo carrega...` cobre edição do painel e leitura dos dados públicos desktop/mobile | Nenhuma lacuna identificada no CRUD administrativo e leitura institucional pública testados. | Preservar os testes de edição administrativa e apresentação pública. |
| RF21 | Implementado | `backend/app/routers/admin.py:get_financial_report` conserva totais/ticket e inclui quebra por barbeiro/serviço/dia e contagem concluído/cancelado/falta; `/admin/relatorio/csv` neutraliza prefixos de fórmula; `backend/tests/test_financial_report.py` cobre intervalo inclusivo, valores cobrados/preço, agrupamentos, status, perfil, datas inválidas e CSV com nomes maliciosos; `frontend/assets/js/financeiro_admin.js` mostra tabela compacta e baixa CSV; Playwright `essential-flows.spec.mjs:relatório financeiro...` cobre filtro, tabela e download desktop/mobile | Nenhuma lacuna identificada no relatório e exportação testados. | Manter os testes dos totais, agrupamentos, status, neutralização CSV e download da tela. |
| RF22 | Implementado | `backend/app/routers/admin.py:get_all_reviews/toggle_avaliacao_oculta`; `backend/app/routers/appointments.py:get_avaliacoes` exclui ocultas; `backend/tests/test_review_moderation.py` cobre admin, bloqueio para cliente, ocultar/reexibir e reflexo público; Playwright `essential-flows.spec.mjs:painel administrativo carrega...` cobre moderação e home desktop/mobile | Nenhuma lacuna identificada na moderação e exposição pública. | Manter os testes de autorização, ocultação e reexibição com atualização da home. |
| RF23 | Implementado | `docs/AUDITORIA_RF23_RNF14.md`; `test_audit.py` (15 testes), `test_audit_catalog.py` (19 testes); catálogo persistido, usuário/ação/entidade/período inclusivo, paginação e RBAC validados também em PostgreSQL 16 descartável | Sem lacuna funcional demonstrada no catálogo exigido. Metadados de edição administrativa contêm apenas nomes de campos; ator anônimo permanece para conta inexistente/anonimização. | Preservar matriz e testes ao alterar geradores. |
| RF24 | Implementado | `GET /users/me/exportacao` (alias legado `/me/export`), dados próprios e versionados; `test_lgpd_portability.py:test_export_is_versioned_complete_and_never_includes_another_user_or_secrets`; botão em `client-account.html`/`schedule.js` | Nenhuma lacuna funcional identificada; limite aplicado por IP/rota através de `AuthRateLimitMiddleware`. | Preservar teste de isolamento, esquema versionado e limite de exportação em futuras alterações. |

## Regras de negócio

| Requisito | Situação | Evidência | Limite / pendência | Próximo passo mínimo |
|---|---|---|---|---|
| RN-01 | Implementado | `booking.py:validate_booking_slot`, `lock_barber_for_booking`; `backend/tests/test_booking_integrity.py` (concorrência, duração e conflito), `test_booking_temporal.py` (bloqueios/jornada) | Nenhuma lacuna identificada nos fluxos testados. | Preservar testes de conflito concorrente, bloqueio, jornada e duração ao evoluir a reserva. |
| RN-02 | Implementado | `appointments.py:update_appointment`; `backend/tests/test_booking_temporal.py:test_cancel_requires_exactly_twenty_four_hours_or_more`, `test_reschedule_obeys_exact_twenty_four_hour_limit_and_two_change_cap` | Nenhuma lacuna identificada nos fluxos de cliente testados. | Preservar testes de antecedência e limite de reagendamentos. |
| RN-03 | Implementado | `booking.py:BOOKING_WINDOW_DAYS`, `validate_booking_slot`; `backend/tests/test_booking_temporal.py:test_booking_rejects_past_and_enforces_exact_fourteen_day_instant_boundary` | Nenhuma lacuna identificada. | Preservar teste do limite temporal exato de 14 dias. |
| RN-04 | Implementado | `appointments.py:create_avaliacao`; `Avaliacao.appointment_id` único; `backend/tests/test_appointment_reviews.py:test_owner_can_rate_concluded_appointment_only_once` e `test_rating_requires_owner_and_concluded_status_and_valid_score` passaram | Não foi feito ensaio de concorrência simultânea de avaliações; a unicidade da coluna é a proteção persistente. | Preservar os testes de titular, status concluído, nota válida e unicidade; adicionar teste concorrente se a implementação de avaliações mudar. |
| RN-05 | Implementado | `appointments.py:create_appointment`, `admin.py:create_manual_appointment`; `backend/tests/test_booking_temporal.py:test_public_and_admin_creation_keep_price_and_duration_snapshots` | Nenhuma lacuna identificada. | Preservar teste de snapshot após edição do serviço. |

## Requisitos não funcionais

| Requisito | Situação | Evidência | Limite / pendência | Próximo passo mínimo |
|---|---|---|---|---|
| RNF-01 | Implementado | `booking.py:lock_barber_for_booking`; aplicado em criação/reagendamento; `backend/tests/test_booking_integrity.py:test_concurrent_overlapping_bookings_for_same_barber_only_one_persists` | Concorrência/double booking executada com sucesso em SQLite e PostgreSQL 16 descartável nesta RC. | Manter validação descartável nos dois dialetos. |
| RNF-02 | Implementado | `core/security.py`, refresh rotativo/revogável e JWT; testes de autenticação, configuração e E2E aprovados na RC. Hash atual Argon2; bcrypt legado é verificado e atualizado. | Divergência documental: texto normativo ainda cita bcrypt como hash de novas senhas; não rebaixar Argon2. Access JWT 5–60 min e refresh persistido apenas como SHA-256. | Alinhar a redação normativa ao hash atual antes da v1.0, sem alterar a proteção existente. |
| RNF-03 | Implementado | `responsive-a11y.spec.mjs`; Chromium, Firefox e WebKit aprovados em 320×568, 390×844 e 1280×800; fluxos completos desktop/mobile nesta RC. | Sem regressão responsiva demonstrada. Firefox exigiu repetição fora da sandbox após queda antes de abrir páginas. | Preservar cobertura de overflow, foco e rótulos. |
| RNF-04 | Implementado | `users.py:excluir_minha_conta` verifica senha, protege último admin, anonimiza/desvincula dados e revoga sessões; migração `20261029_04`; `test_lgpd_portability.py:test_erasure_unlinks_identity_preserves_financial_values_and_blocks_login` e `test_wrong_password_and_last_active_admin_are_rejected`; `docs/LGPD.md` | A retenção legal aplicável deve ser confirmada pelo controlador e configurada por instalação; registros financeiros preservados conforme escopo do requisito. | Revisar bases legais e prazos com assessoria jurídica de cada instalação e manter o inventário LGPD atualizado. |
| RNF-05 | Implementado | `backend/app/dependencies.py:get_current_user/require_roles/ensure_resource_owner/ensure_owner_id`; dependências nos routers; `backend/tests/test_route_authorization_matrix.py` percorre rotas e exige autenticação fora da lista pública; `backend/tests/test_authorization.py` cobre acesso cruzado de clientes e barbeiros | Matriz de perfis e guard de rota são mantidos em `docs/MATRIZ_AUTORIZACAO.md`; criar endpoints requer atualizar explicitamente o inventário público/matriz. | Preservar a lista pública explícita, a matriz e os testes cruzados ao adicionar rotas ou perfis. |
| RNF-06 | Parcial | `backend/app/main.py:SecurityHeadersMiddleware`; `backend/app/config.py:load_settings`; `backend/tests/test_security_controls.py:test_security_headers_are_present_and_hsts_is_production_only`; exemplo estático em `docs/IMPLANTACAO_E_REUTILIZACAO.md` | Render saudável é evidência fornecida pelo usuário; TLS 1.3, redirect, HSTS e headers do frontend/API publicados não foram medidos nesta RC. | Verificação somente leitura do host publicado antes do piloto com dados reais. |
| RNF-07 | Implementado | `backend/app/core/rate_limit.py:AuthRateLimitMiddleware`; modelo `LoginAttempt`; migração `20261029_02`; `backend/tests/test_security_controls.py` cobre 5 falhas, sucesso/reset, expiração e IPs independentes | Bloqueio/reset/expiração e separação por IP aprovados nas suítes RC SQLite/PostgreSQL. Não há prova de contenção simultânea entre múltiplos workers. | Manter cobertura; ensaio multi-worker é P2 enquanto não houver necessidade ou regressão concreta. |
| RNF-08 | Implementado | `appointments.py:get_available_slots`; shared rule `booking.py:validate_slot_against_loaded_data`; indexes revision `20261029_06`; `test_booking_temporal.py:test_availability_matches_legacy_slot_validation_and_uses_bounded_queries`; `test_booking_integrity.py` (concurrency); `docs/BENCH_DISPONIVEIS.md` | Benchmark histórico SQLite: p95 14,72 ms/5 SELECTs (handler, 100 chamadas). Equivalência/limite de consultas aprovados na RC nos dois dialetos; benchmark de carga/latência publicado não realizado. | Não extrapolar benchmark local para SLA do host; medir carga real quando necessário. |
| RNF-09 | Parcial | Playwright: 63 casos distintos aprovados entre suíte completa e repetição Firefox; três motores × três viewports. Chromium 1248, Firefox 1555, WebKit 2370 instalados. | Motores Playwright não comprovam integralmente versões comerciais estáveis Chrome/Safari/Edge. A execução completa saiu 1 (60/63); repetição somente Firefox saiu 0 (3/3), sem alterar código. | Smoke das versões estáveis de marca antes de declarar compatibilidade completa. |
| RNF-10 | Implementado | SQLAlchemy/Alembic; suítes RC SQLite/PostgreSQL 16: banco vazio, upgrade anterior, repetição em head, preservação, paridade; `test_render_start.py` e `test_postgres_booking_migration.py`. | Texto normativo promete rollback genérico; revisões que recusam downgrade destrutivo permanecem assim por segurança. Rollback de deploy não desfaz schema; restore exige procedimento isolado. | Explicitar limite de rollback na especificação antes da v1.0; não editar migrations históricas. |
| RNF-11 | Implementado | `backend/app/schemas/{user,service,institucional,appointment,horario,barbeiro_servico}.py` e `schemas/base.py` validam tipos, tamanhos, formatos, espaços e controles; `test_schema_validation.py`; `frontend/assets/js/escape-html.mjs` usado por `admin_management.js` e `agenda_admin.js`; `home.js` usa nós/textContent e valida HTTPS/host do mapa; `frontend/e2e/essential-flows.spec.mjs` cobre payloads XSS público/admin; `frontend/tests/escape-html.test.mjs` | Nenhuma lacuna reproduzida nos testes. A busca encontrou somente SQL estático ou expressões SQLAlchemy parametrizadas; sem concatenação dinâmica localizada. | Preservar testes de schema e XSS ao alterar campos e telas que exibem dados de API. |
| RNF-12 | Implementado | `config.py:parse_cors_origins`, `main.py:CORSMiddleware` com métodos/cabeçalhos explícitos; `backend/tests/test_application_configuration.py` cobre origem, método, cabeçalho e allowlist | CORS restrito aprovado; variável real `CORS_ALLOWED_ORIGINS`, enquanto `REQUISITOS.md` ainda nomeia `ALLOWED_ORIGINS`. | Alinhar nome documental antes da v1.0 e manter preflight fail-closed. |
| RNF-13 | Parcial | `config.py:load_settings` valida `INSTALLATION_NAME` e segredos por ambiente; `.env` fica ignorado; procedimento de rotação de 90 dias por instalação em `docs/REUTILIZACAO_E_ATUALIZACAO.md` | Nenhum `.env` real/chave privada versionado encontrado no recorte; custódia/operador e execução periódica de rotação reais não comprovados. | Identificar responsável, cofre e calendário por instalação; não registrar credenciais na documentação. |
| RNF-14 | Implementado | `core/audit.py`, `AuditLog`, `RETENTION_DAYS`, `maintenance.purge_audit`; 34 testes direcionados aprovados em PostgreSQL 16 descartável: eventos, atores, IP/UTC, segredos, filtros, expurgo real e fronteira da retenção | Persistência best-effort existente preservada: falha de armazenamento gera aviso sanitizado e pode perder a linha. Não se declara garantia de zero perda, coleta externa ou agendamento de expurgo em produção. | Operação deve configurar coleta/monitoramento e execução de retenção; novas garantias de durabilidade exigem escopo próprio. |
| RNF-15 | Parcial | `tools/backup/backup.py`; 4 testes; ciclo RC PostgreSQL 16 real com pg_dump/age/checksum/manifesto/rsync/pg_restore; head `20261031_01`, 14 contagens e fixture preservados; corrupção rejeitada. | Job diário, destino fisicamente externo, custódia e retenção real ≥30 dias dependem da instalação. Dois contêineres no mesmo host não comprovam separação física. | Escolher executor/destino existentes e comprovar primeira cópia externa; script rejeita retenção <30 dias. |
| RNF-16 | Implementado | Versões fixadas, Dependabot semanal e workflow CI existentes. RC: pip-audit com resolução completa (36 dependências, 0 vulnerabilidades) e npm audit (0 em todas severidades). | Nenhuma vulnerabilidade conhecida encontrada na data da rodada. CI remota deste working tree não executada; não se atribui estado remoto a arquivos sem commit. | Manter auditorias periódicas; após integração autorizada, registrar execução remota da revisão exata. |
| RNF-17 | Parcial | `/health`, `/ready`, `/metrics`; 9 testes de readiness/observabilidade aprovados em 2026-11-01; métricas e logs seguros implementados | Health/readiness/métricas aprovados nas suítes RC; monitor externo e recebimento real de alerta continuam sem evidência. Métricas por processo. | Definir conta/canal/responsável e testar alerta em alvo controlado; não derrubar produção. |
| RNF-18 | Parcial | Runbook com metas RPO ≤24h/RTO ≤4h; restore RC PostgreSQL 16 em 3,339 s na massa mínima, revisão `20261031_01`, 14 tabelas e limpeza confirmadas. | Restore mínimo não comprova recuperação integral, RPO real ou tempos de infraestrutura; responsáveis/suplente/canal e ensaio representativo pendentes. | Nomear responsáveis e ensaiar recuperação representativa após configurar backup externo. |

## Critério mínimo de avanço

Para iniciar UAT controlado: usar o candidato identificado, dados fictícios e contas controladas; registrar limitações e responsável pelo aceite. Para encerrar UAT e liberar v1.0 com dados reais: fechar as pendências P1 acima e o checklist da instalação em `CHECKLIST_PRODUCAO.md`. Publicação/integração exige autorização separada; nenhuma foi realizada aqui.

## Histórico de rodadas anteriores

Os registros abaixo preservam evidência datada. Contagens, indisponibilidade antiga de ferramentas e situações remotas refletem sua rodada; o parecer e as tabelas acima são a referência atual. O histórico legível de respostas da sessão está em `HISTORICO_FECHAMENTO_BETA_RC1.md`.

## Correções da revisão final — 2026-10-31

- Telefone internacional explícito preservado, catálogo explícito de erros sem heurística de acentos e precedência de campo obrigatório. Maps separa embed de navegação, valida destinos/caminhos esperados e gera pesquisa somente com endereço textual apropriado; teste XSS original preservado.
- Migração verifica índice/constraint homônimo antes de atualizar dados; recusa definição incompatível. Limites Python/SQL para Unicode e whitespace e necessidade de janela sem escritas foram documentados em `docs/UX_RODADA_20261031.md`.
- Cadastro e atualização tratam somente violações únicas identificadas como e-mail; outros IntegrityErrors não são mascarados. Testes de corrida determinística em duas sessões e de classificação do driver passaram em SQLite/PostgreSQL descartável.
- PDF registra exportação após geração bem-sucedida, usa limite conservador de largura da fonte e tem testes de múltiplas páginas, escaping, offsets e auditoria em falha. Modal foi preservado, com testes de foco inicial, Tab/Shift+Tab, Escape e retorno do foco. E2E de e-mail inválido comprova apresentação amigável.
- Validação final: SQLite 235 testes (7 skips: 6 anteriores e 1 caso específico de PostgreSQL); PostgreSQL 235 testes (2 skips anteriores); JavaScript 26/26; audits npm/pip sem vulnerabilidades; migração/paridade PostgreSQL 7/7; E2E direcionados de modal/e-mail 4/4 e XSS 2/2; matriz Playwright completa 63/63 em Windows, incluindo 320x568/390px/desktop. O cenário XSS continuou com as assertions originais; corrigido o fallback de endereço que o afetava. `git diff --check` nos arquivos da revisão aprovado. AGENTS.md e GUIA.md preservados; nenhum Ruflo/Graphify, staging, commit, push ou deploy.

## Rodada controlada de UX — 2026-10-31

- Identidade de e-mail: trim/lowercase em schemas, persistência e consultas; nova revisão Alembic `20261031_01` com preflight de colisões e índice único funcional, sem unir contas ou editar revisões anteriores. Testes de login/cadastro/recuperação, colisão legada, preservação de aliases e paridade de schema.
- Apresentação de erros: mensagens de validação traduzidas e códigos HTTP removidos da mensagem ao usuário; status e tipo/localização de validação preservados para diagnóstico sem dados enviados. Transporte recebe mensagem amigável.
- Home: skeletons removidos em finally e recriados no início; hidden respeitado nos grids; apenas Todos na UI; categorias internas preservadas; telefone da API com WhatsApp e endereço com Maps validado. Teste E2E de sucesso/erro e contatos em desktop/320px.
- Conta: diálogo acessível com senha atual e autorização original; PDF autenticado reutiliza a exportação JSON, que continua disponível. Testes verificam exclusão em modal, download, PDF e isolamento de dados. Limite de repertório da fonte PDF, estratégia de migração e plano futuro de confirmação de e-mail documentados em `docs/UX_RODADA_20261031.md`.
- Navegação: scroll suave, offsets e prefers-reduced-motion já existiam; teste adicional verifica menu mobile fechado, seção não coberta e reduced-motion em 320px.
- Validação final: SQLite 225 testes (6 skips preexistentes); PostgreSQL 16 descartável 225 testes (2 skips preexistentes); Node 23/23; audits npm/pip sem vulnerabilidades; migrações/paridade PostgreSQL 7/7; Playwright completo 61/61 em Windows, incluindo 320x568/390px/desktop; direcionados de home/modal/navegação/PDF aprovados. PDF binário e isolamento do titular aprovados nos dois bancos. `git diff --check` restrito aos arquivos da rodada aprovado. Não houve staging, commit, push ou deploy. Não foram consultados dados reais nem realizado envio real de e-mail nesta validação.

## Overflow administrativo confirmado no Linux — 2026-10-30

- Reproduzidas as duas falhas remotas: Firefox/WebKit 320x568, documento de 349px para viewport de 320px. A imagem Linux Playwright 1.64.1 usava inicialmente WenQuanYi como sans-serif; com DejaVu Sans instalada no ambiente descartável, a falha de 349px apareceu nos dois browsers. Isso explica por que as inspeções anteriores e o Windows não a reproduziram. Nenhuma fonte ou dependência do projeto foi alterada.
- Origem medida: tabela de auditoria com largura mínima intrínseca de 339,25px (Firefox) / 339,28125px (WebKit), borda direita em 349,25px / 349,28125px. Seu wrapper `.management-list` tinha 300px e `overflow-x: visible`; o excesso propagava-se por `#auditoria`, `main`, `body` e documento. Navegação e date-roll já continham sua rolagem local e não eram a origem.
- Correção: uma regra em `admin-workspace.css`, `#auditoria > .management-list { overflow-x: auto; }`. Após a correção, `documentElement.clientWidth = scrollWidth = 320` nos dois browsers; wrapper 300px, conteúdo 339px, `scrollLeft` alcança 39px. A tabela permanece acessível por rolagem local; nenhuma assertion ou teste foi alterado.
- Testes Linux direcionados: Firefox/WebKit 320x568 (2 aprovados), Chromium 320x568 e Chromium/Firefox/WebKit 390x844 (4 aprovados), com `responsive-a11y.spec.mjs` original, sem instrumentação. As medidas de ancestrais foram temporárias e removidas do workspace ao concluir o diagnóstico.
- Matriz Linux completa após a correção: `npx playwright test --config frontend/e2e/playwright.config.mjs`, 59/59 aprovados (3,9 minutos), com Python 3.14, browsers Playwright 1.64.1 e DejaVu Sans no contêiner descartável. A suíte foi executada pelos mesmos testes/configuração versionados, sem alterações nas assertions. `git diff --check` nos arquivos desta correção aprovado.

## Correções direcionadas de CI — 2026-10-30

- E2E: `chooseSlot` seleciona os cards pelos títulos exatos `Corte E2E` e `Barbeiro E2E Fictício`, exigindo um único resultado. Os quatro casos de reserva/conflito em desktop/mobile passaram. O serviço longo tem apenas um profissional associado na fixture; seu seletor foi preservado.
- Harness PostgreSQL: fecha sessões antes do reset e descarta o pool após DROP/CREATE, evitando reutilizar conexões com prepared statements anteriores aos novos OIDs dos ENUMs. Produção e configuração de prepared statements não foram alteradas. PostgreSQL 16 descartável iniciado nesta rodada: 13 testes direcionados aprovados e suíte completa aprovada (221 testes, 2 skips preexistentes). O reset antigo passou no módulo de autorização isolado: a hipótese de OID depende do histórico da suíte, não foi reproduzida isoladamente nesta rodada.
- SQLite: `python -m unittest discover -s tests` com Python 3.14.7: 221 testes, 6 skips preexistentes, sem falhas. PostgreSQL executou o mesmo comando, com `BOOKING_TEST_BACKEND=postgresql` e URL exclusiva do contêiner descartável.
- JavaScript/audits: `node --test frontend/tests/*.test.mjs` (22 aprovados), `npm audit --audit-level=low` (0 vulnerabilidades) e `pip-audit -r backend/requirements.txt` (nenhuma vulnerabilidade conhecida). Dependências e lockfile preservados.
- Responsividade: medição Windows em Firefox/WebKit a 320px mostrou `documentElement.scrollWidth = clientWidth = 320`. Medição adicional na imagem Linux oficial Playwright 1.64.1, com HTML administrativo, nome e datas preenchidos, também mostrou 320/320 nos dois navegadores. Navegação e datas excedem somente seus contêineres roláveis; CSS preservado por ausência de reprodução do overflow.
- WebKit: Tab padrão percorre campos/botão e volta ao documento, omitindo links. O teste agora verifica quatro movimentos explícitos de ida/volta no formulário, exige o destino correto e mantém a assertion de foco visível; teste direcionado aprovado.
- RF13: a matriz completa revelou `Execution context was destroyed` ao consultar localStorage durante o redirecionamento do login. A espera agora usa a URL administrativa e o nome exato do barbeiro antes da navegação seguinte. Casos direcionados desktop/mobile aprovados.
- Validação final Playwright: `npx playwright test --config frontend/e2e/playwright.config.mjs` passou com 59/59 testes em Windows, após a correção RF13. A matriz inclui 50 casos funcionais desktop/mobile e 9 casos responsivos Chromium/Firefox/WebKit. Nenhum teste foi desativado e nenhum sleep foi adicionado. A medição Linux foi uma inspeção de layout adicional, não uma execução integral dessa matriz em Linux.
- CI remoto: consulta pública confirmou que `main` (run 41007129252) e os PRs Dependabot #20–#23 falham nos testes Playwright/PostgreSQL, enquanto SQLite e audits passam. Logs completos retornaram HTTP 403 sem autenticação. As falhas compartilhadas apontam para a base; não se validou a compatibilidade das atualizações major, especialmente bcrypt 5. Nenhuma atualização foi aplicada.
- `git diff --check` global aponta whitespace preexistente em `AGENTS.md:19`, preservado por instrução explícita. Os arquivos desta entrega passam na checagem restrita.

## Fechamento RF23 / RNF-14 — 2026-11-01

- Matriz de evento → gerador → metadados → perfil → teste → lacuna em `AUDITORIA_RF23_RNF14.md`. RF23 e RNF-14 classificados como Implementado no escopo especificado, sem garantia adicional de auditoria durável durante indisponibilidade de armazenamento.
- TDD demonstrou quatro lacunas: login com senha errada perdia ator conhecido; edição administrativa de cliente não gerava evento; API key não era filtrada; período com datetime offset/naive causava TypeError. Correções pontuais em `auth.py`, `users.py`, `core/audit.py`, `admin.py`; sem schema, dependências, alterações de regras de negócio ou redesenho.
- SQLite: suíte ampla com 265 testes, 7 skips previstos, sem falhas (241,064 s). Essa execução precedeu o ajuste final de timezone; após esse ajuste, 34 testes direcionados (`test_audit` e `test_audit_catalog`) passaram em SQLite e PostgreSQL 16 descartável (34/34, nenhum skip). Node: 26/26 aprovados. A revisão isolada final não encontrou bloqueadores. Filtros, IP/UTC, segregação por perfil, metadados sem credenciais, retenção dry-run e expurgo real foram validados. Dados inteiramente fictícios e contêiner PostgreSQL removido após os testes.
- Persistência best-effort e aviso sanitizado em falha foram preservados. Coleta externa/agendamento de retenção na instalação não foram executados nem declarados comprovados. RF06 permanece separado e a validar no ambiente publicado. Graphify atualizado por AST; sem commit, push ou deploy.

## Migrações antes do startup no Render Free — 2026-10-31

- Implementado em `backend/app/render_start.py` e conectado ao `startCommand` do `render.yaml`: Alembic upgrade até head, verificação da revisão e substituição do processo por Uvicorn somente após sucesso. A composição de `PASSWORD_RESET_URL`, a porta e `--no-proxy-headers` foram preservadas. `/ready` e o lifespan não foram alterados; o build continua sem acesso ao banco.
- O Free não oferece Shell/SSH, jobs avulsos ou pre-deploy. Em cada início/reinício o launcher verifica migrações; em head, revisões não são reaplicadas. Falha retorna código não zero sem traceback ou dados privados e impede que a nova API seja iniciada.
- Evidência: `test_render_start.py`, 3 testes aprovados com SQLite temporário, cobrindo banco vazio, em head e desatualizado; revisão inválida; conflito real na migração de identidade; preservação de contas; `/ready` antes/depois e Uvicorn iniciado somente após head. A fronteira do servidor é substituída por um módulo de teste no subprocesso, sem servidor externo. Suíte Python/SQLite completa: 238 testes, 7 ignorados, sem falhas (174,875 s, Python 3.14.7); Node: 26 testes aprovados. YAML validado com PyYAML no ambiente virtual e checagem de whitespace dos arquivos da alteração aprovada.
- Validação PostgreSQL 16 posterior: Docker Desktop estava fechado; a configuração era válida e o erro de leitura de `config.json` vinha da sandbox. Iniciar apenas o Desktop restabeleceu o Engine, sem editar configuração/serviço Windows ou remover recursos existentes. Um contêiner exclusivo `postgres:16-alpine`, com porta somente em localhost, credencial efêmera, banco `*_test` e schemas isolados, validou o launcher existente nos estados vazio, head, desatualizado e conflito real de dados. Vazio/desatualizado: `/ready` 503 -> 200; head: 200 -> 200; falha: código não zero, fronteira Uvicorn não alcançada, `/ready` 503 e contas/revisão anterior preservadas. Reutilizou-se `_start` de `test_render_start.py` em harness temporário via stdin, com servidor substituído pelo verificador de head existente. Regressão adicional `PostgreSQLSchemaMigrationTests`: 1 teste aprovado, 0 falhas, 0 erros, 0 skips, incluindo upgrade repetido e paridade modelos/schema. Contêiner exclusivo encerrado com remoção automática; implementação preservada.
- Encerramento do harness temporário: após os cenários e a regressão aprovados, a limpeza manual do schema foi repetida pelo callback `atexit` depois de encerrar o contêiner, gerando `ConnectionTimeout` somente nessa limpeza duplicada. O processo terminou com código 0 e a consulta Docker filtrada pelo label exclusivo confirmou ausência do contêiner. Essa ocorrência não veio do launcher; em nova execução do harness, desregistrar o callback após a limpeza manual, antes de remover o contêiner.
- Limites: Render online não executado. Migrações precisam manter compatibilidade com a versão anterior ainda atendendo, e falha/rollback de deploy não desfaz alterações já confirmadas no banco. O `/ready` da versão anterior pode falhar após avançar o schema, pois exige revisão exata; não há garantia de zero downtime. Um único serviço deve coordenar migrações nesse banco; não há lock para migradores concorrentes. A criação do administrador segue separada. Nenhum banco real, secret ou recurso Render foi alterado; sem commit, push ou deploy. Graphify não foi atualizado nesta validação porque não houve mudança de código.

## Atualização técnica Render — 2026-10-30

- Preparação inicial (histórica): Static Site, Web Service Python, PostgreSQL 16 e `/ready`. A proposta de Alembic em pre-deploy foi abandonada por incompatibilidade com Free; o fluxo atual usa `app.render_start` no startCommand.
- O frontend mantém o fallback local; `frontend/scripts/build-static.mjs` exige origem pública HTTPS e injeta configuração somente no artefato de build. Cobertura específica em `frontend/tests/static-build.test.mjs`.
- Produção agora exige `ALLOWED_HOSTS`, aplicado por `TrustedHostMiddleware`; `/docs`, `/redoc` e `/openapi.json` são desativados em production. Validação final: suíte SQLite 208 executados, 0 falhas e 6 ignorados; configuração/produção/host/readiness 47 aprovados; Node 22 aprovados; E2E RF13 2 aprovados (desktop/mobile). PostgreSQL/Render online não executados.
- IP para rate limit/auditoria: `direct` ignora headers e usa o peer do socket; o Blueprint Render define explicitamente `cf-connecting-ip`, validado como um IP único, e Uvicorn inicia com `--no-proxy-headers`. A confiança depende do comportamento documentado da borda Render/Cloudflare; precisa de confirmação operacional no primeiro deploy, sem registrar IPs em logs. A CSP do frontend está limitada a `frame-ancestors 'none'` até validar o import map inline, jsDelivr, logos externos e Google Maps.
- O Blueprint Free resolve hosts e URLs por `fromService` e compõe `/pages/reset.html` na inicialização, sem Alembic ou `preDeployCommand`. Usa `EMAIL_TRANSPORT=brevo_api`; somente `BREVO_API_KEY` e `EMAIL_FROM` são solicitados no painel. SMTP continua como padrão para outras instalações. Provisionamento, remetente autorizado/chave no Render, migrations operacionais, criação interativa do primeiro administrador e validação online seguem pendentes.
- Validação da adaptação Brevo: 68 testes Python relevantes aprovados (7 Brevo, 18 configuração, 21 configuração da aplicação/produção, 8 recuperação, 7 segurança/rate limiting e 7 JWT), com SQLite temporário; 4 testes Node de build estático e fragmento aprovados. YAML e referências entre serviços validados localmente com PyYAML; CLI/validação online Render, PostgreSQL e entrega externa não executados. `git diff --check` dos arquivos da implementação sem erros; a verificação global aponta somente whitespace preexistente em `AGENTS.md:19`, preservado.

Integração HOME/motion: catálogo, auth e contatos mantidos em home.js; apresentação GSAP e vídeo separados. Evidências e testes em docs/HOME_MOTION_INTEGRATION.md. Sem publicação.

Estrelinha cinematográfica: três aparições decorativas, com flag por instalação, canvas compartilhado e reduced-motion; detalhes e validação em docs/ESTRELINHA_CINEMATICA.md.

## Workflow Codex — 2026-11-02

- Regras atuais preservadas em `AGENTS.md`, com plano explícito apenas para mudanças complexas e reforço de banco descartável de teste; marcador vazio com whitespace removido.
- Área existente `docs/superpowers/plans/` reutilizada com modelo curto; decisões confirmadas da HOME em `specs/home-experience.md`. `GUIA.md` alinhado à arquitetura single-tenant, sem reescrita geral.
- Hook do Graphify preservado; check de whitespace após `apply_patch` acrescentado em `.codex/hooks.json`, sem testes pesados automáticos. Ativação depende da revisão de confiança via `/hooks`; comando validado diretamente.
- Diferença entre instruções e sandbox/aprovações documentada em `tools/codex-helpers/README.md`. Sem mudança de permissões globais, dependências, banco, produção ou aplicação.
- Validação: JSON dos hooks e preservação exata do handler Graphify conferidos com Python; UTF-8/whitespace dos oito arquivos (incluindo untracked) e quatro links locais validados; `rtk proxy git diff --check` com código 0. Arquivos de frontend previamente modificados preservados por comparação de hashes. Suítes Python/Node da aplicação, Playwright e PostgreSQL não executadas: mudança restrita a documentação/configuração de hook.

Diagnóstico Ritual Chrome/Edge (2026-11-02): sem correção na HOME. Probe em ambos os canais instalados: scrub contínuo em 1440x900; três tempos em 1440x640 por seleção responsiva. Zero writes durante seeking. Playwright HOME desktop/mobile: 4/4. Causa da sessão manual pendente de confirmação da viewport/modo; evidência e coleta em docs/RITUAL_CROSS_BROWSER_DIAGNOSTICO.md.


## Integração independente — 2026-11-04

Implementados: nomes NFC; testes de identidade sem dependência de cooldown;
visibilidade acessível; correções administrativas.
SQLite:290 aprovados/12 ignorados; PostgreSQL descartável:300/2;
Node:34; visibilidade Playwright:32; essenciais finais:56.
Primeira rodada essencial55/56, com corrida preexistente de redirecionamento
documentada. Recuperação/JWT/sessões/migrações iguais a main.
Evidências em
[integração independente](INTEGRACAO_QUALIDADE_AUTH_UX_INDEPENDENTE_20261104.md).
Sem publicação, migração real, e-mail real ou instalação de dependências.

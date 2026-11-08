# Histórico das respostas — fechamento beta até v1.0.0-rc.1

Registro solicitado pelo proprietário em 2026-11-01. Organiza os textos explicativos e resultados disponíveis da sessão desde a auditoria formal de fechamento da beta; as rodadas anteriores estão condensadas, portanto não é uma transcrição literal/integral da interface. As conclusões antigas representam aquele momento; o parecer atual fica no último bloco, com saídas relevantes dos comandos. Não inclui dumps de arquivos lidos, instruções internas ou todos os traces do terminal. Não contém credenciais nem tokens reais.

## 1. Auditoria para fechamento da beta

### Mensagens de acompanhamento

Vou confrontar os requisitos e o checklist com a main, o código e os testes atuais. Usarei Graphify primeiro para direcionar a leitura e manterei separadas as lacunas reais, as pendências operacionais e as anotações antigas já superadas. Esta rodada será somente análise, sem alterações ou execução de suítes.

A main está no commit aprovado 218575f, sem alterações locais no código da aplicação. A documentação ainda mistura evidências antigas e recentes: RF13/RF14, PostgreSQL, navegadores e startup Free aparecem como pendentes em alguns trechos. As pendências que ainda precisam de atenção se concentram no aceite operacional — recuperação de senha real, backup/restauração, alertas e configuração da L20 — e na cobertura da auditoria, não em refazer funcionalidades já concluídas.

### Registro da resposta final

**SIM COM RESSALVAS: o projeto pode entrar em fase de Release Candidate.** O menor caminho agora é fechar evidências de aceite e operação da L20, sem reabrir funcionalidades concluídas.

A análise considera a main em 218575f, sincronizada com a referência local origin/main, e o deploy saudável informado por você. As alterações locais em AGENTS.md e arquivos não rastreados não fazem parte dessa versão. Não alterei arquivos nem executei testes nesta rodada.

**1. RF: 22 completos, 1 parcial de evidência e 1 a validar**

| RF | Situação naquele momento |
|---|---|
| RF01 — Catálogo | Completo |
| RF02 — Informações institucionais | Completo |
| RF03 — Média de avaliações | Completo |
| RF04 — Cadastro e consentimento | Completo |
| RF05 — Autenticação/autorização | Completo |
| RF06 — Recuperação de senha | A validar: entrega real pela Brevo e redefinição no ambiente publicado |
| RF07 — Disponibilidade | Completo |
| RF08 — Agendamento | Completo |
| RF09 — Cancelamento | Completo |
| RF10 — Reagendamento | Completo |
| RF11 — Histórico | Completo |
| RF12 — Avaliação | Completo |
| RF13 — Agenda diária | Completo, incluindo isolamento por perfil e E2E |
| RF14 — Registro de atendimento | Completo, incluindo matriz de transições |
| RF15 — Agendamento manual/avulso | Completo para Admin/Barbeiro |
| RF16 — Serviços | Completo |
| RF17 — Associação barbeiro-serviço | Completo |
| RF18 — Jornadas/bloqueios | Completo |
| RF19 — Gestão/bloqueio de clientes | Completo |
| RF20 — Gestão institucional | Completo |
| RF21 — Financeiro | Completo |
| RF22 — Moderação | Completo |
| RF23 — Auditoria | Parcial de evidência: consulta e eventos implementados; falta fechar cobertura dos eventos obrigatórios |
| RF24 — Portabilidade | Completo |

RF23 não representa uma funcionalidade inteira ausente. O código e os testes já cobrem autenticação, consulta restrita, filtros, paginação, ausência de segredos, falha de persistência e retenção em dry-run. A ação mínima é identificar e testar os casos obrigatórios restantes, sem redesenhar a auditoria.

**2. RN: 5 de 5 completas**

RN01 — Jornada, bloqueios, conflito e duração: completa. RN02 — Antecedência de 24h e dois reagendamentos pelo cliente: completa. RN03 — Janela de 14 dias: completa. RN04 — Avaliação única pelo titular após conclusão: completa. RN05 — Snapshot de preço/duração: completa.

Não há evidência para transformar essas regras em nova implementação.

**3. RNFs: 11 implementadas e 7 ainda parciais**

| RNF | Avaliação naquele momento |
|---|---|
| RNF01 | Atomicidade implementada, com evidência PostgreSQL |
| RNF02 | Credenciais/tokens implementados; especificação antiga precisa refletir Argon2 e compatibilidade bcrypt |
| RNF03 | Responsividade implementada e validada |
| RNF04 | Controles LGPD implementados; prazos/responsabilidades dependem da instalação |
| RNF05 | RBAC/propriedade implementados |
| RNF06 | Parcial operacional: registrar HTTPS/cabeçalhos no ambiente final |
| RNF07 | Força bruta implementada; ensaio multiworker não bloqueia a instalação atual |
| RNF08 | Implementada com benchmark local; falta aceite representativo na instalação-alvo |
| RNF09 | Parcial de aceite: motores validados; falta evidência dos navegadores de marca exigidos |
| RNF10 | Persistência/migrações implementadas; descrição de rollback divergente |
| RNF11 | Validação/XSS/SQL implementados |
| RNF12 | CORS implementado; corrigir nome antigo da variável |
| RNF13 | Parcial operacional: responsáveis, custódia e calendário de rotação |
| RNF14 | Parcial: cobertura obrigatória restante e comprovação do expurgo |
| RNF15 | Parcial: rotina diária externa e restauração ainda sem comprovação |
| RNF16 | Dependências/audits implementados; evidências recentes substituem pendências antigas |
| RNF17 | Parcial operacional: endpoints/métricas existem; alerta externo não comprovado |
| RNF18 | Parcial: responsáveis e exercício com RPO/RTO medidos |

Validar startup/migrações no PostgreSQL não equivale a validar backup/restauração.

**4. P0 — impedimentos de entrega**

Nenhum bug P0 de código foi confirmado. Há dois gates operacionais antes de entregar para uso com dados reais: banco permanente para a L20 e backup recuperável. Confirmar destino durável; comprovar backup diário, retenção de 30 dias, cópia externa e restauração isolada. O PostgreSQL Free do Render expira após 30 dias e não oferece backup gerenciado. O plano efetivo no painel não foi consultado. Esses gates não impedem RC controlada de homologação.

**5. P1 — resolver antes da v1.0.0**

- Validar entrega Brevo e redefinição completa.
- Fechar cobertura dos eventos obrigatórios e expurgo.
- Aceite no endereço final: login, renovação, logout, CORS e cookie.
- Registrar HTTPS, redirect, HSTS, CSP e demais cabeçalhos.
- Configurar monitor externo e testar recebimento do alerta.
- Preencher responsáveis, custódia, rotação e recuperação.
- Smoke breve em Chrome, Firefox, Safari e Edge, reaproveitando Playwright.
- Medição representativa da disponibilidade no ambiente-alvo.
- Conferir administrador, profissionais, serviços, preços, jornadas, contatos e termos da L20.
- Consolidar documentação e identificar candidato por commit/tag.

O cookie de refresh continua SameSite=Lax. O aceite precisa confirmar a sessão nos domínios efetivamente usados; /ready=200 sozinho não demonstra esse fluxo.

**6. P2/P3**

P2: ensaio de contenção do rate limit entre múltiplos workers, caso a instalação passe a utilizá-los. P3: nenhum novo item obrigatório demonstrado. Não criar backlog de features/refatorações nesta fase.

**7. Documentos desatualizados**

RASTREABILIDADE: RF13/RF14 parciais e PostgreSQL/Firefox/WebKit indisponíveis. REQUISITOS_STATUS: tabelas e “Dez maiores lacunas” antigas. CHECKLIST_PRODUCAO: ausência de deploy e migração manual/SMTP. REQUISITOS: bcrypt versus Argon2, ALLOWED_ORIGINS versus CORS_ALLOWED_ORIGINS, downgrade genérico versus recusa deliberada. PLANO_RECUPERACAO_DESASTRES: disponibilidade do PostgreSQL ficou antiga; restauração e responsáveis continuavam pendentes.

A atualização deve separar registro histórico de estado atual.

**8. Checklist mínimo para RC**

Consolidar contagens; corrigir contradições documentais; vincular ao commit/evidências; smoke integrado com recuperação e sessão; pendências P0/P1 com responsável/critério; preparar v1.0.0-rc.1 sem arquivos locais. Não repetir suítes/audits sem mudança que invalide evidências.

**9. Checklist mínimo v1.0.0**

Fechar gates P0 e P1; demonstrar restauração e RPO/RTO; aceite L20 para os três perfis; entregar configuração, suporte e recuperação; release notes/tag; revalidar componentes alterados desde a RC.

**10. O projeto pode entrar em RC? SIM COM RESSALVAS.** Base funcional e startup maduros. Fechamento exige aceite real e operação comprovada; entrega definitiva não estava concluída.

## 2. Validação RF06

### Acompanhamento

Vou localizar o fluxo e os testes com Graphify, verificar a regressão focada e conferir quais acessos estão disponíveis para o aceite publicado. Não enviarei e-mails nem alterarei senhas sem uma conta de teste autorizada; se faltar acesso, pararei nessa fronteira com uma única ação concreta.

### Registro da resposta final

**RF06 permanece “A validar” no ambiente publicado.** Nenhuma regressão foi detectada nas suítes existentes; falta comprovar entrega e uso real do link.

Evidências desta rodada:

- 15 testes Python aprovados: resposta uniforme, transporte Brevo simulado, URL com token no fragmento, validade de uma hora, expiração, uso único e falhas de envio.
- 2 testes Node aprovados: leitura pelo fragmento e rejeição pela query string.
- Sonda local SQLite: solicitação existente/inexistente 200, redefinição 200, senha antiga 401, senha nova 200, reutilização 400.
- A primeira sonda não atingiu retorno esperado com endereço fictício .test; passou após ajustar apenas essa entrada para example.com. Nenhum arquivo alterado.

Fronteira externa: sem URL pública confirmada e conta de teste identificada como sua. Resposta 200 não comprova entrega, pois falha de transporte também responde uniformemente.

Uma ação: enviar URL pública do frontend e e-mail de conta de teste própria autorizada. Não enviar senha, chave, link de recuperação ou token.

Arquivos alterados: nenhum. Status preservado. Nenhum e-mail real enviado, secret lido ou commit/push/deploy executado.

## 3. Fechamento RF23 / RNF-14

### Acompanhamento

Vou mapear os eventos e testes existentes antes de alterar qualquer coisa. Usarei Graphify para direcionar a leitura e TDD apenas nas lacunas demonstradas, preservando a arquitetura de auditoria e as regras de negócio.

A matriz preliminar mostra os pontos de emissão já presentes para autenticação, reservas, serviços, jornadas, bloqueios, moderação, institucional, associações e LGPD. Encontrei duas lacunas concretas: senha errada de conta conhecida registra ator anônimo; edição administrativa de nome/e-mail não gera evento. As demais lacunas identificadas são de cobertura.

O teste confirmou as duas lacunas e revelou que o sanitizador não removia BREVO_API_KEY. Correções pontuais sem mudar respostas, permissões ou transações de negócio. Filtros, paginação e retenção passaram sem mudança.

A revisão encontrou uma borda no período: misturar datas com e sem fuso causava erro 500. O caso foi reproduzido e normalizado para UTC somente nos filtros da auditoria, sem alterar agendamentos.

### Registro da resposta final

**RF23 e RNF-14 foram classificados como Implementados**, com evidências e limites registrados.

A matriz completa em AUDITORIA_RF23_RNF14.md relaciona evento, gerador, metadados, perfil, teste e lacuna. Cobre autenticação, cancelamentos, reagendamentos, ações administrativas e o catálogo solicitado.

TDD demonstrou quatro lacunas:

- Login malsucedido de conta conhecida perdia ator.
- Edição administrativa não gerava evento; agora só nomes dos campos alterados.
- Sanitizador não removia API keys.
- Período com timezone misto causava erro 500; normalizado para UTC.

Arquitetura, schema, permissões e regras preservados.

Estado final: 34 testes focados SQLite e 34 PostgreSQL 16 descartável aprovados, sem skips. Regressão ampla SQLite: 265 testes, 7 skips previstos, antes do último ajuste de timezone. Node: 26 aprovados. Diff check aprovado. Revisão sem bloqueador.

Alterados core/audit.py, routers auth/users/admin, testes, README, matriz/status/rastreabilidade; Graphify atualizado.

Limite preservado: persistência best-effort pode perder linha durante falha de armazenamento e gera aviso sanitizado. Sem garantia zero perda ou comprovação de agendamento/coleta externa.

Nenhum banco real ou secret acessado. Alterações locais preservadas. Sem commit/push/deploy.

## 4. Preparação operacional RNF-15 / RNF-17 / RNF-18

### Acompanhamento

Vou auditar scripts e procedimentos, identificar o que pode ser ensaiado localmente e validar restauração apenas em PostgreSQL descartável. Evidências locais e pendências externas serão separadas.

Já existem dump consistente, age, checksum, manifesto e restauração com revisão/contagens. Faltavam evidências completas; o script aceitava retenção menor que 30 dias. Corrigido com teste antes. Ferramentas ausentes no host foram usadas apenas em contêineres descartáveis.

O primeiro ensaio parou por dependência omitida na cópia mínima dos fontes e limpou os recursos. A repetição incluiu o arquivo. Nenhum destino, monitor ou serviço pago configurado.

O ensaio passou: PostgreSQL 16, pg_dump, age, checksum e rsync reais; restore a partir da cópia do receptor, head 20261031_01 e 14 contagens; corrupção rejeitada. Restore de 1,673 s em massa mínima não comprova RTO real.

### Registro da resposta final

**A preparação local foi validada; a ativação operacional parou na escolha do destino, executor e responsável.**

Comprovei em PostgreSQL 16 descartável backup pg_dump/age/checksum/manifesto, rsync para outro contêiner e restore da cópia, revisão 20261031_01, 14 tabelas e dados fictícios, rejeição de corrupção e remoção dos recursos.

Restauração em 1,673 s, sem comprovar RTO integral. Retenção inferior a 30 dias corrigida via TDD antes do acesso ao banco.

Validações: 4 testes de backup, 9 de health/readiness/observabilidade e 26 Node aprovados. Diff check aprovado; Graphify atualizado.

| Requisito | Estado | Pendência externa |
|---|---|---|
| RNF-15 | Parcial | Job diário, destino fisicamente externo, custódia e retenção real de 30 dias |
| RNF-17 | Parcial | Monitor e recebimento de alertas |
| RNF-18 | Parcial | Responsáveis e ensaio representativo de RPO/RTO |

Opção mínima: executor externo existente e sempre ligado, destino controlado pela instalação via rclone/rsync SSH, UptimeRobot Free com 5 minutos se aceito, responsável nominal/suplente/canal. Metas RPO ≤24h e RTO ≤4h. YAML ainda declara PostgreSQL Free, que expira após 30 dias; não é destino permanente. Nenhum plano alterado.

Para avançar: indicar executor, destino e nome/canal do responsável, sem credenciais.

Scripts/testes e documentação atualizados. Nenhum banco/backup real alterado, nenhum serviço externo configurado. Sem commit/push/deploy.

## 5. Validação formal v1.0.0-rc.1 — 2026-11-01

### Mensagens de acompanhamento

As validações passaram: backend em SQLite e PostgreSQL descartável, backup/restore e auditorias de dependências. Os 63 cenários Playwright também passaram entre a execução completa e a repetição isolada do Firefox; a primeira execução teve três quedas do navegador antes de abrir páginas.

Vou registrar esses resultados nos três documentos de controle, distinguindo as evidências locais das pendências no ambiente publicado, e concluir o histórico solicitado.

Não foi demonstrada falha P0/P1 no código candidato. Permanecem ressalvas externas para a entrega comercial: recuperação de senha no ambiente publicado, backup diário externo, monitor com alertas, responsáveis operacionais e verificações do host.

O parecer será “APROVADA COM RESSALVAS” para UAT controlado, sem declarar prontidão irrestrita para dados reais. Também vou corrigir os registros antigos que ainda dizem que PostgreSQL, Firefox/WebKit e RF13/RF14 não foram validados.

### Identificação do candidato

- Branch: main.
- HEAD: 218575f202e897a92f23cd4ee23091c2b1438045.
- Candidato: working tree incluindo correções anteriores locais de auditoria e backup; não apenas o commit acima.
- SHA-256 do recorte de 178 arquivos de aplicação/testes/migrations/frontend/backup/manifests, antes e depois das validações: 1723a723dca17bc10c6f3ee428a4d96c68e1e201d021b8dae447de0b9df691f8.
- Nenhuma alteração de código, nova feature ou migration nesta rodada RC. Alterações desta rodada restritas aos três controles documentais e a este registro.
- Impressão do recorte serve à comparação local; não representa checksum de artefato publicado ou de arquivos alheios.

### Saídas relevantes preservadas

Backend SQLite, suíte completa, exit 0:

```text
Ran 266 tests in 294.012s

OK (skipped=7)
```

Backend PostgreSQL 16, suíte completa em harness descartável, exit 0:

```text
PostgreSQL 16 full suite: tests=266, failures=0, errors=0, skips=2
Disposable PostgreSQL cleanup: OK
No real database or credentials accessed.
```

Os skips são condicionais por dialeto. PostgreSQL usou banco temporário *_test, porta apenas localhost e credencial aleatória em memória. Não leu DATABASE_URL real. Inclui migrations vazio/anterior/head, paridade, concorrência/double booking, auth/RBAC, reset local, LGPD, auditoria e RF13/RF14.

Node:

```text
rtk proxy node --test frontend/tests/*.test.mjs
26 testes aprovados; exit 0
```

Backup/retenção/filesystem:

```text
rtk proxy backend/.venv/Scripts/python.exe -B -m unittest discover -s tools/backup -p test_backup.py
4 testes aprovados; exit 0
```

Ciclo real de backup/restauração no harness com PostgreSQL 16 e receptor isolados, exit 0:

```text
PASS encrypted backup: pg_dump custom + age + checksum + manifest + rsync to separate receiver container.
PASS restore from receiver copy: Alembic head=20261031_01; table_counts=14; fixture preserved; elapsed_seconds=3.339
PASS generated restore database removed; source database preserved.
PASS corrupted ciphertext rejected before restore.
Local complete-cycle elapsed_seconds=3.83
ALL BACKUP/RESTORE CHECKS PASSED.
Disposable container cleanup: OK
Disposable container cleanup: OK
Disposable network cleanup: OK
```

A massa é mínima e fictícia; dois contêineres no mesmo host não comprovam cópia física externa nem RPO/RTO real. Recursos criados exclusivamente para teste, removidos sem tocar em recursos preexistentes.

Playwright:

```text
rtk proxy npx.cmd playwright test --config=frontend/e2e/playwright.config.mjs
exit 1 — 60 passed, 3 failed — 4.9 min
Firefox: browserContext.newPage: Target crashed

rtk proxy npx.cmd playwright test --config=frontend/e2e/playwright.config.mjs --project=firefox-320x568 --project=firefox-390x844 --project=firefox-1280x800 --output=test-results/rc1-firefox-diagnostic
exit 0 — 3 passed — 1.1 min — fora da sandbox
```

| Projeto | Resultado |
|---|---:|
| Fluxos desktop 1280×800 | 27/27 |
| Fluxos mobile 390×844 | 27/27 |
| Chromium 320×568 / 390×844 / 1280×800 | 3/3 |
| Firefox 320×568 / 390×844 / 1280×800 | 3/3 na repetição |
| WebKit 320×568 / 390×844 / 1280×800 | 3/3 |

63 casos distintos aprovados entre execução completa e repetição; não se afirma exit 0 na primeira execução. Queda antes da página não se reproduziu fora da sandbox; hipótese ambiental, causa raiz não demonstrada. P2 operacional, nenhum bug funcional P0/P1 reproduzido. Artefatos em test-results/e2e/ e test-results/rc1-firefox-diagnostic/. Browsers instalados Chromium1248/Firefox1555/WebKit2370.

Segurança:

```text
rtk proxy npm audit --audit-level=low --json
exit 0 — 0 vulnerabilidades em todas as severidades

rtk proxy backend/.venv/Scripts/python.exe -m pip_audit -r backend/requirements.txt --format=json --progress-spinner=off
exit 0 — resolução completa — 36 dependências — 0 vulnerabilidades
```

As duas auditorias precisaram de rede liberada após restrição da sandbox. Nenhum upgrade de dependências aplicado. Scan sanitizado: 204 textos rastreados, 12 binários excluídos; 23 candidatos apenas fixtures, nenhum marcador de secret real identificado no recorte. Não abrange histórico Git ou todos os arquivos locais. Nenhum valor sensível registrado.

Render/startup: YAML atual local validado; plan Free, rootDir backend, startCommand contém python -m app.render_start, healthCheckPath /ready. Launcher só libera a fronteira Uvicorn após upgrade e revisão correta; falha bloqueia startup. Nenhum acesso ao Render, banco real, secrets ou deploy desta rodada.

Checagem de whitespace restrita aos arquivos relacionados: exit 0. A checagem global do agente frontend apontou apenas whitespace preexistente em AGENTS.md:29, preservado. Arquivos novos documentais e de testes também verificados separadamente. Nenhum staging.

### Registro da resposta final da rodada

**RELEASE CANDIDATE: APROVADA COM RESSALVAS**

Aprovada para UAT controlado com dados fictícios/contas próprias. Nenhum P0/P1 de código foi demonstrado. Permanecem bloqueadores externos antes de piloto com dados reais/v1.0:

- RF06: comprovar entrega e redefinição no ambiente publicado.
- Backup diário externo com retenção ≥30 dias, monitor/alertas, responsáveis e ensaio operacional de recuperação.
- Confirmar TLS/headers/CORS/sessão/IP da instalação, custódia/rotação de secrets e continuidade do PostgreSQL Free.
- Smoke de navegadores de marca e alinhamentos documentais normativos de hash, CORS e rollback.

Resultados: SQLite 266 (7 skips), PostgreSQL 266 (2 skips), Node26, backup4 e restore real aprovados. Playwright63 distintos aprovados entre a completa60 e repetiçãoFirefox3. pip/npm audit:0 vulnerabilidades.

Requisitos:23RF implementados/1a validar(RF06);5RN implementadas;12RNF implementados/6parciais(06,09,13,15,17,18). Documentos atualizados: REQUISITOS_STATUS.md, RASTREABILIDADE.md, CHECKLIST_PRODUCAO.md e este histórico.

Código candidato permaneceu idêntico ao início da validação; alterações locais anteriores preservadas. Graphify não atualizado nesta rodada, pois não houve alteração de código. Sem commit, push, deploy ou tag.

# Checklist de prontidão para UAT e produção

Atualizado em 2026-11-01 para **v1.0.0-rc.1: APROVADA COM RESSALVAS**, restrita a UAT controlado com dados fictícios/contas próprias até fechar as pendências externas. Candidato é o working tree sobre `main` / `218575f202e897a92f23cd4ee23091c2b1438045`, incluindo auditoria e backup locais. A identificação e os resultados estão em `REQUISITOS_STATUS.md`.

Render funcionando/deploy anterior saudável é contexto confirmado pelo usuário. Esta rodada não consultou nem publicou o candidato no Render. Não inserir credenciais, tokens, chaves ou URLs autenticadas nesta lista.

## Evidência local concluída para Release Candidate

- [x] Backend SQLite: 266 executados, 7 skips condicionais, sem falhas/erros.
- [x] Backend PostgreSQL 16 exclusivamente descartável: 266 executados, 2 skips exclusivos SQLite, sem falhas/erros; limpeza confirmada.
- [x] Banco vazio/anterior/head, upgrade repetido, paridade de schema e preservação; revisão Alembic `20261031_01`.
- [x] Concorrência/double booking, autenticação/RBAC, recuperação local, LGPD, auditoria, RF13 e RF14 cobertos pelas suítes.
- [x] Node: 26/26; testes backup/retenção/filesystem: 4/4.
- [x] Playwright: 63 casos distintos aprovados; três motores × 320×568/390×844/1280×800 e fluxos completos desktop/mobile. Completa: 60/63, exit 1, Firefox caiu antes da página; repetição somente Firefox fora da sandbox: 3/3, exit 0.
- [x] pip-audit com resolução completa: 36 dependências, 0 vulnerabilidades; npm audit: 0 em todas severidades. Nenhuma atualização de dependência aplicada.
- [x] CORS, headers, rate limiting, XSS, isolamento e RBAC validados em código/testes. Scan sanitizado de textos rastreados sem secret real identificado no recorte; não abrange histórico, binários ou todo arquivo local.
- [x] Backup PostgreSQL 16 real: pg_dump/age/checksum/manifesto, cópia rsync recebida e restore; head, 14 contagens e fixture preservados, corrupção rejeitada. Restore 3,339 s em massa mínima.
- [x] YAML Free/launcher verificados: `python -m app.render_start`, migração e verificação antes da fronteira Uvicorn; falha impede startup; `/ready` preservado e usado pelo Render.
- [x] RF01–RF24, RN01–RN05 e RNF01–RNF18 reconciliados. RF13/RF14/RF23/RNF-14 concluídos preservados; RF06 real continua A validar.
- [x] Alterações locais alheias preservadas; nenhum commit, push, tag ou deploy nesta rodada.

## Pendências para concluir UAT e liberar piloto com dados reais / v1.0

- [ ] **RF06 — P1:** com uma conta própria de teste, comprovar solicitação, resposta uniforme, entrega pelo transporte configurado (Brevo HTTPS no YAML atual), URL pública, expiração/uso único, reset, senha antiga rejeitada/nova aceita e reuso rejeitado. Não registrar token/link completo nem secrets.
- [ ] **TLS/headers/origem — P1:** medir HTTPS/TLS 1.3, redirect/HSTS/CSP/nosniff da API e frontend reais; confirmar CORS restrito, cookie HttpOnly/Secure, refresh/logout e relação entre origens. Não alterar configuração por tentativa sem evidência.
- [ ] **Borda/IP — P1:** confirmar que o serviço recebe IP confiável da borda configurada, sem headers controláveis pelo cliente, para rate limit e auditoria. Não registrar IPs reais em relatório público.
- [ ] **Banco durável — P1:** resolver a continuidade do PostgreSQL Free declarado no YAML (expiração de 30 dias, confirmada na [documentação Render Free](https://render.com/docs/free)); decisão do responsável antes de uso comercial continuado. Nenhum plano pago autorizado/configurado aqui.
- [ ] **Backup externo diário — P1 (RNF-15):** escolher executor/destino existentes, configurar agendamento, criptografia/custódia e retenção ≥30 dias, comprovar primeira cópia e alerta de falha. Dois contêineres no mesmo host são ensaio, não destino fisicamente externo.
- [ ] **Incidente/recuperação — P1 (RNF-18):** nomear operador/suplente e canais protegidos no runbook; ensaiar recuperação representativa em banco descartável e registrar tempo total. Metas RPO ≤24h/RTO ≤4h ainda não medidas na instalação.
- [ ] **Monitor externo — P1 (RNF-17):** definir conta, alvo e canal; comprovar alerta/recuperação em alvo controlado. Opção mínima anteriormente proposta: UptimeRobot Free (intervalo 5 min), se aceito pelo responsável; não sustenta prometida verificação por minuto.
- [ ] **Secrets — P1 (RNF-13):** identificar cofre/custódia, responsável e calendário de rotação por instalação; comprovar procedimento sem divulgar valores. Não presumir que a ausência de .env versionado prova operação segura.
- [ ] **Navegadores (RNF-09):** smoke nas versões comerciais estáveis de Chrome/Firefox/Safari/Edge antes do aceite final de compatibilidade; WebKit Playwright não é Safari instalado.
- [ ] **Documentação normativa — P1:** resolver redações antigas: RNF-02 cita bcrypt, implementação usa Argon2 com migração de bcrypt; RNF-12 nomeia ALLOWED_ORIGINS, variável é CORS_ALLOWED_ORIGINS; RNF-10 promete rollback genérico, migrations recusam downgrade destrutivo. Não alterar código seguro para reproduzir texto antigo.
- [ ] **Aceite e versão exata:** registrar responsável UAT, resultados e ressalvas; após autorização de integração/publicação, registrar commit/tag/artefato efetivamente entregue e CI dessa revisão. O estado remoto atual não certifica alterações locais sem commit.
- [ ] **Smoke publicado do candidato:** somente após publicação autorizada, confirmar `GET /health` e `GET /ready` 200 e fluxos essenciais com conta própria. Não simular falha de banco em produção. Falhas de conectividade/revisão já testadas isoladamente.

## Operação contínua

- [ ] Registrar execução diária/alertas de backup, retenção real de 30 dias e ensaios periódicos de restauração em ambiente descartável; nunca restaurar sobre banco real no ensaio.
- [ ] Programar retenção de auditoria e coleta/monitoramento conforme runbook; armazenamento best-effort não garante zero perda.
- [ ] Manter auditorias npm/pip, Dependabot e testes relevantes na CI; não aplicar atualização major sem validação.
- [ ] Na próxima alteração de schema, manter compatibilidade com versão anterior durante deploy. O launcher executa no start, não no build/pre-deploy; uma única instância deve coordenar migrations. /ready exige head exato; não há garantia de zero downtime ou rollback automático do banco.
- [ ] Confirmar bases legais/prazos LGPD com o controlador; manter contatos de incidente e inventário de dados em local operacional protegido.

## Histórico substituído nesta revisão

A lista antiga dizia “não implantado”, “PostgreSQL indisponível”, “Firefox/WebKit não instalados”, “RF13 sem E2E” e “RF14 sem matriz”. Esses estados não descrevem o candidato atual e foram substituídos por evidências acima. Histórico de testes e limitações datadas preservado em `REQUISITOS_STATUS.md`; respostas da sessão em `HISTORICO_FECHAMENTO_BETA_RC1.md`.

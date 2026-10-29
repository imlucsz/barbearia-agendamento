# Checklist de prontidão para produção

Este checklist reflete o que está versionado no repositório. A aplicação ainda não está implantada: itens externos precisam ser preenchidos e comprovados por instalação. Não inserir senhas, tokens, certificados privados ou URLs com credenciais neste documento.

## Pendências externas antes de publicar

- [ ] **Domínio:** registrar e apontar DNS para frontend e API. Escolher nomes no mesmo domínio registrável (por exemplo, `app.exemplo.com` e `api.exemplo.com`), necessário para a sessão baseada em cookie `SameSite=Lax`.
- [ ] **TLS/HTTPS:** contratar ou provisionar certificados no host/proxy; forçar HTTP→HTTPS, TLS moderno, HSTS e cabeçalhos de segurança também para páginas estáticas. Não há configuração real de proxy/deploy no repositório.
- [ ] **Hospedagem:** escolher host para frontend, API e PostgreSQL; manter o banco privado e exclusivo desta barbearia; configurar serviço/supervisor, firewall, atualização do SO, capacidade e monitoramento de processo. Não há unidade systemd, contêiner ou infraestrutura de produção configurada.
- [ ] **Configuração:** criar `.env` seguro fora do controle de versão; definir `APP_ENV=production`, `INSTALLATION_NAME`, `DATABASE_URL`, `SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, fuso, `TERMS_VERSION` e demais variáveis, todas próprias da instalação. Usar banco novo; não importar banco ou dados de outra barbearia.
- [ ] **Migrações/admin:** antes do startup, fazer backup do banco novo, executar `python -m alembic upgrade head`, conferir `alembic current` e criar o primeiro admin por `python -m app.initial_admin`. Não usar `/seed` em produção.
- [ ] **SMTP:** escolher provedor, validar domínio remetente, TLS e entrega; configurar usuário/senha e `PASSWORD_RESET_URL`; enviar e receber mensagem de recuperação de senha em homologação antes do lançamento.
- [ ] **CORS/sessão:** cadastrar somente a origem HTTPS do frontend em `CORS_ALLOWED_ORIGINS`; confirmar `credentials: include`, domínio registrável compartilhado e Origin permitido em refresh/logout.
- [ ] **Monitor:** escolher serviço de uptime ou cron externo e configurar verificação de `/health` a cada minuto, alerta após falhas consecutivas e alerta da taxa de 5xx. Configurar acesso protegido a `/metrics` com segredo próprio, se coletor Prometheus for usado. Exemplos estão em `MONITORAMENTO.md`; nenhum monitor foi provisionado.
- [ ] **Backup remoto:** provisionar destino separado do host de aplicação, ferramenta/conta e criptografia; preencher variáveis exigidas por `tools/backup`; proteger chave `age` e credenciais. Configurar job diário e retenção mínima de 30 dias. O repositório não cria bucket nem conta externa.
- [ ] **Restauração:** provisionar PostgreSQL descartável isolado e agendar o ensaio trimestral; comparar revisão Alembic e contagens. O teste não foi executado nesta máquina.
- [ ] **Responsáveis:** preencher os campos em `PLANO_RECUPERACAO_DESASTRES.md` para operação, backup/chaves, comunicação e retorno do serviço.
- [ ] **Segredos:** definir cofre e calendário por instalação para rodar `SECRET_KEY`, credenciais DB/SMTP e chaves de backup; validar impacto de logout e comunicação. Rotação documentada, ainda não executada.
- [ ] **Evidência de navegador:** executar os 57 projetos/casos Playwright em ambiente com Chromium, Firefox e WebKit instalados; localmente 51 passaram e 6 não iniciaram por ausência de Firefox/WebKit.
- [ ] **CI:** executar workflow GitHub Actions em PR/branch e confirmar jobs SQLite, PostgreSQL efêmero, Node, `pip-audit`, `npm audit` e Playwright verdes. A CI remota não foi executada nesta rodada.

## Verificação pós-publicação

- [ ] `GET /health` responde 200 com banco acessível e 503 genérico se o banco ficar indisponível.
- [ ] `GET /ready` responde 200 com esquema atualizado e 503 se a revisão estiver defasada.
- [ ] Fluxo de fumaça: cadastro/consentimento, e-mail de recuperação, login, agendamento, cancelamento/reagendamento, sessão renovada, exportação e logout.
- [ ] Testar bloqueio de cliente e verificar revogação imediata da sessão.
- [ ] Confirmar HTTPS/certificado, redirect, HSTS, CSP das páginas estáticas, CORS restrito e cookie HttpOnly.
- [ ] Confirmar primeiro backup, checksum, cópia fora do host e alerta de falha; completar restauração descartável antes de declarar recuperação comprovada.
- [ ] Confirmar que logs e métricas não expõem credenciais, tokens, PII excessiva ou IDs de usuário em labels.
- [ ] Registrar data, operador, versão/tag, revisão Alembic, resultado dos testes e contatos de incidente em local operacional protegido.

## Pendências encontradas na validação local

1. PostgreSQL de teste indisponível: seis testes foram ignorados e os testes PostgreSQL não executaram.
2. Firefox e WebKit não estão instalados: seis projetos Playwright falharam ao iniciar; Chromium passou.
3. Sem SMTP de homologação: não há comprovação de entrega real do link de redefinição.
4. Sem domínio, TLS, hospedagem, monitor e destino de backup provisionados: são configurações da instalação, não defeitos do código.
5. Matriz normativa de transições de status de RF14 não foi definida; decisões de domínio continuam pendentes.
6. Rota visual da agenda diária de RF13 precisa de E2E dedicado.

# Reutilização e atualização por instalação

## Modelo operacional

Cada barbearia recebe uma instalação própria: repositório/checkout, domínio e DNS, variáveis de ambiente, banco, usuários, serviços, armazenamento de branding e agendamento de backup. Cada domínio da API atende uma única instalação e aponta para um banco exclusivo. Não compartilhe `DATABASE_URL`, diretório de backup, credenciais nem tabela de usuários entre instalações. Este modelo não usa `tenant_id` nem multi-tenancy.

Crie uma árvore limpa a partir do núcleo com `tools/new-installation/new-installation.ps1` ou `bash tools/new-installation/new-installation.sh`. O destino deve ser novo e ficar fora da árvore do núcleo. O gerador ignora `.git`, `.env`/`.env.*`, arquivos SQLite/PostgreSQL, WAL, dados, exports, backups, logs e conteúdo de `frontend/assets/branding`; também não segue symlinks. Ele cria um `.env` novo com valores de exemplo, configuração frontend, diretório vazio de marca e `INSTALLATION_CHECKLIST.md`. O destino não herda banco, contas, logo ou conteúdo privado da barbearia de origem.

## Inventário de identidade e configuração

| Item | Fonte por instalação | Nota |
|---|---|---|
| Nome, símbolo, slogan, logo e cor da barra do navegador | `frontend/assets/js/installation-config.mjs`; `INSTALLATION_NAME` em `backend/.env` | O nome aparece também no título OpenAPI da API. Mantenha os dois valores sincronizados. A aplicação de marca escreve texto com `textContent`; logos aceitos seguem a validação de imagem HTTPS/raster existente. Coloque logos próprios em `frontend/assets/branding/`. |
| Paleta, fontes e cores de estados/contraste | `frontend/assets/css/installation.css` | `style.css` e `home.css` consomem tokens CSS. Personalize os tokens, mantendo contraste claro/escuro. |
| Chamadas de campanha da home e texto do consentimento | `installation-config.mjs` em `content` | São copy pública configurável. O restante dos rótulos e instruções de fluxo (login, agenda, validação, status) é texto funcional do núcleo, compartilhado entre instalações. |
| Aceite/versionamento LGPD | Texto `content.consentText` no frontend e `TERMS_VERSION` em `backend/.env` | Atualize o texto e a versão em conjunto após aprovação da instalação. A versão/data/IP aceitos ficam no banco dessa instalação. |
| Telefone, e-mail, endereço, site, mapa, horários e dias | Painel e tabela `informacoes_institucionais` | Cada banco começa sem dados copiados; preencha o painel após o bootstrap. URLs institucionais e mapa ficam nos dados da instalação. |
| Origem da API | `apiBaseUrl` em `installation-config.mjs` | Use a origem pública HTTPS da API dessa instalação. Links de páginas e endpoints relativos permanecem parte do núcleo. |
| Domínio do reset de senha, SMTP, banco, `SECRET_KEY`, CORS, proxy confiável e métricas | `backend/.env` ou secret store do host | Nunca versionar `.env`; use segredos e credenciais distintos por barbearia e ambiente. |
| Fuso horário | `SCHEDULING_TIMEZONE` em `backend/.env` | Informe um identificador IANA válido, por exemplo `America/Sao_Paulo`. |
| Estrelinha / Three.js | `features.estrelinhaWidget` em `installation-config.mjs` | Ativo por padrão. Com `false`, o carregador remove o encaixe e não importa Three.js nem sua folha de estilos; home e demais fluxos continuam funcionando. O modelo 3D é um recurso do núcleo, não é uma cópia personalizável da mascote. |
| Serviços e equipe | Painel e tabelas do banco da instalação | Crie dados próprios; não duplique a base de outra barbearia. |

## Núcleo versionado e repositórios por barbearia

Mantenha `main` como núcleo compartilhado, sem credenciais nem dados de clientes, e publique releases com tags versionadas (por exemplo, `v1.4.0`). Para cada barbearia, mantenha repositório privado próprio ou branch estável próprio criado de uma tag do núcleo. Personalizações devem ficar nos arquivos de instalação acima e no banco; evite editar routers, schemas e componentes funcionais para mudar logo, paleta, contatos ou copy.

No repositório da instalação, configure o núcleo como `upstream` e a instalação como `origin`:

```bash
git remote add upstream <URL_DO_REPOSITORIO_DO_NUCLEO>
git remote -v
git fetch upstream --tags
git switch main
git merge --ff-only <TAG_DA_INSTALACAO_ATUAL>
```

Se a política da equipe mantiver commits próprios na branch de instalação, crie uma branch de atualização a partir da release e integre-a antes de promover:

```bash
git fetch upstream --tags
git switch -c atualizacao/v1.5.0 <TAG_DA_RELEASE>
git merge <BRANCH_ESTAVEL_DA_INSTALACAO>
```

Resolva conflitos apenas na branch da instalação, preservando configuração própria e mudanças do núcleo. Revise o diff para garantir que `.env`, bancos, exports, backups e arquivos de clientes não entraram no Git. Execute testes e smoke checks em staging antes de promover a versão no domínio da barbearia.

## Atualização de schema em cada banco

Uma migration é aplicada separadamente em cada instalação; não existe atualização central de bancos. Para cada barbearia:

1. Agende janela e comunique a equipe; confirme versão/tag, notas da migration e compatibilidade de downgrade/upgrade.
2. Confirme que o backup diário terminou, confira checksum e cópia fora do host. Faça também um backup imediatamente antes da migration e verifique que é restaurável em banco descartável.
3. Pare gravações de API/job conforme a janela e confirme que `backend/.env`/secret store aponta somente ao banco daquela barbearia.
4. Atualize o checkout para a release aprovada e instale as versões fixadas de `backend/requirements.txt`.
5. No diretório `backend`, execute `python -m alembic current`, depois `python -m alembic upgrade head`. Nunca use `stamp` como atalho nem edite revisões já publicadas.
6. Execute testes relevantes em banco temporário, depois `python -m alembic current`, `/health`, `/ready`, smoke de catálogo/login/agendamento e confira painel/dados institucionais.
7. Reabra tráfego e acompanhe logs/métricas. Registre tag, revisão antes/depois, backup, horário, operador e resultado sem incluir PII ou segredos.
8. Repita individualmente para o próximo banco. Se a migration falhar, mantenha a instalação em manutenção e siga rollback/recuperação aprovada; não restaure backup sobre banco ativo sem plano e cópia preservada.

## Rotação periódica de segredos (RNF-13)

Cada instalação mantém seus próprios segredos. Use o cofre do operador e faça revisão/rotação pelo menos a cada 90 dias e imediatamente após suspeita de exposição, troca de responsável ou acesso indevido. A credencial PostgreSQL, SMTP, `METRICS_TOKEN`, chaves de cópia externa/SSH e `SECRET_KEY` são valores independentes; não reutilize entre barbearias.

1. Nomeie um operador e registre a janela. Gere o valor novo no secret manager, não em comando versionado, ticket ou log.
2. Para banco/SMTP/armazenamento, crie ou altere credencial sem removê-la antes; atualize o secret store e a instalação, faça reload/restart controlado e verifique `/health`, `/ready`, SMTP e cópia externa.
3. Para `SECRET_KEY`, planeje que access JWTs assinados com a chave anterior deixam de valer após restart. A sessão pode renová-los pelo refresh token; em incidente, revogue também refresh/reset tokens ativos e exija novo login conforme o procedimento de incidente.
4. Confirme que a chave/credencial antiga deixou de funcionar e remova-a do cofre/serviços após validar todos os processos da instalação.
5. Atualize o registro da instalação com responsável, data de rotação e próxima data (90 dias); nunca registre o conteúdo do segredo.

## Verificação depois de criar a instalação

Preencha `API_URL` e `FRONTEND_URL` com origens HTTPS públicas e rode `tools/new-installation/smoke.ps1` no Windows ou `bash tools/new-installation/smoke.sh` em Linux/macOS. O smoke verifica `/health`, `/ready`, `/services/` e a página pública da home; não cria usuário nem altera dados. Depois, faça em staging um fluxo fictício de cadastro, login, disponibilidade, agendamento e cancelamento antes de abrir para clientes.

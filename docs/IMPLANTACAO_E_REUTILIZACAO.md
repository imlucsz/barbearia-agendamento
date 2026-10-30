# Implantação e reutilização por barbearia

## Estado e limite de publicação

O modelo recomendado é uma instalação independente por barbearia: frontend, domínio, configuração e banco de dados próprios, usando a mesma base de código. Não há `tenant_id` nem administração SaaS multi-tenant.

**O projeto ainda não está pronto para uma publicação de produção sem ressalvas.** A cadeia Alembic cria o schema completo, o startup não executa DDL, e migrações PostgreSQL e um ciclo local de backup/restauração foram ensaiados com bancos descartáveis e dados artificiais. Ainda é necessário escolher e validar a infraestrutura externa de deploy e HTTPS.

Há agora um Blueprint Render de preparação (`render.yaml`) com o processo web, static site, PostgreSQL, headers estáticos e etapa de migrations; nenhum recurso externo foi criado. O operador ainda precisa provisionar e validar o ambiente, fornecer os valores por instalação e verificar TLS, headers, logs, disponibilidade e restauração.

## Pré-requisitos

- Python 3.10 ou superior para a base atual; Render usa a versão 3.14.8 fixada em `backend/.python-version`, alinhada à versão 3.14 do CI.
- PostgreSQL para produção. A dependência `psycopg[binary]` já está em `backend/requirements.txt`.
- Um host para servir os arquivos estáticos de `frontend/` e um processo para executar FastAPI. Podem ser infraestrutura já disponível ou serviços escolhidos pelo operador; este projeto não exige um fornecedor pago específico.
- Um domínio com HTTPS para o site e um endpoint HTTPS para a API. Podem usar o mesmo domínio com proxy ou subdomínios distintos sob o mesmo domínio registrável (por exemplo, `app.dominio.com` e `api.dominio.com`), exigência para envio do cookie de refresh `SameSite=Lax`.
- Um provedor SMTP configurado para produção, pois recuperação de senha é parte dos fluxos publicados; em desenvolvimento local, SMTP pode ficar desativado.
- Armazenamento de backup com acesso restrito e protegido, separado do banco em execução.

## Configuração por instalação

Copie `backend/.env.example` para `backend/.env` apenas no servidor protegido, ou injete as mesmas variáveis por um gerenciador de segredos do ambiente. Nunca versione o arquivo preenchido.

| Variável | Necessidade e uso |
| --- | --- |
| `APP_ENV` | Obrigatória em todos os ambientes: `development`, `test` ou `production`. Use exatamente `production` na publicação; `/seed` só é registrado em `development`. |
| `DATABASE_URL` | Obrigatória fora do desenvolvimento local. Produção exige PostgreSQL, banco, host e usuário; `postgresql://` é normalizada para `postgresql+psycopg://`. Para host remoto, `sslmode=require` é aplicado quando ausente e modos inseguros explícitos são rejeitados. SQLite é rejeitado em produção. Proteja a URL como segredo. |
| `SECRET_KEY` | Obrigatória em todos os ambientes, privada e persistente. Gere uma chave aleatória de pelo menos 32 bytes; valores de exemplo, baixa diversidade ou marcados como teste/desenvolvimento são recusados em produção. |
| `CORS_ALLOWED_ORIGINS` | Origens exatas do frontend, separadas por vírgula, obrigatórias e HTTPS em produção; não inclua caminhos nem `*`. A origem pública do site é definida aqui. |
| `SCHEDULING_TIMEZONE` | Obrigatória em produção e validada como fuso IANA, por exemplo `America/Sao_Paulo`. Não altere depois de gravar reservas sem um plano de conversão dos horários existentes. |
| `ALGORITHM` | Algoritmo JWT; o padrão do projeto é `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiração do access token JWT em minutos; padrão `15`, faixa `5` a `60`. |
| `TERMS_VERSION` | Versão dos termos de consentimento LGPD gravada no cadastro; padrão `1.0`. |
| `CLIENT_IP_SOURCE` | Fonte do IP de cliente para rate limit e auditoria: `direct` (padrão, usa o socket e ignora headers) ou `cf-connecting-ip` (valida um único endereço IP no header do edge explicitamente confiável). |
| `RATE_LIMIT_MAX_ATTEMPTS` | Falhas consecutivas por IP/rota antes de bloquear; padrão `5`, faixa `1` a `100`. |
| `RATE_LIMIT_BLOCK_MINUTES` | Duração do bloqueio; padrão `15`, faixa `1` a `1440` minutos. |
| `FORCE_HTTPS` | Redireciona HTTP para HTTPS; padrão ligado em `production`, desligado nos demais ambientes. Se TLS termina em proxy, configure o redirect no proxy/edge; a aplicação não confia em `X-Forwarded-Proto`. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | Host e remetente são obrigatórios em produção; usuário e senha devem ser fornecidos juntos quando usados. SMTP usa STARTTLS; a senha é segredo. |
| `SMTP_TIMEOUT_SECONDS` | Timeout de envio SMTP, entre 1 e 120 segundos; padrão 10. |
| `PASSWORD_RESET_URL` | Obrigatória em produção: URL HTTPS sem query/fragment, terminando em `reset.html` e na mesma origem autorizada por CORS. |

Gere a chave JWT localmente e transfira-a para o mecanismo de segredo sem incluí-la em comandos versionados ou logs:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Em hospedagem Render, configure `PUBLIC_API_URL`; o build gera a configuração pública no artefato estático e preserva o fallback local dos fontes. `window.BARBEARIA_API_URL`, definido antes dos módulos da página, continua sendo um override suportado. Configure `CORS_ALLOWED_ORIGINS` com a origem HTTPS exata do site, incluindo porta não padrão quando houver.

O cookie de refresh usa `SameSite=Lax`; por isso, site e API precisam estar sob o mesmo domínio registrável (por exemplo, `app.dominio.com` e `api.dominio.com`). Não use domínios registráveis diferentes para a página e a API.

## Homologação Render

O `render.yaml` na raiz descreve PostgreSQL 16, um Web Service para `backend/` e um Static Site para `frontend/`. O backend instala `backend/requirements.txt`, executa `python -m alembic upgrade head` no `preDeployCommand`, inicia `uvicorn app.main:app --host 0.0.0.0 --port $PORT` e usa `/ready` como health check. A aplicação não executa migrations no lifespan. O serviço de banco deve estar na mesma região do backend; a URL Render `postgresql://` é normalizada para `postgresql+psycopg://`, e `sslmode=require` é aplicado à conexão remota quando não houver modo TLS explícito.

O comando `preDeployCommand` do Render está disponível somente para Web Services pagos. O Blueprint não escolhe um plano; antes do provisionamento, selecione um plano que suporte essa etapa. Não mova migrations para o startup de cada worker. `/ready` verifica a revisão Alembic esperada após a etapa de release.

O Static Site executa `node scripts/build-static.mjs` apenas durante o build e publica `dist/`; o Node não é runtime do site. O build exige `PUBLIC_API_URL`, valida uma origem HTTPS sem credenciais/caminho/query e grava apenas a origem pública em `assets/js/render-api-config.js` no artefato. Os arquivos fonte continuam com fallback local `http://127.0.0.1:8000`. O domínio padrão do frontend redireciona `/` para `/pages/index.html`.

### Valores de ambiente a fornecer no Render

Públicos: `PUBLIC_API_URL` no Static Site; `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `PASSWORD_RESET_URL`, `SCHEDULING_TIMEZONE` e `APP_ENV` no backend. `ALLOWED_HOSTS` contém hostname(s) da API sem esquema ou porta; `CORS_ALLOWED_ORIGINS` contém a origem HTTPS exata do frontend. Os domínios Render ou custom domains ainda precisam ser copiados para as respectivas listas.

Segredos: `SECRET_KEY` é gerada pelo Blueprint no provisionamento; `DATABASE_URL` é referenciada do PostgreSQL do mesmo Blueprint; `SMTP_USERNAME`/`SMTP_PASSWORD` são valores manuais protegidos quando o relay exigir autenticação. `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM` e `PASSWORD_RESET_URL` são configuração não secreta, mas obrigatória para que o backend production aceite iniciar. Nenhuma credencial SMTP é criada nesta preparação. O Blueprint usa `sync: false` para valores que o operador preencherá; isso não disponibiliza seus valores a ambientes preview.

O primeiro administrador permanece uma operação manual depois das migrations: a partir de `backend/`, executar `python -m app.initial_admin` com `APP_ENV=production` e o `DATABASE_URL` do próprio serviço. O comando exige interação para solicitar senha sem eco. O provisionamento não deve ser considerado concluído até confirmar um terminal interativo seguro no serviço escolhido e criar essa conta; não há credencial administrativa automática.

No Render, HTTPS termina na borda e o Blueprint define `FORCE_HTTPS=false`; o edge é responsável pelo redirect HTTP→HTTPS. O comando Uvicorn usa `--no-proxy-headers`, pois o runtime Render pode definir `FORWARDED_ALLOW_IPS=*` e a aplicação não deve confiar implicitamente em `X-Forwarded-For` ou `X-Forwarded-Proto`. `CLIENT_IP_SOURCE=cf-connecting-ip` habilita somente o header `CF-Connecting-IP`, validado como exatamente um IPv4 ou IPv6. A documentação do Render informa que sua integração Cloudflare sobrescreve esse header na borda com o IP conectado ao edge ([referência](https://render.com/articles/host-pocketbase-on-render)); isso é apropriado para o Web Service público do Render, não para serviços privados nem para qualquer proxy genérico. O modo `direct` permanece como padrão local e ignora todos os headers encaminhados. Para outro provedor, mantenha `direct` até haver uma garantia documentada de que um header específico é removido/sobrescrito pelo proxy; então implemente uma fonte enumerada equivalente. `ALLOWED_HOSTS` restringe o Host, mas não autentica headers de IP.

O Blueprint aplica HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy` e `Content-Security-Policy: frame-ancestors 'none'` ao Static Site. A CSP completa continua pendente: a home usa import map inline para Three.js em `cdn.jsdelivr.net`, permite logo HTTPS configurável e pode criar iframe do Google Maps. Uma política mais estrita depende de hash do import map e validação real dos hosts; CSP restritiva arbitrária poderia quebrar esses recursos.

`/docs`, `/redoc` e `/openapi.json` ficam desativados em `APP_ENV=production`; permanecem habilitados em desenvolvimento/teste. O root Python fixa `3.14.8` por `backend/.python-version`, alinhado à linha 3.14 do CI. O build estático fixa Node 22 em `frontend/.node-version` e não instala dependências.

## CSP e cabeçalhos para arquivos estáticos

Inventário do frontend atual: a página inicial carrega Three.js `0.186.0` de `cdn.jsdelivr.net` por um import map inline; o mapa institucional pode criar iframe em host `google.com` ou `google.com.br`; não foram encontrados fontes remotas. CSS, módulos e imagens ficam em `frontend/`. O import map inline exige hash CSP atualizado quando seu conteúdo mudar. Este exemplo é orientação para o host estático/proxy, não uma configuração de deploy aplicada:

```text
Content-Security-Policy: default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self' https://cdn.jsdelivr.net 'sha256-<hash-SHA256-do-conteudo-inline-do-importmap>'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' https://api.dominio.com; frame-src https://www.google.com https://www.google.com.br https://maps.google.com; upgrade-insecure-requests
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
X-Frame-Options: DENY
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

Calcule o hash do texto exato dentro da tag `script type="importmap"` em cada release, ou mova o mapa para arquivo externo e ajuste a CSP. O CSP da API é deliberadamente mais restritivo (`default-src 'none'`); o exemplo acima é somente para o host das páginas. Configure HSTS no host estático apenas depois de confirmar HTTPS para todos os subdomínios abrangidos.

### Dados personalizáveis

Cada instalação mantém seus dados no próprio banco:

- Nome institucional, endereço, telefone, e-mail, site, dias/horários de atendimento e link de mapa: painel administrativo, tabela `informacoes_institucionais`.
- Serviços, preços e durações: painel administrativo, tabela `services`.
- Contas de barbeiros, serviços associados, jornadas e bloqueios: painel administrativo e tabelas próprias.
- Fuso horário, chaves, banco, SMTP, CORS e endpoint frontend: configuração isolada da instalação.

A paleta visual fica em `frontend/assets/css/installation.css`, nos tokens CSS `--color-*`, `--font-*` e tokens do hero. Uma instalação pode personalizar esse arquivo sem alterar a lógica de agendamento. O nome comercial, o logo e a cor da barra do navegador ficam em `frontend/assets/js/installation-config.mjs` e são aplicados por `installation-brand.mjs` nas páginas funcionais que carregam `api.js`. A configuração é pública e não deve conter segredos.

Para personalizar sem editar HTML, ajuste `brand.name`, `brand.logoUrl` e `brand.themeColor` em `installation-config.mjs`. Sem `logoUrl`, a marca atual `B.` continua visível. Para usar um arquivo da própria instalação, coloque uma imagem raster real em `frontend/assets/branding/` com nome seguro e configure, por exemplo, `../assets/branding/logo.webp`. São aceitos PNG, JPEG, WebP e AVIF; SVG, data URL, `javascript:`, caminho fora da pasta de marca, traversal, HTTP externo, URL com credenciais, query ou fragmento são rejeitados. URL externa só pode usar HTTPS; configure a CSP do host para permitir explicitamente esse domínio. Não há endpoint de upload. Não publique SVG arbitrário: o operador deve verificar que a extensão e o conteúdo do arquivo correspondem ao formato raster informado e que o servidor envia o MIME type correto.

O nome é exibido usando `textContent`, e nunca interpretado como HTML. Logo inválido ou ausente mantém o símbolo padrão; erro ao carregar o arquivo também retorna ao símbolo `B.`. As dimensões são contidas no símbolo com `object-fit: contain`. Continue personalizando as cores completas em `installation.css`; mantenha `brand.themeColor` sincronizada com a cor de fundo escolhida.

## Preparar uma instalação nova

Crie um banco PostgreSQL vazio, um usuário restrito àquele banco e a configuração própria da barbearia. Não restaure o banco, SQLite, exportações ou dados de clientes de outra instalação para criar uma nova barbearia.

Exemplo de preparação no host Linux/macOS, com os valores reais fornecidos pelo ambiente de implantação e não pelo repositório:

```bash
git clone <repositorio> barbearia-agendamento
cd barbearia-agendamento/backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Preencha as variáveis da instalação no `.env` protegido ou no gerenciador de segredos. A URL deve apontar exclusivamente ao banco novo desta barbearia. Depois:

```bash
python -m alembic upgrade head
```

`alembic upgrade head` cria onze tabelas, índices, chaves estrangeiras e restrições. Faça isso antes do startup da API:

```bash
python -m alembic current
python -m alembic upgrade head
python -m alembic current
```

Depois de aplicar as migracoes, crie o administrador pelo comando interativo. Em producao exige `APP_ENV=production`, PostgreSQL e revisao Alembic atual; no desenvolvimento local aceita `APP_ENV=development` e SQLite ou PostgreSQL. Recusa bancos sem todas as tabelas, segundo administrador e senhas com menos de 12 caracteres. A senha e solicitada sem eco. O bloqueio transacional serializa tentativas simultaneas.

```bash
python -m app.initial_admin
```

O comando nao imprime credenciais. A rota `/seed` existe somente em desenvolvimento e cria apenas contas demo sem privilegios administrativos; nunca use essas contas em producao.

Reinicie o backend atrás do proxy HTTPS e só então publique/aponte o domínio para a instalação. Não use `/seed` em produção e não crie a conta de produção com as credenciais de demonstração. Cadastre os dados institucionais, serviços, barbeiros, associações, jornadas e bloqueios pelo painel administrativo.

O startup verifica a revisão Alembic e registra um aviso claro se ela não estiver atualizada; ele não cria nem altera tabelas. Se um schema preexistente não for reconhecido, preserve-o e faça a investigação em um banco temporário antes de planejar qualquer transição.

## HTTPS, CORS e processo da aplicação

- Termine TLS em um proxy reverso ou serviço equivalente e force HTTPS para site e API. Configure HSTS e cabeçalhos apropriados no host/proxy; não há configuração de proxy no repositório.
- Faça o proxy encaminhar tráfego da API para Uvicorn em `127.0.0.1:8000`; não exponha o servidor de desenvolvimento nem use `--reload`.
- Sirva `frontend/` como conteúdo estático. Defina a URL da API em `installation-config.mjs` como HTTPS antes de publicar os módulos JS.
- Use `CORS_ALLOWED_ORIGINS` com a origem do frontend, não a URL da API. CORS não substitui autenticação, TLS ou controle de acesso. Refresh e logout exigem `Origin` presente e listado nessa configuração.
- Em produção, site e API precisam compartilhar o mesmo domínio registrável (por exemplo, `app.dominio.com` e `api.dominio.com`). O frontend envia cookies com `credentials: include`; refresh e logout exigem `Origin` listado em `CORS_ALLOWED_ORIGINS`. O cookie de refresh é HttpOnly, `SameSite=Lax` e `Secure` em produção.
- Configure `PASSWORD_RESET_URL` para a URL final HTTPS do formulário de redefinição.
- Use um supervisor/container do ambiente escolhido para reiniciar e observar o processo. A aplicação não inclui um unit file, container de produção nem sistema de logs/monitoramento.
- O access token bearer permanece em `localStorage` para sobreviver à navegação entre páginas; JavaScript executado na origem (por exemplo, por XSS) pode lê-lo e exfiltrá-lo. Sua validade padrão é 15 minutos. O refresh token fica somente em cookie `HttpOnly`, `SameSite=Lax` (e `Secure` em produção), com `credentials: include` nas chamadas.

## Health checks e verificações pós-deploy

- `GET /health` confirms database connectivity with `SELECT 1`, with a 1 second timeout; it returns a generic `503` when the database does not respond.
- `GET /ready` checks connectivity and the current Alembic revision without running migrations. It also returns 503 when the schema is outdated.
- `GET /metrics` exposes Prometheus request counts by route/method/status, the 5xx ratio, and approximate latency. Set `METRICS_TOKEN` (at least 32 random characters) to enable it; otherwise it returns `404`.

Após publicar em staging, confirme:

1. O processo inicia com `APP_ENV=production`, PostgreSQL, `SECRET_KEY` forte e CORS HTTPS explícito.
2. `/health` and `/ready` return 200 when the database and schema are ready; database outage makes both return 503, while an outdated schema keeps `/health` at 200 and `/ready` at 503.
3. O domínio frontend chama a origem configurada da API e uma origem fora da lista CORS é rejeitada pelo navegador. Site e API devem compartilhar o mesmo domínio registrável (por exemplo, `app.dominio.com` e `api.dominio.com`) para que o cookie SameSite=Lax seja enviado.
4. HTTPS é válido para site, API e recuperação de senha; login, cadastro, recuperação e fluxos essenciais de agendamento funcionam.
5. O bootstrap criou apenas o administrador desta instalação; não há contas demo nem dados de outra barbearia.
6. Backup é produzido, protegido e restaurado com sucesso em um banco temporário isolado.

## Backup e restauração PostgreSQL

Faça backups regulares, criptografe-os em repouso e restrinja quem pode ler/restaurar. Use autenticação interativa ou arquivo de credenciais protegido pelo sistema; não passe senha como argumento nem grave a URL em histórico de shell.

Backup custom-format:

```bash
pg_dump --format=custom --host <host> --username <usuario> --dbname <banco_da_instalacao> --file <backup.dump>
```

Restaure em um banco vazio e isolado, nunca por cima de outro cliente:

```bash
createdb --host <host> --username <usuario> <banco_temporario>
pg_restore --no-owner --host <host> --username <usuario> --dbname <banco_temporario> <backup.dump>
```

### Ensaio reproduzível de backup/restauração

O provedor/plataforma de hospedagem ainda não foi escolhido. Este procedimento valida PostgreSQL local e não representa deploy público nem validação de HTTPS externo. Para ensaiar o backup e o restore sem acessar o banco de desenvolvimento ou o container `postgres-test` existente, use o script `tools/test-postgres-backup-restore.ps1`. Requer Docker, imagem `postgres:16-alpine` já presente (o script não baixa imagens) e dependências em `backend/.venv`:

```powershell
.\tools\test-postgres-backup-restore.ps1
```

O script cria um container PostgreSQL novo, com nome aleatório, sem volume persistente e porta aleatória vinculada somente a `127.0.0.1`. Cria dois bancos fictícios terminados em `_test`, aplica as migrações Alembic na origem, grava dados artificiais, gera um dump custom-format e restaura no segundo banco. Compara contagens, registros de referência, revisão Alembic, índices, PKs, FKs, unicidades e checks, faz uma consulta de integridade relacional e executa `test_schema_migrations.py`, `test_postgres_booking_migration.py`, `test_booking_integrity.py` e `test_booking_temporal.py` em schemas isolados. Ao terminar, encerra somente o container criado pelo próprio script e remove o dump e os helpers temporários. Não executa `docker compose down`, não remove volumes e não altera o serviço PostgreSQL de teste já ativo.

O ensaio local com dados fictícios foi executado com sucesso nesta revisão do documento. Ele não valida criptografia/retention em storage externo, backup de dados reais, permissões do provedor, RPO/RTO nem plano de recuperação de desastre. O operador deve definir esses controles na plataforma escolhida e repetir testes de restauração periodicamente.

### Contrato mínimo de deploy

Até a escolha do provedor, use estas regras como requisitos de implantação, não como configuração já aplicada: TLS deve terminar no proxy/serviço público para frontend e API; o proxy encaminha somente à API privada; o PostgreSQL não recebe tráfego público e aceita conexões apenas da aplicação e dos operadores autorizados. Em um host com proxy local, Uvicorn pode ouvir em `127.0.0.1:8000`; em container, use uma rede interna e publique somente o proxy. Encaminhe `Host` e `X-Forwarded-Proto` e configure Uvicorn para confiar exclusivamente nos IPs do proxy real (`--forwarded-allow-ips`), nunca em `*` sem isolamento equivalente.

Antes de expor tráfego, provisionar os segredos fora do Git, aplicar `python -m alembic upgrade head` com a URL do banco daquela instalação, executar Uvicorn sem `--reload`, servir `frontend/` por HTTPS, configurar CORS com a origem exata do site e validar `/health` e `/ready`. Configure HSTS, CSP, limites de requisição, logs sem tokens/credenciais, firewall e alertas na plataforma escolhida. Nenhum domínio, certificado, proxy, firewall ou cabeçalho foi ativado ou validado externamente nesta etapa.

Valide as tabelas, contagens e relações no banco temporário e execute `python -m alembic upgrade head` com `DATABASE_URL` apontando para ele quando a restauração precisar das revisões mais recentes. Teste restauração periodicamente; um arquivo de backup não verificado não prova recuperabilidade. Preserve a instalação original durante o teste.

## Atualizar o código sem perder dados

1. Faça deploy da versão nova primeiro em staging com uma cópia protegida/anonimizada ou um banco de teste; nunca teste migrações no banco de produção.
2. Faça backup PostgreSQL e confirme que a restauração foi verificada recentemente.
3. Leia o histórico e as notas das revisões novas. Pare a aplicação ou coloque-a em manutenção.
4. Instale as dependências da release e execute, a partir de `backend`, `python -m alembic upgrade head` apontando somente para o banco desta instalação.
5. Inicie a versão nova, verifique `/ready` e execute smoke tests antes de reabrir o tráfego.
6. Em falha, preserve logs sem segredos e dados atuais; restaure backup em ambiente separado e prepare correção/rollback explícito. Não use `stamp`, `downgrade` ou exclusão de dados para contornar divergência.

O `requirements.txt` contém dependências sem versões fixas para a maioria dos pacotes, e não existe lockfile. Isso torna builds futuros menos reproduzíveis; fixe/valide versões em uma etapa própria antes de definir uma política de releases estável. Novas alterações de schema precisam de migrações versionadas testadas em SQLite e PostgreSQL.

## Testes reproduzíveis

No backend, os testes normais usam SQLite temporário e não o banco local:

```bash
cd backend
python -m unittest discover -s tests -v
```

Os testes PostgreSQL usam `BOOKING_TEST_BACKEND=postgresql` e `BOOKING_TEST_POSTGRES_URL` apontando para um banco exclusivo terminado em `_test`; o harness valida o banco e cria schemas temporários isolados. Siga o procedimento e os comandos PostgreSQL da seção “Testes de integração PostgreSQL” do `README.md`.

Os testes do frontend podem ser executados com Node.js:

```bash
node --test frontend/tests/api-errors.test.mjs frontend/tests/reset-token.test.mjs frontend/tests/session.test.mjs frontend/tests/installation-brand.test.mjs
```

## Auditoria e retenção

Eventos de autenticação e operações administrativas ficam em `audit_logs` e são consultáveis por administradores em `/admin/auditoria`. Configure `RETENTION_DAYS` (padrão 365). Para conferir a quantidade vencida sem excluir dados, execute no diretório `backend`:

```bash
python -m app.maintenance purge-audit --dry-run
```

Para executar o expurgo dos registros anteriores ao prazo configurado, remova `--dry-run`. O endpoint administrativo de consulta não altera nem apaga eventos. A tabela armazena metadados permitidos, nunca corpo bruto, senha, token ou hash.

## Limitações ainda existentes

- A migração, os fluxos de agendamento e a restauração PostgreSQL foram exercitados em bancos descartáveis com registros artificiais. Isso não substitui um ensaio de upgrade sobre uma cópia anonimizada do banco da instalação quando ela existir.
- Não há deploy/infra de produção versionados, CSP/HSTS configurados pelo host, backups automáticos ou monitoração operacional no repositório.
- O logo e o nome são configurados no arquivo estático por instalação, não pelo painel. A paleta também é configurada em CSS; não há editor visual no painel.
- A URL de API do frontend precisa ser personalizada por instalação antes de publicar.
- O SMTP depende de um provedor externo e credenciais próprias.
- Dependências não estão totalmente fixadas; a reprodutibilidade de instalação precisa ser melhorada.
- Cada instalação deve provisionar, proteger, manter e restaurar seu próprio banco e configuração. Não há isolamento multi-tenant dentro da aplicação.

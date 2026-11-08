# F1 — frontend e API na mesma origem

## Estado

Implementação e prova local HTTPS concluídas; validação publicada Render ainda pendente. Nenhum deploy, domínio/DNS, segredo real, banco publicado ou recurso externo foi alterado. A configuração versionada identifica API Python e frontend estático separados; o conector Render estava sem workspace confirmado, portanto a configuração atualmente aplicada não foi inspecionada.

## Causa e arquitetura

O frontend separado executava fetch com credentials=include, mas isso não supera SameSite nem a política de cookies de terceiros. `onrender.com` consta na [Public Suffix List](https://publicsuffix.org/list/public_suffix_list.dat): serviços distintos não devem ser tratados como subdomínios de um domínio próprio compartilhado. CORS permite ler respostas; não obriga o navegador a aceitar/enviar cookies.

A solução single-tenant usa o serviço Python existente para servir somente `/pages` e `/assets`, além das rotas API existentes. `SERVE_FRONTEND=true` habilita esse modo e faz `/` redirecionar para a home. API-only continua sendo o padrão: `/` permanece JSON e as páginas não são publicadas.

HTML recebe, antes dos módulos, `/assets/js/same-origin-config.js`, que configura a API como `window.location.origin`. Não deriva autorização de Host ou de X-Forwarded-Host. O backend monta diretórios públicos explícitos com a contenção de StaticFiles; não publica raiz, `.env`, backend, scripts de build ou testes. HTML usa no-store; a CSP de documentos permite o frontend já existente e mantém frame-ancestors none/base-uri self/object-src none. Respostas da API mantêm a CSP restritiva default-src none; respostas `/auth/*` usam no-store. Não se adicionou unsafe-inline à política da API.

O frontend estático antigo é mantido como entrada de redirecionamento: build com `PUBLIC_SAME_ORIGIN_REDIRECT=true` gera páginas sem a aplicação antiga. Script externo direciona ao PUBLIC_API_URL validado (HTTPS/origem sem credenciais), preservando pathname, query e fragmento de recuperação. Não transfere JWT, localStorage ou cookie entre origens. Usuários com sessão no site antigo podem precisar entrar novamente.

## Cookies, CORS e CSRF

- Cookie refresh continua host-only (sem Domain), HttpOnly, Secure em produção, SameSite=Lax, Path=/auth e duração de 30 dias. Logout limpa exatamente esse escopo. Não se adotou SameSite=None, Domain compartilhado ou cookie de terceiros.
- CORS continua com origens explícitas e allow_credentials=true, sem wildcard. No modo publicado, CORS_ALLOWED_ORIGINS é a URL do próprio serviço. Refresh/logout exigem Origin válido e listado; ausente, null e origem estrangeira recebem 403 antes de mutar a família.
- Login agora rejeita Origin estrangeiro quando o header está presente; clientes não browser que omitem Origin conservam o contrato. Login usa JSON; refresh/logout são POST e continuam sem autorização por cookie para os demais endpoints. JWTs continuam por ID, com Bearer e o mesmo tratamento de expiração.
- A prova adversária usa outra porta no mesmo host/site: Lax sozinho não impediria enviar o cookie, mas a verificação exata de Origin bloqueia a operação. Nada é autorizado automaticamente porque aparenta ser same-site.
- CAS, capacidade de hashing, reservas, limites e transação F2 não foram reescritos. O marcador pós-commit de F2 e a finalização idempotente continuam intactos. O frontend conserva refresh single-flight e retry apenas após 401 nos endpoints apropriados.

## Render: preparação versionada e aplicação externa pendente

**Barreira de implantação:** antes de publicar/sincronizar este Blueprint, pausar auto-deploy e auto-sync do frontend legado no painel autorizado. O arquivo único não garante ordem de deploy entre serviços. Não sincronizar ambos de uma vez: aplicar a configuração/API primeiro; somente após validar sua URL canônica habilitar o build/redirect legado. Esta tarefa não altera essas opções remotas. HTML e assets de URLs estáveis usam no-store e ignoram validadores condicionais; abas já abertas ainda devem ser recarregadas na transição, pois cache não torna múltiplas requisições atômicas entre releases.

1. Revisar diff do Blueprint sem aplicar automaticamente. Os nomes e tipos de serviços/banco foram preservados; nenhum recurso foi removido ou recriado.
2. API: `rootDir: .`, build `pip install -r backend/requirements.txt`, start entra em backend antes do render_start existente. A raiz precisa conter frontend e backend: [Render não disponibiliza arquivos fora de rootDir](https://render.com/docs/monorepo-support). PYTHON_VERSION=3.14.8 preserva a versão declarada em backend/.python-version após mudar a raiz.
3. SERVE_FRONTEND=true. FRONTEND_ORIGIN e CORS_ALLOWED_ORIGINS referenciam o RENDER_EXTERNAL_URL da própria API; ALLOWED_HOSTS continua no hostname explícito. PASSWORD_RESET_URL usa a origem canônica. [Self-reference é suportado](https://render.com/docs/blueprint-spec#self-referencing-environment-variables).
4. Aplicar primeiro a API e verificar HTTPS, `/ready`, telas, headers, login/refresh/logout e recuperação com conta descartável autorizada. Não executar a fixture QA em serviço publicado. O render_start mantém a revisão Alembic existente; nenhuma migração nova foi criada nesta tarefa.
5. Depois atualizar o serviço estático para o build de redirecionamento, com PUBLIC_API_URL da mesma API e PUBLIC_SAME_ORIGIN_REDIRECT=true. Validar links antigos, caminhos, query e token no fragmento, sem transferir tokens de sessão.
6. Validar com cookies de terceiros bloqueados, expiração real, operações simultâneas, replay, origens hostis, logout e navegação em telas reais. Só então encerrar F1 no ambiente publicado. Verificar também regras manuais do Dashboard e preview URLs antes de sincronizar.

Não é necessário um novo domínio/DNS ou proxy para a URL onrender.com da API. Domínio próprio é opcional: ao adotá-lo, ajustar conjuntamente FRONTEND_ORIGIN/CORS_ALLOWED_ORIGINS/ALLOWED_HOSTS e reset URL, validar HTTPS e reconfigurar o redirect legado para essa mesma origem. Não adicionar subdomínios arbitrários à allowlist.

O Blueprint foi analisado pela especificação atual e por contratos automatizados de configuração. Não houve sync/plan/apply remoto nem validação autenticada da configuração aplicada. Se disponível no ambiente operacional, executar `render blueprints validate render.yaml` antes da aplicação autorizada.

## Reprodução local e Chromium

Configuração local normal (sem depender de cookies de terceiros): `SERVE_FRONTEND=true`, `APP_ENV=development`, CORS_ALLOWED_ORIGINS exatamente a origem FastAPI local, por exemplo `http://127.0.0.1:8000`. Não deixar o default antigo :5500 ao abrir as telas em :8000. No modo API-only, a instalação separada continua possível sob responsabilidade de configurar uma topologia de cookies compatível.

Regressões persistentes: `backend/tests/test_same_origin_frontend.py`, `test_same_origin_deployment.py`, `frontend/tests/same-origin.test.mjs` e a prova Chromium `frontend/e2e/auth-session.spec.mjs`, cujo fluxo está em `auth-session-browser.mjs`.

Para a prova HTTPS, gerar um certificado local de curta duração para localhost/127.0.0.1, sem instalar CA no sistema. Pode-se usar OpenSSL já instalado (ou ferramenta equivalente) fora dos diretórios versionados. Depois, com o Python do projeto:

Exemplo OpenSSL: `openssl req -x509 -newkey rsa:2048 -nodes -days 1 -keyout CAMINHO_CHAVE_LOCAL -out CAMINHO_CERT_LOCAL -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"`. Guardar os dois arquivos somente em diretório temporário próprio; não versionar chaves.

```powershell
python -B frontend/e2e/auth-session-server.py --certfile CAMINHO_CERT_LOCAL --keyfile CAMINHO_CHAVE_LOCAL
npx --no-install playwright test --config frontend/e2e/auth-session.config.mjs
```

O segundo comando requer Playwright/Chromium já disponíveis; não instala automaticamente. Nesta execução, o mesmo fluxo persistente foi executado pelo conector Chromium existente. ignoreHTTPSErrors é exclusivo do certificado self-signed da fixture, não muda o app nem a validação TLS publicada. A fixture usa conta fictícia e SQLite temporário do harness e simula os atributos de cookie/headers de produção mantendo os settings do banco/HMAC em teste. As rotas `__qa__` só existem no servidor de teste, não no aplicativo implantado. A origem adversária local usa porta 4198. Encerrar o processo e remover somente certificado/chave próprios ao concluir.

## Limites

Não se promete corrigir browsers que bloqueiam todos os cookies first-party, entrega HTTP após commit, XSS integral do frontend, sincronização automática de refresh entre abas ou revogação imediata dos access JWTs. A solução não exige relaxar as proteções de autenticação. F1 pode ser encerrado localmente no código; o encerramento operacional depende da implantação coordenada e da validação HTTPS real, que não foram autorizadas nesta rodada.

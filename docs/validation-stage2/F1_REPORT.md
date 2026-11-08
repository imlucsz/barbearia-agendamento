# F1 — implementação e validação local de origem única

## Revisão final para commit local

O restante deste relatório registra a rodada original, anterior ao commit. Na revisão final autorizada, assets também passaram a usar no-store, validadores condicionais são ignorados para impedir HTML/JS antigos e HEAD preserva Content-Length sem corpo. Acrescentada regressão de métodos/404/precedência e explicitada a barreira externa contra implantação simultânea do redirect legado. Seleção final adicional: nove testes Python F1 e nove Node aprovados. As validações completas anteriores permanecem registradas abaixo, sem repetir a auditoria máxima. Nenhuma migração ou configuração remota alterada.

Base: branch `fix/auth-security-stage2-sessions`, HEAD `3ffc560a803d0c6437af6943f638ded8b31ea6f2`. Sem commit/staging, push, PR, merge ou deploy nesta tarefa. Alterações prontas para revisão; nenhum schema, migração ou requisito de dependência foi modificado.

**Resultado: F1 corrigido no código e comprovado localmente com HTTPS/Chromium real. Encerramento operacional no Render ainda pendente de implantação coordenada e validação publicada.**

## Causa e solução

Frontend e API separados recebiam credenciais por fetch, mas CORS não supera SameSite nem bloqueio de cookies de terceiros. O controle negativo desta rodada confirmou login 200, cookie rejeitado pelo Chromium (`UserPreferences`) e refresh 401, mesmo com a origem explicitamente permitida por CORS.

A solução single-tenant habilita `SERVE_FRONTEND=true` no mesmo serviço Python: monta somente `/pages` e `/assets` públicos e injeta configuração que aponta a API para a própria origem da página. Cookies permanecem host-only, HttpOnly, Secure em produção, SameSite=Lax, Path=/auth e 30 dias. Sem SameSite=None, Domain ampliado, proxy novo ou necessidade de DNS novo para usar a URL existente da API.

O frontend estático anterior permanece definido no Blueprint como entrada de redirecionamento para a origem canônica. O build preserva pathname, query e fragmento (inclusive reset), sem transferir access/refresh/localStorage entre sites. O modo API-only padrão conserva `/` JSON; apenas o modo web explícito redireciona `/` para a home. API/health/ready e demais rotas existentes são preservadas.

Login rejeita Origin estrangeiro presente. Refresh/logout continuam exigindo origem explícita válida; CORS permanece sem wildcard e com credenciais. A origem não é autorizada a partir de Host recebido. HTML recebe política CSP de frontend compatível com a aplicação existente, mantendo bloqueio de framing/base-uri/objetos; respostas API mantêm default-src none. HTML e `/auth/*` usam no-store. Contenção de StaticFiles foi exercitada; backend, env, testes e ferramentas não são publicados.

## Alterações

- `backend/app/frontend.py`: publicação opt-in e injeção de configuração.
- `backend/app/main.py`: instalação do frontend, redirect raiz condicional, CSP por tipo de resposta e no-store de autenticação.
- `backend/app/routers/auth.py`: validação de Origin do login, sem alterar CAS, hashing, reservas, F2 ou emissão/rotação.
- `frontend/assets/js/same-origin-config.js`: API baseada na origem corrente.
- `frontend/scripts/build-static.mjs`: modo de redirecionamento legado, preservando o modo estático anterior.
- `render.yaml`: raiz do repo para API acessar frontend, comandos relativos ajustados, Python 3.14.8 explícito, SERVE_FRONTEND, self-reference de origem/CORS e build legado em redirect. Nomes/tipos de recursos e banco mantidos.
- Novas regressões Python/Node e fixture/suite Chromium em `frontend/e2e/auth-session*` e `build-legacy-fixture.mjs`.
- README, status de requisitos, procedimento da etapa 2, procedimento F1 e plano atualizados.

## Testes reais e resultados

| Verificação final | Aprovados | Falhos | Erros | Ignorados |
|---|---:|---:|---:|---:|
| Python completo rastreado + seis casos novos F1 (378) | 362 | 0 | 0 | 16 |
| Contratos de implantação adicionais | 2 | 0 | 0 | 0 |
| Node completo + novas regressões (53) | 53 | 0 | 0 | 0 |
| PostgreSQL direcionado (41) | 41 | 0 | 0 | 0 |
| Chromium HTTPS, 20 verificações persistentes | 20 | 0 | 0 | 0 |

Python 3.14.7/Windows em venv temporário com os pins exatos do projeto, incluindo Pydantic 2.14.2 e python-multipart 0.0.33. pip check aprovado. Os 16 ignorados da rodada SQLite não são contados como testes PostgreSQL executados. PostgreSQL 16.15 descartável e isolado: zero transações idle/schemas remanescentes; container removido. Os 41 casos mantêm evidência de CAS/reset, reservas/limites entre processos, finalização idempotente, F2 e refresh/logout concorrentes. Nenhuma persistência de produção foi usada.

Regressões novas começaram falhando antes da implementação. Ocorrências de instrumentação corrigidas durante a prova: o cliente ASGI local sinaliza disconnect cedo para FileResponse (o body de arquivo passou a ser conferido no navegador real); o harness HTTPS precisou manter settings de teste para seu banco/HMAC enquanto exercita atributos de produção; a inspeção de cookies precisa usar URL em `/auth`, não `/`; e a resposta bloqueada por CORS foi observada pelo CDP, não por resposta JS da página atacante. Os resultados finais acima não escondem falhas de produto conhecidas.

Ruff nos arquivos novos e git diff --check aprovados. A revisão independente de segurança não encontrou bloqueadores; a configuração explícita de CORS ao desenvolver em :8000 foi documentada.

## Evidência Chromium

Chromium **156.0.8078.48**, HTTPS local restrito a loopback com certificado self-signed de curta duração, sem instalar CA. A execução final confirmou no servidor Pydantic **2.14.2**, python-multipart **0.0.33**, FastAPI **0.162.0**, Python **3.14.7**. CDP `Network.setCookieControls` ativou restrição de cookies de terceiros e desativou exceções/heurísticas para a prova. Nenhum endpoint de autenticação foi interceptado ou substituído por respostas simuladas.

Verificado: tela real de login/dashboard e CSS; cookie Secure/HttpOnly/Lax/host-only; JWT realmente expirado e assinado (401 → refresh 200 → retry 200); cookie rotacionado; três requisições simultâneas com um refresh; origem adversária no mesmo site mas outra porta com HTTP 403 real e falha CORS na página; estado persistido sem alteração após CSRF; Origin ausente 403; replay 401 revogando família; nova sessão; clique Sair com cookie removido e família revogada; cookie ausente com limpeza de sessão/retorno ao login; redirect legado gerado pelo build real chegando à tela de reset e preservando query/fragmento; controle cross-site com cookie rejeitado e refresh 401. Estado final da fixture: **5 refresh, 3 famílias, todos revogados, zero ativos**.

Artefatos locais, não versionados, em `docs/validation-stage2/postgresql/runs/f1-real-20261107/`:

- `chromium-exact-final.json`: 20 asserções finais em loopback com pins exatos, status HTTP e motivos de rejeição, sem tokens/cookies brutos.
- `dashboard.png`: tela real renderizada após login.
- `python.json`, `runtime-during-tests.json`, `node.json`, `pip-check.json`: suíte e versões.
- `postgresql/f2.json`, `postgresql/runtime-during-tests.json`, `postgresql/environment.json`: PostgreSQL e versões.

A fixture mantém o banco/settings isolados do harness; somente os atributos de produção de cookie/headers são exercitados. As rotas `__qa__` não integram a aplicação de produção. ignoreHTTPSErrors fica restrito à automação com o certificado local; não é mudança de TLS do produto.

## Render, passos externos e limites

O conector estava sem workspace confirmado; só a topologia versionada e a especificação oficial foram analisadas, sem consulta a secrets ou banco publicado. Não houve plan/apply/sync remoto. A raiz do serviço precisa disponibilizar ambos os diretórios, e o Render suporta self-reference de variáveis padrão. Os contratos YAML passaram; validação autenticada da configuração aplicada e do deploy permanecem externas.

Aplicar a transição em duas fases autorizadas: primeiro API com telas/origem canônica e verificar HTTPS/ready/sessão/reset; depois frontend legado em redirect. Confirmar regras existentes de Dashboard/preview, URLs, CORS/ALLOWED_HOSTS e e-mail. Domínio próprio é opcional e requer ajustar todos esses valores juntos; não adicionar origens arbitrárias ou Domain compartilhado. Procedimento e comandos reproduzíveis em [AUTH_F1_SAME_ORIGIN.md](../security/AUTH_F1_SAME_ORIGIN.md).

Permanecem fora da prova: ambiente publicado, Python patch 3.14.8/Linux de destino, navegadores que bloqueiam todos os cookies first-party, coordenação de refresh entre abas, CSP/XSS integral e entrega HTTP após commit. Access JWT continua válido até expirar após logout/reset, conforme desenho anterior. Nenhuma dessas garantias foi enfraquecida para passar testes.

Artefatos locais anteriores foram preservados. Graphify não foi reconstruído: a única diferença na comparação do manifesto anterior foi `graphify-out/cache/last_query_stamp`, atualizado pelas consultas obrigatórias de navegação/revisão; graph.json e demais evidências permaneceram idênticos. Servidores HTTPS foram encerrados; container PostgreSQL removido. O venv e a chave TLS próprios são descartados após salvar a evidência, fora do staging. Encerramento detalhado em `runs/f1-real-20261107/summary.json`; sem criar commit.

Fontes primárias: [cookies e atributos](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie), [Public Suffix List](https://publicsuffix.org/list/public_suffix_list.dat), [Render rootDir](https://render.com/docs/monorepo-support), [Blueprint self-reference](https://render.com/docs/blueprint-spec#self-referencing-environment-variables), [Python Render](https://render.com/docs/python-version).

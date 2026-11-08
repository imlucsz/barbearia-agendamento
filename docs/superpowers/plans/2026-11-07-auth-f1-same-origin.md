# F1 — origem única: plano de implementação

**Objetivo:** disponibilizar telas e API no mesmo serviço/origem HTTPS, sem cookies de terceiros.
**Autorização:** implementação e testes locais autônomos; sem commit/deploy/DNS ou dados publicados.
**Arquitetura:** FastAPI monta apenas assets/pages públicos quando SERVE_FRONTEND=true; HTML recebe configuração da API baseada na própria origem. API mantém rotas, cookies e Origin allowlist. Serviço estático antigo torna-se entrada de redirecionamento. Nenhum schema muda.

Alternativas avaliadas: SameSite=None depende de cookies de terceiros; domínio próprio compartilhado requer DNS; proxy separado adiciona serviço. Origem única no serviço Python existente evita essas dependências. O contrato JSON de / permanece no modo API-only (padrão); no modo web / redireciona para a home.

- [x] Criar regressões de publicação segura, headers, Origin e configuração de origem; observar falhas antes da implementação.
- [x] Implementar publicação opt-in, configuração frontend e redirecionamento legado; preservar cookies, CAS, F2 e rotas.
- [x] Preparar Render com raiz do repositório e origem canônica; não remover recursos ou aplicar Blueprint.
- [x] Exercitar Chromium real com HTTPS, expiração, simultaneidade, cookies bloqueados/ausentes, CORS e CSRF.
- [x] Executar Python/Node pertinentes e regressões de sessão; documentar resultados e pendências externas.
- [x] Revisão independente final e git diff --check; preservar artefatos locais; sem commit.

Evidência final: Python completo + seis regressões F1: 378 casos, 362 aprovados/16 ignorados; dois contratos de implantação adicionais aprovados. Node 53; PostgreSQL 41; Chromium HTTPS 20 verificações aprovadas. Pins exatos em venv descartável. Revisão independente sem bloqueadores; configuração CORS local explicitada. Sem alteração de schema, commit, deploy ou operação publicada. Graphify não foi reconstruído; consultas atualizaram apenas cache/last_query_stamp. Relatório detalhado: docs/validation-stage2/F1_REPORT.md.

Riscos a verificar: CSP de HTML versus API; traversal/exposição de arquivos privados; cache/configuração antiga; redirecionamento deve preservar fragmento reset; nenhuma origem é autorizada a partir de Host recebido; CORS/CSRF continuam com allowlist explícita. O conector Render não tem workspace confirmado: a topologia publicada só poderá ser conferida após confirmação; configuração versionada já localiza os dois serviços.

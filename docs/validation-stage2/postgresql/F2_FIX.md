# Correção exclusiva de F2

> O corpo abaixo registra a implementação e a validação anteriores ao commit local. O empacotamento final e os comandos atuais estão na seção seguinte; os caminhos de JSONs históricos são artefatos locais, não arquivos necessários no repositório.

## Empacotamento para o commit local

- Apenas código F2, README/status, este relatório, três módulos de teste e dois runners são incluídos. Graphify, caches, arquivos pessoais e resultados gerados permanecem fora do commit, preservados no disco.
- Testes independentes da auditoria local: `backend/tests/test_f2_login_resilience.py`, `test_f2_transaction_consistency.py` e `test_f2_postgresql.py`. As fixtures relevantes foram extraídas sem modificar os probes antigos. A seleção empacotada foi executada novamente: **PostgreSQL 16.15: 41 aprovados, zero falhos/ignorados; SQLite: 37 aprovados, quatro exclusivos de PostgreSQL ignorados, zero falhos**.
- Os runners registram o HEAD efetivo, dispensam o relatório local antigo e não exigem permanecer no commit-base anterior. Cada execução escreve em `runs/<identificador>/`, ignorado pelo Git, sem sobrescrever as evidências históricas. Não baixam imagens (`--pull=never`) nem instalam dependências. O ambiente Python existente deve conter as dependências declaradas do projeto; Docker e a imagem local `postgres:16-alpine` são necessários para PostgreSQL.
- Comandos atuais, na raiz do checkout, usando o Python do ambiente existente:

```powershell
rtk proxy python -B docs/validation-stage2/postgresql/run_f2_fix.py
rtk proxy python -B docs/validation-stage2/postgresql/run_f2_sqlite.py
```

- O teste F2 versionado exige 200, cookie utilizável em refresh e uma sessão confirmada, mesmo se `finish` estiver indisponível. Falhas antes do commit deixam zero sessões e reserva neutra. O probe posterior ao commit caracteriza a impossibilidade de rollback retroativo, sem alegar garantia de entrega HTTP.
- Ruff aprovado nos módulos/runners selecionados. O staging é conferido com `git diff --cached --check`; nenhum JSON, log, banco, credencial real ou arquivo Graphify integra a seleção. O hook Graphify dispõe de `GRAPHIFY_SKIP_HOOK=1`, usado somente no processo do commit, sem alterar configuração permanente.

Worktree `.worktrees/auth-security-stage2-sessions`, branch `fix/auth-security-stage2-sessions`, HEAD `5fe4134a5d79c58482a78c7ced0cf2413c9eee58`. Sem commit, publicação, migração, dependências novas, produção/homologação ou alteração de Graphify/outros worktrees.

## Causa e correção

`auth.login_user` confirma em `db.commit()` a mesma transação de CAS da senha, refresh, auditoria e sucesso da reserva. O middleware executava outro `finish` depois. Uma falha dessa gravação redundante substituía a resposta com cookie por 503.

A correção aproveita a transação existente: `login_reservation_committed` começa falso e só se torna verdadeiro depois que o commit retorna. O middleware dispensa `finish` quando esse marcador está verdadeiro, inclusive no caminho excepcional. Antes disso, mantém o tratamento existente. `finish` não mudou: UPDATE condicional continua idempotente. Sem consulta adicional, compensação pós-commit, schema ou arquitetura nova. JWT por ID, CAS, limites por conta/IP e refresh/logout não foram alterados.

## Evidência antes/depois

- `f2-before/f2.json`: o teste histórico reproduziu F2 em PostgreSQL: 503 sem cookie, uma linha de refresh e reserva `sucesso`. A rodada também executou regressões por erro de seleção do runner: 39 execuções, 37 aprovadas, uma falha F2 e um erro de coleta do módulo novo ainda não disponível. O erro de coleta é instrumentação, não produto.
- O teste F2 foi atualizado para exigir a política corrigida: 200, exatamente um refresh persistido, cookie utilizável em `/auth/refresh` e nenhuma chamada redundante a `finish`. Os JSONs históricos permanecem preservados; não se passou a aceitar a resposta contraditória.
- `f2-after/f2.json`: **41 aprovados, zero falhos/erros/ignorados**, PostgreSQL 16.15/UTF8/en_US.utf8/READ COMMITTED, fsync/synchronous_commit ativos. Inclui CAS bcrypt/Argon2 × reset, conta/IP, idempotência concorrente, cancelamento/leases, processos independentes, rotação simultânea, refresh/logout/replay/famílias e reset × exclusão.
- Novos testes: falha após flush de refresh antes do commit e falha do próprio commit deixam zero refresh e reserva neutra; falha na construção de resposta depois do commit caracteriza uma sessão já confirmada, sem tentar finalizá-la novamente. A perda real de conexão anterior ao commit também passou no probe PostgreSQL existente.
- `f2-sqlite/f2.json`: **37 aprovados, quatro ignorados exclusivos de PostgreSQL, zero falhos/erros**. SQLite não foi usado como evidência PostgreSQL.

O runner usa containers locais próprios, imagem já instalada, banco/usuário aleatórios, porta loopback, 1 CPU/512 MiB, tmpfs e limites de execução. Os dois containers desta correção foram removidos após conferir posse; zero schemas remanescentes e zero transações idle ao fim da rodada PostgreSQL.

Verificações finais: `git diff --check` aprovado; Ruff aprovado nos arquivos novos. Nos dois arquivos de produção, comparação com HEAD encontrou os mesmos 13 alertas preexistentes e zero alertas novos; não foram feitas correções de lint fora de escopo. Consulta final `docker ps -a` pelo prefixo dos containers não retornou recursos. Git mantém o HEAD informado, com quatro arquivos rastreados modificados (dois de produção, README e status), além dos testes/evidências não rastreados; nada em staging.

## Comandos e checks históricos

No worktree, usando o Python já instalado:

```powershell
rtk proxy C:\Users\Aluno\Documents\barbearia-agendamento\backend\.venv\Scripts\python.exe -B docs\validation-stage2\postgresql\run_f2_fix.py --before
rtk proxy C:\Users\Aluno\Documents\barbearia-agendamento\backend\.venv\Scripts\python.exe -B docs\validation-stage2\postgresql\run_f2_fix.py
rtk proxy C:\Users\Aluno\Documents\barbearia-agendamento\backend\.venv\Scripts\python.exe -B docs\validation-stage2\postgresql\run_f2_sqlite.py
rtk proxy git diff --check
```

`--before` foi usado com código/teste ainda não corrigidos; não desfaz arquivos. Os runners novos preservam o runner/JSONs anteriores; repetir uma opção sobrescreve somente os resultados correspondentes em `f2-*`. A chamada anterior à correção retornou 1; a posterior e a rodada SQLite concluída retornaram 0.

Houve duas falhas adicionais de instrumentação SQLite: permissão do sandbox no diretório temporário (reexecução autorizada fora do sandbox) e consulta de métricas `pg_stat_activity` no SQLite (guarda por dialect adicionada ao runner). Não foram contadas como falhas de produto nem ocultadas nos totais da rodada final. Node/navegador não executados: nenhum frontend alterado.

O campo genérico `prior_evidence_preserved=false` no JSON posterior reflete arquivos novos da própria correção criados durante a execução SQLite paralela. Comparação individual do manifesto anterior apontou alterações somente no teste F2 autorizado e nos scripts novos desta tarefa; relatórios, JSONs e demais testes anteriores não foram sobrescritos. Um script preparador temporário próprio foi removido após derivar o runner.

## Limites e entrega

Corrigiu-se a dependência evitável de uma segunda escrita após commit. Falhas posteriores de construção/serialização ou entrega da resposta ainda podem ocorrer depois da confirmação, conforme o probe pós-commit caracteriza. Não existe atomicidade entre PostgreSQL e entrega HTTP: desconexão, cancelamento tardio ou perda do ACK do commit podem deixar operação confirmada sem resposta recebida. O marcador não é publicado se commit lança exceção, mesmo quando o resultado ficou incerto no servidor; não há promessa de rollback nesses casos.

Arquivos de produção alterados: `backend/app/core/login_rate_limit.py` e `backend/app/routers/auth.py`. Teste F2 anterior atualizado; novo `backend/tests/test_f2_transaction_consistency.py`; README/status atualizados; runners e evidências novos nesta pasta. F2 corrigida para revisão. F1, HTTPS/cookies/topologia publicada, proxy/CSP e navegador continuam pendentes e fora desta tarefa; não há aprovação de implantação.

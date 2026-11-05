# SEC-01 e UX-01

- Base: origin/main 6409dd3; worktree isolado, sem alterar branches existentes.
- Auth: reproduzir exposição em teste; remover campo somente do login e schema; consumidores de testes passam a extrair cookie. Preservar rotação, revogação, Origin, CORS, rate limiting e atributos.
- Datas: validar formato, calendário e janela de São Paulo antes de disponibilidade e confirmação; testes focados Node e browser.
- Validar Python/SQLite, Node, Playwright pertinente, diff; atualizar Graphify e documentação; dois commits locais autorizados.
- Render: origens onrender.com distintas são cross-site (Public Suffix List). Lax não funciona nesse fetch mesmo com credentials include. Não alterar arquitetura nem relaxar cookie; propor HTTPS app/api no mesmo domínio registrável ou proxy de mesma origem antes de implantação.
- PostgreSQL somente se banco descartável explicitamente configurado. Nenhum dado real, push, merge ou deploy.

## Progresso e evidências

- Auth concluído, primeiro commit local ba82a2e; 13 testes focados e 31 na suíte auth/autorização aprovados (SQLite temporário).
- Datas: consulta por dia e confirmação por instante conforme backend; formato/calendário/janela, min/max, feedback acessível e descarte de respostas antigas implementados. 8 testes focados e 51 Node totais aprovados; 32 Python de agendamento aprovados.
- Revisão independente sem bloqueadores; diff sem erros. Playwright tentou iniciar, mas CLI ausente; PostgreSQL não configurado para testes, não executado. Cookie no Render não validado com sessão real; incompatibilidade cross-site documentada sem mudar arquitetura.

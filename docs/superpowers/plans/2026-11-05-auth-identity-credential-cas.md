# Identidade JWT e credencial concorrente

## Objetivo e limites
Corrigir somente reutilização de identidade por e-mail e restauração de senha durante login. Base HEAD64e4878, worktree separado; sem commit/publicação, produção ou novas dependências.

## Implementação
- [x] Regressões persistentes primeiro: duas contas descartáveis, rejeição de JWT legado/inválido/expirado/inativo, refresh com ID; corrida controlada por eventos em sessões independentes.
- [x] JWT sub canônico como ID positivo da conta; validar na emissão/decodificação e resolver somente User.id. Sem fallback por e-mail; legados exigem novo login ou refresh válido.
- [x] Guardar hash originalmente verificado; UPDATE condicional pelo ID/hash/estado ativo antes de emitir tokens, inclusive quando não houver upgrade. UPDATE mantém lock até commit; zero linhas implica rollback e 401 genérico. Não basta comparação em memória.
- [x] Adaptar somente fixtures emissoras de JWT nos testes existentes; executar regressões e suíte Python relevante, Node, diff e revisão independente.
- [x] Atualizar documentação e Graphify; não alterar refresh/reset/cookies nem schema.

## Riscos e validação
Tokens legados por e-mail são deliberadamente rejeitados; ID continua representando a mesma conta após mudança de e-mail, nunca uma nova conta que reutilize o endereço. Exclusão/inatividade continua invalidando o token.
PostgreSQL somente em banco descartável explicitamente configurado. Se indisponível, registrar ausência de validação concorrente nesse banco. Fixtures SQLite exclusivamente temporárias, sem dotenv e sem dados reais. Testes não imprimem credenciais, hashes ou tokens.

## Progresso
Dois cenários reproduzidos antes da correção e bloqueados depois. 7 testes novos, 38 auth/autorização, 8 recuperação, 7 configuração JWT e 51 Node aprovados. Suíte Python completa: 313 testes, 301 aprovados e 12 ignorados, sem falhas. Revisão independente sem defeitos de produção; reforços nos testes retestados. PostgreSQL não executado. Nenhum commit ou publicação.

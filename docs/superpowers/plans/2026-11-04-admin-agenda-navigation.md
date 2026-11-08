# Correção pontual de clientes e agenda administrativa

- Base: origin/main f565c29; branch fix/admin-agenda-navigation.
- Filtrar clientes inativos na listagem e nas consultas/alterações por ID;
  preservar bloqueados ativos, anonimização e histórico.
- Desacoplar agenda dos catálogos auxiliares, manter erros da agenda visíveis,
  proteger renderização de respostas antigas e habilitar semanas/teclado.
- Testes: regressões Python/SQLite e Node primeiro; depois suítes pertinentes
  e interação Playwright sem dados reais ou execução de migrações.
- Atualizar documentação, Graphify e revisar diff. Sem publicação.

## Progresso

- Implementação e revisão independente concluídas; anonimização preservada.
- Focados: autorização 14/14, LGPD 6/6 e agenda Node 9/9.
- Suítes pertinentes: integridade SQLite 9/9 e Node completo 43/43.
- E2E estático criado, mas não executado: Playwright ausente e npm ENOTFOUND.
  Não repetir instalação; não executar migrações/bancos reais. PostgreSQL não executado.
- Documentação e revisão final do diff concluídas; `git diff --check` sem erros.
- Graphify atualizado por AST; verificação final sem alterações relevantes pendentes.
- Sem commits, push, merge ou deploy; publicação depende de autorização.

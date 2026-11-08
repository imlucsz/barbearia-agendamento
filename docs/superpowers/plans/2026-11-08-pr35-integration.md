# Integração da PR35

- Preservar main em login JWT por ID, CAS, sessões, middleware e testes já integrados.
- Combinar somente a recuperação com admissão distribuída ainda inédita.
- Unir revisões 20261103_01 e 20261107_02 em 20261108_01 sem DDL; não editar revisões históricas.
- Validar upgrade vazio, legado e a partir de 20261107_02, paridade SQLAlchemy e downgrade recusado.
- Executar testes SQLite, Node e PostgreSQL apenas se houver cluster descartável seguro; atualizar evidências antes de commit/push na branch da PR.
- Sem merge na main, deploy, infraestrutura ou uso de dados reais.

# PR35 — integração com a segurança atual

Base de integração: main eaa942a. JWT por ID, CAS de senha, finalização transacional F2, sessões, refresh/logout, cookies e políticas de origem mantidos. O único acréscimo funcional recuperado desta branch histórica é a admissão de recuperação de senha por conta/IP, com cooldown, reserva compartilhada e finalização condicionada ao nonce.

## Resolução

- Testes e documentação de nomes, identidade e elegibilidade já integrados pela PR25 mantêm as versões atuais da main.
- O import de admissão de login foi combinado com o de recuperação, sem substituir o fluxo de login.
- A rota de esquecimento utiliza seu orçamento específico; login/register/reset mantêm o middleware atual. Respostas continuam genéricas para conta existente/inexistente, cooldown e falha de entrega.
- O código não segura transação de escrita durante envio de e-mail. Falha de entrega elimina o token novo sem invalidar o anterior; nonce protege finalização tardia.
- Migrações históricas não editadas: revisão aditiva 20261103_01 preservada. Nova revisão de merge 20261108_01 une 20261103_01 e 20261107_02, sem DDL, backfill ou exclusão de dados. Downgrade integrado recusado; recuperação é forward-only.
- Fixtures de legado excluem a tabela nova; testes antigos de downgrade da revisão de recuperação exercitam somente aquela linha antes da união. Upgrade vazio, paridade e upgrade a partir do head publicado têm cobertura própria.

## Reprodução e isolamento

SQLite completo: em backend, `python -B -m unittest discover -s tests`, com BOOKING_TEST_BACKEND=sqlite e harness de bancos temporários. Node: `node --test frontend/tests`.

PostgreSQL: `python tools/run-recovery-integration-postgres.py`. Exige Docker e imagem postgres:16-alpine já presentes; não instala nem baixa imagem. Cria container/volumes próprios, porta aleatória só em loopback, usuário/banco/senha efêmeros. Recusa alvo externo; nenhum container preexistente é usado ou removido. O runner remove apenas seus recursos no finally e não imprime credenciais.

O conjunto PostgreSQL inclui também testes explicitamente SQLite de migração; estes não são contados como validações PostgreSQL. Nenhuma alteração de dados publicados ou configuração Render.

## Resultados executados

- Suíte Python completa em SQLite temporário: 399 testes em 371,373 s, **382 aprovados, 17 ignorados**, sem falhas/erros.
- PostgreSQL **16.15** descartável: seleção de 53 testes em 78,572 s, **53 aprovados**, zero ignorados. **45 utilizam o harness PostgreSQL e 8 são testes explicitamente SQLite**; não confundir as duas validações. Cobertura de migrações, recuperação, processos independentes, concorrência de sessões e autorização. Container/volumes próprios removidos, container preexistente preservado.
- Node: **56 aprovados**, sem falhas. Nenhuma dependência instalada.
- Diff de entrega comparado com main: sem erros de whitespace; nenhuma entrada não resolvida. As revisões Alembic históricas mantêm seus bytes. Graphify atualizado localmente por AST; caches não incluídos.
- Rodada inicial direcionada: uma falha de paridade antes da integração das duas linhas e um erro na fixture legada. Fixtures corrigidas; upgrade integrado e proteção de downgrade aprovados na suíte completa final e no conjunto PostgreSQL.
- Navegador não repetido nesta resolução: fluxo de recuperação conserva o teste Node e o teste de navegador persistente; validar o job Playwright remoto antes de merge. Nenhuma validação publicada foi alegada.

## Implantação e recuperação

Antes de merge, aguardar CI e revisar o novo head e a admissão de recuperação. Render monitora main com auto-deploy/autoSync: merge exige coordenação operacional. Aplicar upgrade head antes de iniciar os writers; manter configuração de origem única e secrets existentes. Não aplicar downgrade/drop/stamp. Rollback de aplicação só com versão compatível com o schema aditivo, mantendo dados de limites. Limitações de lease de envio e enumeração temporal existentes não foram eliminadas.

Os documentos de novembro 3/4 nesta branch são históricos; para comportamento final e resultados, usar este relatório.

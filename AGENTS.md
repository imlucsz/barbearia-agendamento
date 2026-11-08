# Instruções do projeto

- Projeto: sistema de agendamento para uma barbearia por instalação.
- Stack: FastAPI, SQLAlchemy, Pydantic, HTML, CSS e JavaScript ES Modules.
- Não implementar multi-tenancy nem reescrever a arquitetura sem necessidade.
- Preservar funcionalidades, contratos da API, alterações locais e dados existentes.
- Antes de alterar código, inspecionar somente os arquivos relevantes.
- Fazer mudanças pequenas e focadas, sem refatorações fora do escopo.
- Executar os testes relevantes após cada alteração e informar os resultados reais.
- Não fazer commit, push, merge, deploy nem descartar alterações locais sem autorização explícita do usuário.
- Resposta final: resumo, arquivos modificados, testes e pendências.

## Autonomia dentro do escopo

- O pedido do usuário autoriza as etapas operacionais normais necessárias à conclusão da tarefa.
- Execute sem confirmação intermediária as leituras e buscas de arquivos; o uso de Graphify; a edição/criação de arquivos necessários dentro do escopo; testes, lint, typecheck e auditorias pertinentes; Git somente leitura; ciclos implementação -> teste -> correção; e subagentes conforme as regras atuais.
- Para escolhas técnicas pequenas, reversíveis e de baixo risco, escolha a opção mais conservadora e continue. Não peça nova aprovação para cada etapa quando objetivo e escopo já estiverem claros.
- Exija autorização explícita antes de commit, push, merge, deploy, reset/clean/restore destrutivo, apagar ou sobrescrever trabalho preexistente, operações em produção ou dados reais, alteração de secrets/credenciais reais, migrações destrutivas, mudanças destrutivas de infraestrutura ou expansão material do escopo.
- Relate problemas preexistentes e não relacionados sem ampliar silenciosamente a tarefa.
- Se uma operação for tecnicamente bloqueada, conclua primeiro todo trabalho independente permitido e então peça uma única autorização concreta, explicando o motivo.

## Fluxo eficiente de contexto

- Antes de iniciar uma tarefa neste repositório, leia e aplique `.agents/skills/token-efficient-workflow/SKILL.md`.
- Consulte `PROJECT_EXCLUSIONS.md` antes de buscas amplas ou leitura de arquivos grandes; trate-o como orientação de fluxo, não como controle de acesso ou garantia de sigilo.
- Para buscas, usos de símbolos, lista de arquivos alterados e resumos, prefira os scripts em `tools/codex-helpers/` quando forem adequados.
- Esses scripts são auxiliares: confira os resultados e use comandos diretos quando o caso exigir. Eles não substituem testes nem revisão manual.
- Para decidir e coordenar o uso de subagentes, aplique a seção 11 de `.agents/skills/barbearia-safe-change/SKILL.md`. Use somente os parâmetros expostos pelas ferramentas da sessão; adapte exemplos das skills quando houver divergência com o runtime, preservando as restrições deste projeto.

## Planejamento e verificação

- Mudanças cross-cutting, arquiteturais ou de alto risco exigem plano explícito antes de implementar; reutilize `docs/superpowers/plans/` e seu modelo curto. Atualize o plano durante tarefas longas. Mudanças pequenas e reversíveis continuam com execução direta.
- Após mudanças relevantes, execute os checks baratos relacionados e `git diff --check`; use formatter/lint/typecheck quando já configurados. Suítes pesadas (Playwright completo e PostgreSQL) ficam para o fechamento das tarefas que as exigirem, não para cada edição.


## Padrão de entrega (toda tarefa de requisito)

```
- Schema: nova revisão Alembic encadeada à última; nunca editar revisões existentes, nunca stamp, nunca drop de tabela ou dado; modelos SQLAlchemy e migrações coerentes (manter o teste de paridade).
- Testes: bancos temporários exclusivos; SQLite sempre; PostgreSQL automatizado só em banco descartável explicitamente configurado para testes, senão informar «não executado». Nunca executar testes contra banco de dev ou de produção.
- Contratos: não quebrar rotas, schemas nem telas existentes; mudança incompatível exige aviso explícito.
- Segurança: nunca imprimir segredos, tokens, senhas, hashes ou URLs de banco; dados de teste fictícios.
- Interface: reutilizar os tokens de installation.css; visual sóbrio no estilo Linear, Vercel e Stripe, com cantos retos e bordas finas, alto contraste com suporte a Dark Mode, fonte monoespaçada para números, datas e métricas e layout denso e funcional; sem gradientes sem propósito nem espaço em branco inútil; não reescrever telas existentes.
- Documentação: atualizar docs/REQUISITOS_STATUS.md (status e evidência) e o README só no que mudou.
- Validação: testes Python, testes Node e git diff --check; sem commit.
- Relatório final: requisitos atendidos, arquivos alterados, comandos reais com resultados, pendências.
```

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

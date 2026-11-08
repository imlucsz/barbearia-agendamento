# Planos de implementação

Esta pasta é o equivalente local a `PLANS.md`; mantenha os planos existentes como histórico.

Crie um plano antes de mudanças cross-cutting, arquiteturais ou de alto risco. Correções pequenas, localizadas e reversíveis podem ser executadas diretamente. Requisitos ambíguos ou expansão material de escopo precisam ser resolvidos antes da implementação.

Use um arquivo `AAAA-MM-DD-assunto.md` com este formato curto:

```markdown
# Objetivo e limites
O que muda e o que deve ser preservado.

## Aceite
- Comportamentos verificáveis que encerram a tarefa.

## Áreas e etapas
- [ ] Arquivos/áreas envolvidos e mudança proposta.

## Riscos e recuperação
Contratos, dados e riscos relevantes; como recuperar apenas esta mudança,
quando aplicável, sem descartar trabalho local ou executar ações destrutivas.

## Validação
Checks baratos durante as etapas; testes pesados somente quando pertinentes.
Usar bancos temporários exclusivos; PostgreSQL apenas descartável de teste.

## Progresso e evidências
Etapas concluídas, resultados reais, decisões e pendências.
```

Atualize o mesmo plano durante tarefas longas, inclusive quando o escopo ou a validação mudar. Planos antigos não substituem decisões atuais registradas em `specs/` nem autorizam operações protegidas por `AGENTS.md`.

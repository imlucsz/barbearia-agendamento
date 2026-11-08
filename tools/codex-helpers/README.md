# Codex helpers

PowerShell helpers adapted from [Creativebrook/codex-token-optimizer-kit](https://github.com/Creativebrook/codex-token-optimizer-kit). They require `rg` (ripgrep) and/or Git on `PATH`.

Run from the repository root:

```powershell
.\tools\codex-helpers\search_symbol.ps1 "Appointment"
.\tools\codex-helpers\find_usages.ps1 "create_appointment"
.\tools\codex-helpers\list_changed_files.ps1
.\tools\codex-helpers\summarize_file.ps1 .\README.md
```

Search helpers skip common generated folders, local virtual environments, local database files, logs, and credential-like files. `summarize_file.ps1` refuses common sensitive filenames and binary data extensions. These are convenience safeguards, not a security boundary; review the target before reading it.

PowerShell's execution policy may block these scripts. Do not weaken or bypass that policy just to run a helper; use the equivalent direct Git or ripgrep command instead.

The upstream kit does not automatically force Codex to call the helpers. This project references the workflow in `AGENTS.md` and provides the local skill at `.agents/skills/token-efficient-workflow/SKILL.md`.

## Workflow local do Codex

- Planos: reutilizar [a pasta existente e o modelo curto](../../docs/superpowers/plans/README.md) para mudanças complexas; tarefas triviais seguem diretamente.
- Decisões confirmadas da HOME: [spec](../../specs/home-experience.md). Planos históricos não redefinem essa direção.
- Graphify: consultar antes da primeira busca/leitura de código, conforme `AGENTS.md`; após alterar código, executar `rtk proxy graphify update .` (AST, sem API).
- Compactação: no CLI, usar `/compact` quando a conversa crescer; manter objetivo, restrições, progresso e pendências no plano antes disso. Não criar um novo plano para tarefas triviais.
- Subagentes: somente quando as regras da sessão e a seção 11 de `barbearia-safe-change` permitirem, para subtarefas independentes com ganho claro. Não são requisito para toda tarefa.
- Worktrees automáticos, MCP novo, headless e CI novo não foram configurados.

### Checks e hooks

`.codex/hooks.json` preserva `PreToolUse`/`Bash` com `graphify hook-check` e acrescenta apenas `PostToolUse`/`apply_patch` com `rtk proxy git diff --check`. Reutiliza o mecanismo do Codex, sem instalar hook Git. O matcher `Bash` também cobre `exec_command`.

Hooks locais exigem confiança no projeto e revisão da definição atual: no CLI, conferir `/hooks` e confiar no hook após revisão, se solicitado. A execução automática nesta sessão não é presumida; o comando é validado também diretamente. Não contornar a revisão de confiança.

O check de whitespace cobre o diff rastreado, não arquivos untracked; estes precisam de revisão explícita. Edições feitas por shell ou ferramentas diferentes de `apply_patch` exigem executar o check diretamente. Ele não formata, não altera arquivos e não substitui testes.

Não há scripts de formatter/lint no `package.json` atual. Não instalar ferramentas apenas para o hook. Escolher testes locais baratos conforme os arquivos alterados (por exemplo, `rtk proxy node --test frontend/tests/arquivo.test.mjs`); manter Playwright completo e PostgreSQL fora dos hooks e executar no fechamento quando exigidos pelo escopo.

### Instruções versus proteção técnica

`AGENTS.md` orienta o comportamento: leitura, pesquisa, edição no workspace, testes locais, lint/typecheck, Graphify e Git somente leitura são autônomos dentro do escopo. Commit/push/merge/deploy, reset/clean/restore destrutivo, produção, dados ou secrets reais, migrações e infraestrutura destrutivas continuam exigindo autorização explícita. Autorização para alterar código não autoriza esses atos.

Sandbox e política de aprovação são controles técnicos separados; o texto de `AGENTS.md`, as exclusões de busca e os hooks de qualidade não impedem tecnicamente o acesso a um banco real. Nunca testar contra desenvolvimento/produção. SQLite deve ser temporário e exclusivo; PostgreSQL automatizado somente em banco descartável explicitamente configurado para testes, sem reutilizar credenciais reais.

Auditoria desta rodada: configuração global consultada apenas nos campos não sensíveis de execução (`sandbox_mode = workspace-write`, `approval_policy = on-request`); sem `config.toml` local. Nenhuma permissão global foi alterada. O sandbox efetivo e as políticas gerenciadas da sessão podem restringir mais que esses valores. Mantenha esse isolamento; qualquer endurecimento global adicional deve ser proposto com seus efeitos antes de ser aplicado.

Referências oficiais: [hooks e revisão de confiança](https://learn.chatgpt.com/docs/hooks), [sandbox e aprovações](https://learn.chatgpt.com/docs/agent-approvals-security), [comandos do CLI](https://developers.openai.com/codex/cli/slash-commands).

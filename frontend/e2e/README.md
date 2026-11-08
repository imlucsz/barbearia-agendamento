# E2E com Playwright

A suíte usa `@playwright/test` já listado nas dependências locais e Chromium. O
ambiente é criado do zero a cada execução: Alembic migra um SQLite em uma pasta
temporária, `seed_database.py` verifica que o arquivo está nessa pasta e cria
somente usuários, serviços, jornadas, bloqueio e atendimentos fictícios. SMTP é
desabilitado e nenhum endpoint de seed da aplicação é chamado. O script encerra
os servidores e remove apenas seu diretório temporário ao fim do Playwright.

Execute a partir da raiz do repositório:

```powershell
npx.cmd playwright test --config=frontend/e2e/playwright.config.mjs
```

Os projetos executam os fluxos em 1280×800 e 390×844. Screenshots e traces
ficam em `test-results/e2e/`, ignorado pelo Git. Não instale axe nesta suíte:
os critérios básicos pedidos são cobertos com navegação real por teclado,
`document.activeElement`, estilo `:focus-visible`, labels e validação HTML nativa.

Se Chromium não estiver instalado localmente, o comando para instalar somente
esse navegador é `npx.cmd playwright install chromium` (requer acesso à rede).

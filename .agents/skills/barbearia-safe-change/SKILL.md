---
name: barbearia-safe-change
description: Fluxo seguro, economico e verificavel para alteracoes no projeto barbearia-agendamento.
---



\# Barbearia Safe Change



Use esta skill para implementar, corrigir, refatorar ou revisar alteraÃ§Ãµes no projeto `barbearia-agendamento`.



\## Objetivos



\- Minimizar consumo de contexto e tokens.

\- Entender o impacto antes de alterar cÃ³digo.

\- Fazer a menor mudanÃ§a correta possÃ­vel.

\- Preservar alteraÃ§Ãµes locais existentes.

\- Evitar regressÃµes.

\- Manter seguranÃ§a, banco, migraÃ§Ãµes e contratos consistentes.

\- NÃ£o executar aÃ§Ãµes irreversÃ­veis ou publicar alteraÃ§Ãµes sem autorizaÃ§Ã£o explÃ­cita.



\## 1. Preserve o estado atual



Antes de alterar arquivos:



1\. Execute `git status --short`.

2\. Considere modificaÃ§Ãµes existentes como trabalho do usuÃ¡rio.

3\. NÃ£o reverta, sobrescreva, mova, apague ou inclua alteraÃ§Ãµes nÃ£o relacionadas.

4\. Nunca execute automaticamente:

&#x20;  - `git reset --hard`

&#x20;  - `git clean`

&#x20;  - `git restore` sobre trabalho existente

&#x20;  - comandos destrutivos equivalentes

5\. NÃ£o faÃ§a commit, push, merge, deploy ou alteraÃ§Ã£o em produÃ§Ã£o sem autorizaÃ§Ã£o explÃ­cita.

6\. Nunca exponha secrets, tokens, senhas, hashes ou URLs de banco contendo credenciais.



Arquivos/diretÃ³rios locais ou de trabalho devem ser preservados quando nÃ£o fizerem parte da tarefa, incluindo:



\- `AGENTS.md`

\- `GUIA.md`

\- `docs/business/`

\- `graphify-out/`



O fato de um arquivo estar modificado ou nÃ£o rastreado nÃ£o autoriza sua alteraÃ§Ã£o.



\## 2. Graphify primeiro



Para perguntas ou tarefas relacionadas ao cÃ³digo:



1\. Consulte o knowledge graph antes de buscas amplas.

2\. Prefira consultas pequenas e especÃ­ficas.



Exemplo:



`graphify query "<pergunta especÃ­fica>" --budget 800`



Use tambÃ©m quando adequado:



\- `graphify explain "<sÃ­mbolo>"`

\- `graphify path "<A>" "<B>"`

\- `graphify affected "<sÃ­mbolo>"`



3\. NÃ£o aumente automaticamente o orÃ§amento sÃ³ porque a resposta foi truncada.

4\. Primeiro refine a pergunta, o sÃ­mbolo ou o contexto.

5\. Leia arquivos brutos somente depois que Graphify, Git, testes ou uma busca direcionada indicarem quais arquivos sÃ£o relevantes.

6\. NÃ£o leia o repositÃ³rio inteiro por padrÃ£o.



Se Graphify nÃ£o tiver informaÃ§Ã£o suficiente, use busca direcionada com `rg`, helpers do projeto ou Git.



\## 3. Diagnostique antes de implementar



Antes de editar:



1\. Defina o comportamento atual.

2\. Defina o comportamento esperado.

3\. Localize os arquivos e sÃ­mbolos envolvidos.

4\. Identifique contratos e testes relacionados.

5\. Determine o risco da mudanÃ§a.



Para bugs, tente reproduzir ou localizar evidÃªncia concreta antes da correÃ§Ã£o.



NÃ£o altere cÃ³digo apenas com base em hipÃ³tese quando houver forma razoÃ¡vel de verificar a causa.



\## 4. Escolha o menor escopo



Prefira:



\- alteraÃ§Ã£o localizada;

\- reutilizaÃ§Ã£o de estruturas existentes;

\- compatibilidade com contratos atuais;

\- testes focados.



Evite:



\- refatoraÃ§Ãµes nÃ£o solicitadas;

\- reescrita de arquivos inteiros;

\- mudanÃ§as cosmÃ©ticas nÃ£o relacionadas;

\- novas dependÃªncias sem necessidade;

\- criaÃ§Ã£o de abstraÃ§Ãµes prematuras.



Se encontrar outro problema nÃ£o relacionado, informe-o separadamente em vez de expandir silenciosamente a tarefa.



\## 5. Banco de dados e Alembic



Para mudanÃ§as de schema:



\- modelos SQLAlchemy e migraÃ§Ãµes devem permanecer coerentes;

\- criar nova revisÃ£o Alembic encadeada Ã  revisÃ£o atual;

\- nÃ£o editar migraÃ§Ãµes histÃ³ricas jÃ¡ aplicadas;

\- nÃ£o usar `stamp` como atalho para esconder inconsistÃªncia;

\- nÃ£o apagar tabelas ou dados reais;

\- preservar compatibilidade e dados existentes sempre que aplicÃ¡vel.



Testes de banco devem usar bancos temporÃ¡rios/descartÃ¡veis.



Nunca executar migraÃ§Ã£o destrutiva ou experimental no banco de produÃ§Ã£o.



PostgreSQL real de produÃ§Ã£o exige autorizaÃ§Ã£o explÃ­cita.



\## 6. SeguranÃ§a



MudanÃ§as envolvendo qualquer item abaixo recebem revisÃ£o de seguranÃ§a adicional:



\- autenticaÃ§Ã£o;

\- autorizaÃ§Ã£o;

\- JWT/sessÃµes;

\- recuperaÃ§Ã£o de senha;

\- e-mail de autenticaÃ§Ã£o;

\- upload;

\- dados pessoais/LGPD;

\- endpoints administrativos;

\- banco de dados;

\- CORS;

\- proxy/IP;

\- secrets;

\- integraÃ§Ãµes externas.



Verifique conforme aplicÃ¡vel:



\- validaÃ§Ã£o de entrada;

\- autorizaÃ§Ã£o por papel e propriedade;

\- exposiÃ§Ã£o de dados;

\- mensagens de erro;

\- armazenamento de secrets;

\- enumeraÃ§Ã£o de usuÃ¡rios;

\- replay/expiraÃ§Ã£o de tokens;

\- integridade e concorrÃªncia.



NÃ£o enfraqueÃ§a controles de seguranÃ§a apenas para fazer um teste ou deploy passar.



\## 7. Testes proporcionais ao risco



NÃ£o execute toda a suÃ­te automaticamente para qualquer alteraÃ§Ã£o.



Comece pelos testes diretamente relacionados.



Amplie a validaÃ§Ã£o conforme o risco.



\### AlteraÃ§Ã£o pequena e isolada



Execute testes focados.



\### Backend/regra de negÃ³cio



Execute testes focados e testes relacionados do backend.



\### Banco/migraÃ§Ã£o/integridade



Execute os testes relevantes em SQLite quando aplicÃ¡vel e PostgreSQL descartÃ¡vel quando necessÃ¡rio.



\### Frontend



Execute testes JS relacionados.



Use Playwright quando a mudanÃ§a afetar fluxo real do usuÃ¡rio, integraÃ§Ã£o frontend/backend ou comportamento visual/interativo importante.



\### Auth, autorizaÃ§Ã£o, agenda, pagamentos futuros, migraÃ§Ãµes ou alteraÃ§Ã£o transversal



Considere suÃ­te mais ampla antes de concluir.



NÃ£o execute testes caros sem relaÃ§Ã£o com a mudanÃ§a apenas para produzir uma lista maior de testes aprovados.



\## 8. ImplementaÃ§Ã£o



Durante a implementaÃ§Ã£o:



1\. FaÃ§a alteraÃ§Ãµes pequenas.

2\. Preserve estilo e arquitetura existentes.

3\. NÃ£o quebre rotas, schemas ou comportamento pÃºblico sem necessidade explÃ­cita.

4\. NÃ£o esconda erros apenas para fazer testes passarem.

5\. NÃ£o altere testes para aceitar comportamento incorreto.

6\. Adicione ou atualize testes quando houver mudanÃ§a real de comportamento.



\## 9. Atualize o Graphify



Depois de alteraÃ§Ãµes de cÃ³digo bem-sucedidas:



`graphify update .`



NÃ£o faÃ§a reconstruÃ§Ãµes completas com LLM quando uma atualizaÃ§Ã£o AST local for suficiente.



\## 10. Revise o diff



Antes de concluir:



1\. Execute `git diff --check`.

2\. Examine `git diff` somente nos arquivos relacionados Ã  tarefa.

3\. Confirme que nÃ£o houve alteraÃ§Ã£o acidental.

4\. Confira novamente `git status --short`.

5\. NÃ£o inclua arquivos locais nÃ£o relacionados.



## 11. Uso de agentes

### Quando delegar

O agente principal resolve tarefas triviais. Delegue somente quando o
isolamento de contexto, a especialização ou a revisão independente
compensarem o custo de iniciar outro agente.

Papéis operacionais, definidos no message:
- implementer: implementação delimitada e validação pertinente;
- reviewer: revisão de requisitos, qualidade e regressões, somente leitura;
- security reviewer: revisão somente leitura dos riscos aplicáveis da seção 6.

As revisões obrigatórias do workflow Superpowers escolhido continuam válidas.
Não acione o fluxo SDD completo para uma microtarefa apenas para delegá-la.

### Como criar

Use collaboration.spawn_agent com task_name, message, fork_turns,
model e reasoning_effort. Não use parâmetros de seleção de papel
ausentes do schema exposto nesta sessão.

Use fork_turns="none" por padrão para agentes especializados; ele é
obrigatório nesta sessão quando model ou reasoning_effort forem
sobrescritos. Especifique ambos para evitar herança involuntária do
modelo/esforço do principal.

O message deve conter apenas:
- papel operacional e objetivo;
- raiz do projeto e caminhos das regras aplicáveis;
- requisitos e critérios de aceite da tarefa;
- arquivos/símbolos conhecidos, interfaces relevantes e limites de edição;
- alterações locais que precisam ser preservadas;
- validação esperada e formato curto do retorno.

Instrua o subagente a ler AGENTS.md, RTK.md e as skills locais
token-efficient-workflow e barbearia-safe-change. Não copie o histórico,
o plano inteiro ou o conteúdo completo dessas regras no message.

Quando houver exploração de código, inclua explicitamente:
“Se graphify-out/graph.json existir, execute graphify query com uma
pergunta específica antes da primeira busca ou leitura de código,
conforme AGENTS.md. Leia somente os trechos localizados.”

### Coordenação e correções

Somente o agente principal cria e coordena subagentes; inclua no message
a instrução de não criar outros agentes.

Registre a identidade retornada pelo spawn. Para esclarecer ou corrigir
a mesma tarefa, use collaboration.followup_task no mesmo implementer.
Reutilize também o reviewer para revisar as correções delimitadas.

Crie outro agente quando houver tarefa independente, necessidade
concretamente justificada de outro modelo/esforço ou indisponibilidade
do agente anterior.

Implemente antes de revisar. Reviewer e security reviewer podem atuar
em paralelo sobre o mesmo estado estável, com escopos complementares.
Não permita implementações concorrentes no mesmo workspace.
Paralelize investigações independentes somente com benefício concreto,
sem duplicar trabalho nem interferir em arquivos ou recursos comuns.

Enquanto houver trabalho independente, prossiga com ele. Quando ocioso,
use wait_agent para aguardar eventos, respeitando os limites e a cadência
de comunicação da sessão. Não faça polling repetido com timeouts curtos
nem chamadas sucessivas de list_agents sem motivo.

### Preservação e revisão

Aplique a seção 1 a todos os agentes. Uma instrução de commit, push,
merge ou deploy em um template não constitui autorização do usuário.

Sem commits autorizados, forneça ao reviewer o recorte das alterações
da tarefa em relação ao estado inicial, incluindo arquivos novos
pertinentes. Não use somente HEAD~1..HEAD para revisar trabalho sem commit
nem atribua alterações locais anteriores ao implementer.

O agente principal coordena a atualização do Graphify após alterações
de código, conforme a seção 9, evitando atualizações concorrentes.
Revisores não atualizam o grafo.

Retornos devem informar resultado, arquivos envolvidos, evidências de
validação e pendências. Não repita testes já comprovados sobre o mesmo
estado sem mudança ou preocupação concreta que justifique a repetição.

### Modelo e esforço

O agente principal escolhe explicitamente model e reasoning_effort
proporcionais à tarefa, usando somente modelos e esforços realmente
disponíveis no runtime. Não há modelo obrigatório.

Priorize modelos mais econômicos e esforço low para tarefas
mecânicas/simples. Use medium para tarefas com julgamento moderado.
Reserve high ou superior, quando disponível, para segurança,
arquitetura, concorrência, integridade ou problemas realmente complexos.

Aplique a política de seleção do Superpowers considerando custo total
e capacidade necessária, sem deduzir preços pelo nome do modelo.
Não escale modelo ou esforço sem justificativa concreta, como risco,
complexidade ou falha observada; registre a razão ao escalar.

\## 12. Economia de contexto



Prefira, nesta ordem:



1\. Graphify especÃ­fico;

2\. Git para mudanÃ§as;

3\. helpers existentes;

4\. `rg` direcionado;

5\. leitura de trechos relevantes;

6\. leitura de arquivo completo somente quando necessÃ¡ria;

7\. busca ampla apenas como Ãºltimo recurso.



NÃ£o releia arquivos jÃ¡ compreendidos sem motivo.



NÃ£o despeje logs enormes no contexto quando resumo + trecho relevante forem suficientes.



\## 13. Encerramento



O relatÃ³rio final deve ser curto e verificÃ¡vel.



Informe:



\- causa ou objetivo;

\- o que mudou;

\- arquivos alterados;

\- testes realmente executados e resultados;

\- riscos ou pendÃªncias;

\- aÃ§Ãµes que exigem autorizaÃ§Ã£o do usuÃ¡rio.



Nunca diga que algo foi testado, validado, implantado ou estÃ¡ pronto para produÃ§Ã£o se isso nÃ£o tiver sido efetivamente comprovado.

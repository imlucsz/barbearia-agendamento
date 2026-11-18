---
name: barbearia-safe-change
description: Fluxo seguro, economico e verificavel para alteracoes no projeto barbearia-agendamento.
---



\# Barbearia Safe Change



Use esta skill para implementar, corrigir, refatorar ou revisar alterações no projeto `barbearia-agendamento`.



\## Objetivos



\- Minimizar consumo de contexto e tokens.

\- Entender o impacto antes de alterar código.

\- Fazer a menor mudança correta possível.

\- Preservar alterações locais existentes.

\- Evitar regressões.

\- Manter segurança, banco, migrações e contratos consistentes.

\- Não executar ações irreversíveis ou publicar alterações sem autorização explícita.



\## 1. Preserve o estado atual



Antes de alterar arquivos:



1\. Execute `git status --short`.

2\. Considere modificações existentes como trabalho do usuário.

3\. Não reverta, sobrescreva, mova, apague ou inclua alterações não relacionadas.

4\. Nunca execute automaticamente:

&#x20;  - `git reset --hard`

&#x20;  - `git clean`

&#x20;  - `git restore` sobre trabalho existente

&#x20;  - comandos destrutivos equivalentes

5\. Não faça commit, push, merge, deploy ou alteração em produção sem autorização explícita.

6\. Nunca exponha secrets, tokens, senhas, hashes ou URLs de banco contendo credenciais.



Arquivos/diretórios locais ou de trabalho devem ser preservados quando não fizerem parte da tarefa, incluindo:



\- `AGENTS.md`

\- `GUIA.md`

\- `docs/business/`

\- `graphify-out/`



O fato de um arquivo estar modificado ou não rastreado não autoriza sua alteração.



\## 2. Graphify primeiro



Para perguntas ou tarefas relacionadas ao código:



1\. Consulte o knowledge graph antes de buscas amplas.

2\. Prefira consultas pequenas e específicas.



Exemplo:



`graphify query "<pergunta específica>" --budget 800`



Use também quando adequado:



\- `graphify explain "<símbolo>"`

\- `graphify path "<A>" "<B>"`

\- `graphify affected "<símbolo>"`



3\. Não aumente automaticamente o orçamento só porque a resposta foi truncada.

4\. Primeiro refine a pergunta, o símbolo ou o contexto.

5\. Leia arquivos brutos somente depois que Graphify, Git, testes ou uma busca direcionada indicarem quais arquivos são relevantes.

6\. Não leia o repositório inteiro por padrão.



Se Graphify não tiver informação suficiente, use busca direcionada com `rg`, helpers do projeto ou Git.



\## 3. Diagnostique antes de implementar



Antes de editar:



1\. Defina o comportamento atual.

2\. Defina o comportamento esperado.

3\. Localize os arquivos e símbolos envolvidos.

4\. Identifique contratos e testes relacionados.

5\. Determine o risco da mudança.



Para bugs, tente reproduzir ou localizar evidência concreta antes da correção.



Não altere código apenas com base em hipótese quando houver forma razoável de verificar a causa.



\## 4. Escolha o menor escopo



Prefira:



\- alteração localizada;

\- reutilização de estruturas existentes;

\- compatibilidade com contratos atuais;

\- testes focados.



Evite:



\- refatorações não solicitadas;

\- reescrita de arquivos inteiros;

\- mudanças cosméticas não relacionadas;

\- novas dependências sem necessidade;

\- criação de abstrações prematuras.



Se encontrar outro problema não relacionado, informe-o separadamente em vez de expandir silenciosamente a tarefa.



\## 5. Banco de dados e Alembic



Para mudanças de schema:



\- modelos SQLAlchemy e migrações devem permanecer coerentes;

\- criar nova revisão Alembic encadeada à revisão atual;

\- não editar migrações históricas já aplicadas;

\- não usar `stamp` como atalho para esconder inconsistência;

\- não apagar tabelas ou dados reais;

\- preservar compatibilidade e dados existentes sempre que aplicável.



Testes de banco devem usar bancos temporários/descartáveis.



Nunca executar migração destrutiva ou experimental no banco de produção.



PostgreSQL real de produção exige autorização explícita.



\## 6. Segurança



Mudanças envolvendo qualquer item abaixo recebem revisão de segurança adicional:



\- autenticação;

\- autorização;

\- JWT/sessões;

\- recuperação de senha;

\- e-mail de autenticação;

\- upload;

\- dados pessoais/LGPD;

\- endpoints administrativos;

\- banco de dados;

\- CORS;

\- proxy/IP;

\- secrets;

\- integrações externas.



Verifique conforme aplicável:



\- validação de entrada;

\- autorização por papel e propriedade;

\- exposição de dados;

\- mensagens de erro;

\- armazenamento de secrets;

\- enumeração de usuários;

\- replay/expiração de tokens;

\- integridade e concorrência.



Não enfraqueça controles de segurança apenas para fazer um teste ou deploy passar.



\## 7. Testes proporcionais ao risco



Não execute toda a suíte automaticamente para qualquer alteração.



Comece pelos testes diretamente relacionados.



Amplie a validação conforme o risco.



\### Alteração pequena e isolada



Execute testes focados.



\### Backend/regra de negócio



Execute testes focados e testes relacionados do backend.



\### Banco/migração/integridade



Execute os testes relevantes em SQLite quando aplicável e PostgreSQL descartável quando necessário.



\### Frontend



Execute testes JS relacionados.



Use Playwright quando a mudança afetar fluxo real do usuário, integração frontend/backend ou comportamento visual/interativo importante.



\### Auth, autorização, agenda, pagamentos futuros, migrações ou alteração transversal



Considere suíte mais ampla antes de concluir.



Não execute testes caros sem relação com a mudança apenas para produzir uma lista maior de testes aprovados.



\## 8. Implementação



Durante a implementação:



1\. Faça alterações pequenas.

2\. Preserve estilo e arquitetura existentes.

3\. Não quebre rotas, schemas ou comportamento público sem necessidade explícita.

4\. Não esconda erros apenas para fazer testes passarem.

5\. Não altere testes para aceitar comportamento incorreto.

6\. Adicione ou atualize testes quando houver mudança real de comportamento.



\## 9. Atualize o Graphify



Depois de alterações de código bem-sucedidas:



`graphify update .`



Não faça reconstruções completas com LLM quando uma atualização AST local for suficiente.



\## 10. Revise o diff



Antes de concluir:



1\. Execute `git diff --check`.

2\. Examine `git diff` somente nos arquivos relacionados à tarefa.

3\. Confirme que não houve alteração acidental.

4\. Confira novamente `git status --short`.

5\. Não inclua arquivos locais não relacionados.



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



1\. Graphify específico;

2\. Git para mudanças;

3\. helpers existentes;

4\. `rg` direcionado;

5\. leitura de trechos relevantes;

6\. leitura de arquivo completo somente quando necessária;

7\. busca ampla apenas como último recurso.



Não releia arquivos já compreendidos sem motivo.



Não despeje logs enormes no contexto quando resumo + trecho relevante forem suficientes.



\## 13. Encerramento



O relatório final deve ser curto e verificável.



Informe:



\- causa ou objetivo;

\- o que mudou;

\- arquivos alterados;

\- testes realmente executados e resultados;

\- riscos ou pendências;

\- ações que exigem autorização do usuário.



Nunca diga que algo foi testado, validado, implantado ou está pronto para produção se isso não tiver sido efetivamente comprovado.

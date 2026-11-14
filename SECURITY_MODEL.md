# Modelo de ameaças — Barbearia Agendamento

## Escopo e origem das informações

Repositório: `imlucsz/barbearia-agendamento`, no GitHub; análise de segurança com esforço normal, conforme configuração enviada pelo usuário. Abrange o repositório completo e a infraestrutura Render versionada nele. Não inclui testes contra serviços publicados nem alteração de dados.

**Informações da documentação do projeto:** uma barbearia por instalação, com banco e configuração próprios; ausência de multi-tenancy (`AGENTS.md`, `README.md`). A documentação apresenta uma versão candidata em homologação e condiciona o uso de dados reais à validação operacional (`README.md`, `docs/CHECKLIST_PRODUCAO.md`). Isso descreve o estado documentado, não uma aceitação de vulnerabilidades; para esta análise prevalece o cenário público com dados reais confirmado abaixo.

**Respostas explícitas do usuário nesta sessão:** considerar acesso público e dados reais; proteger contas, dados pessoais e agenda; não excluir ameaças nem aceitar riscos. Organizar os achados por componente, CVE quando aplicável e categoria de dados pessoais. Essas respostas prevalecem sobre o estado de homologação descrito nos documentos.

**Inferências desta sessão:** os caminhos concretos e as pré-condições de ataque dependem da análise; clientes e barbeiros podem tentar exceder suas permissões. Essas inferências não autorizam alterar a severidade calculada pelo analisador.

## Sistema, componentes e limites de confiança

| Componente estável | Código e responsabilidade | Limite de confiança |
| --- | --- | --- |
| Interface web | `frontend/pages/`, `frontend/assets/`, `frontend/scripts/build-static.mjs`; páginas públicas, autenticação, reserva e gestão | Navegador e conteúdo externo não são fontes confiáveis para autorização. JWT de acesso fica em `localStorage` (`frontend/assets/js/api.js`). Há recursos externos de apresentação e mapa. |
| Identidade e sessões | `backend/app/routers/auth.py`, `backend/app/dependencies.py`, `backend/app/core/security.py`, controles de tentativas e recuperação de senha | Visitante → conta autenticada; cliente → barbeiro → administrador. O servidor consulta o usuário atual, estado e perfil. Recuperação cruza o limite com o provedor de e-mail. |
| Agenda e gestão | Demais módulos em `backend/app/routers/`, serviços de agendamento e schemas | Requisições públicas e autenticadas → operações de negócio. Clientes acessam recursos próprios; barbeiros têm atribuições próprias; administradores gerem a instalação. |
| Dados e privacidade | `backend/app/models/`, `backend/app/database.py`, `backend/alembic/`, exportação/anonimização em `backend/app/routers/users.py`, auditoria e manutenção | API → banco; dados privados → exportações ou registros de auditoria; retenção → anonimização. PostgreSQL na implantação e SQLite em desenvolvimento/testes. |
| Infraestrutura e operação | `render.yaml`, `backend/app/main.py`, `backend/app/frontend.py`, `backend/app/render_start.py`, `backend/app/config.py`, `.github/workflows/`, rotinas operacionais | Internet → borda Render → aplicação → PostgreSQL; operadores e CI → configuração, migrações, segredos e backups. |

Fluxo principal: navegador → API FastAPI → verificação de identidade e autorização → regras de agendamento → SQLAlchemy/banco. Recuperação de senha envia link ao endereço do titular por Brevo HTTPS ou SMTP STARTTLS (`backend/app/core/email.py`). Não foi identificado um worker separado nesse fluxo.

`render.yaml` habilita `SERVE_FRONTEND=true`, servindo páginas e assets pela API, e também mantém um Static Site separado. Ambos são superfícies possíveis; os domínios efetivamente usados e a exposição do Static Site não foram confirmados. Documentos antigos descrevem apenas a separação frontend/API. A infraestrutura foi lida no próprio repositório; nenhum repositório externo de infraestrutura foi utilizado.

## Entradas e exposição

- Internet sem autenticação: páginas/assets; cadastro, login e solicitação de recuperação; catálogo, informações institucionais, disponibilidade e avaliações públicas, conforme cada rota.
- Contas autenticadas: renovação e encerramento de sessão, histórico e operações sobre reservas, avaliações, exportação própria e anonimização; acesso condicionado ao titular, perfil e regras da API.
- Equipe: agenda, jornadas/bloqueios, serviços, clientes, moderação, relatórios financeiros/CSV e consulta de auditoria, conforme permissões de cada endpoint.
- Operação: `/health`, `/ready`; `/metrics` existe apenas quando há token configurado e exige Bearer válido. Documentação OpenAPI é desativada em produção (`backend/app/main.py`).
- Publicação e manutenção: build estático, inicialização com Alembic, criação interativa do primeiro administrador, retenção de auditoria e recuperação de backup. Não há endpoint de upload documentado; imagens de marca são fornecidas pelo operador.

## Ativos e sensibilidade

- Contas, hashes de senha, JWT, famílias de refresh, tokens de redefinição e segredos de implantação: proteção de identidade e privilégios.
- Nome, e-mail, IP, consentimento, histórico de atendimento, comentários e exportações: dados pessoais inventariados em `docs/LGPD.md`.
- Disponibilidade e integridade da agenda, jornadas, bloqueios, preços e registros financeiros: continuidade e correção do atendimento.
- Relatórios, auditoria, banco e backups: confidencialidade, rastreabilidade e recuperação. Não foi observado processamento de cartão; não presumir dados de cartão no sistema.

O usuário priorizou contas, dados pessoais e agenda, sem definir um ativo como excepcionalmente crítico acima dos demais. Manter a avaliação técnica do analisador quando essas prioridades já estiverem contempladas no impacto; não elevar automaticamente achados por envolverem esses ativos.

## Atacantes considerados

O usuário não excluiu nenhum perfil de atacante. Considerar visitante remoto sem conta; cliente autenticado tentando acessar ou alterar recursos de outro titular; barbeiro tentando exceder suas permissões; atacante com sessão roubada; comprometimento de recurso externo carregado pelo navegador. Acesso administrativo, de operador ou de provedor é um privilégio distinto e deve aparecer como pré-condição quando necessário; seu comprometimento não é presumido gratuito.

O isolamento entre instalações decorre de implantações separadas. Não se exige isolamento de tenants inexistentes dentro do mesmo banco, mas continuam relevantes os limites entre usuários, perfis e bancos de instalações distintas.

## Controles observados e dependências operacionais

Leitura estática confirmou: autorização por perfil e titular; consulta ao estado ativo/bloqueado da conta; JWT com algoritmo/validade verificados; Argon2 e compatibilidade bcrypt; refresh em cookie `HttpOnly`, `SameSite=Lax`, `Secure` em produção, armazenado como hash, com rotação/revogação; validação de origem nos fluxos de cookie; recuperação com token no fragmento e controle de uso/expiração; controles de tentativas e limites de concorrência; CORS e hosts configurados; respostas de validação sanitizadas; auditoria; exportação própria e anonimização documentadas.

Cabeçalhos da API e das páginas seguem políticas diferentes; a CSP das páginas permite mais recursos e precisa ser considerada separadamente. O backend pode servir somente diretórios públicos definidos em `backend/app/frontend.py`. HTTPS termina na borda Render, e o uso de `CF-Connecting-IP` depende da garantia do provedor de sobrescrever esse header. Migrações são executadas pelo launcher antes do servidor; backups e restauração dependem da operação descrita em `docs/PLANO_RECUPERACAO_DESASTRES.md`.

`SECURITY-REVIEW.md` é uma revisão estática anterior, usada como contexto, sem tomar suas conclusões como validação do código atual. Configurações publicadas, cadeia de proxy, entrega de e-mail e execução real dos backups não foram verificadas. Nenhuma suíte de testes, auditoria dinâmica ou banco real foi executado nesta sessão.

## Riscos aceitos, exclusões e regra de priorização

O usuário confirmou explicitamente que nenhum risco é aceito e nenhuma ameaça deve ser excluída. A natureza acadêmica e o estado de homologação não implicam que vazamento, acesso indevido ou perda de agenda sejam aceitáveis. Não alterar código, executar operações em produção nem abrir correções sem pedido específico.

Cada achado parte da severidade do analisador, que já pesa probabilidade, pré-condições e impacto. Somente fatos fornecidos pelo usuário ou pela documentação do próprio projeto justificam mudança; inferências desta sessão não justificam. Não elevar ataques difíceis ou não verificados. Quando o modelo não mudar essas condições, preservar a severidade e explicar que a avaliação técnica permanece válida.

## Questões em aberto e etiquetas

As perguntas de exposição, prioridades, exclusões e etiquetas foram respondidas: acesso público, dados reais, proteção de contas/dados pessoais/agenda, sem exclusões ou riscos aceitos.

Etiquetas aprovadas: `Component`, com o nome estável da tabela; `CVE`, com identificador confirmado quando houver; `Categoria de dados pessoais`, com a categoria efetivamente exposta ou afetada (por exemplo, identificação e contato, credenciais e sessão, histórico de atendimento, consentimento ou metadados de segurança). Sem presumir classificação formal de conformidade nem equipes não informadas.

Permanecem desconhecidos: domínios e serviços Render efetivamente publicados, configuração operacional de proxy/e-mail, política concreta de backup/restauração e retenção legal da instalação. Essas lacunas são registradas sem presumir mitigação ou vulnerabilidade.

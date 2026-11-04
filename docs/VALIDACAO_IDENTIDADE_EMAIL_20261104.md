# Identidade de e-mail — Lote 2 — 2026-11-04

Escopo: caracterizar a política existente com testes, sem corrigir funcionalidades. Nenhum arquivo de runtime, índice, revisão Alembic, dependência ou frontend foi alterado neste lote. Trabalho local anterior, incluindo Lote 1 e recuperação/sessões, preservado. Não houve acesso a bancos reais, envio real de e-mails, commit, push ou deploy.

## Contrato e arquivos inspecionados

| Camada / arquivo | Comportamento observado |
| --- | --- |
| `backend/app/schemas/user.py` | `NormalizedEmail`: `strip().lower()` antes de `EmailStr`, máximo 254. Cadastro, login, atualização administrativa e recuperação usam o mesmo tipo. EmailStr normaliza NFD para NFC e domínio IDNA para Unicode. |
| `backend/app/core/email_identity.py` | Helper Python aplica strip/lower, sem NFC, casefold ou regras de provedor. Chave SQL: `lower(ltrim(rtrim(email)))`. Reconhece somente conflitos de unicidade de e-mail conhecidos. |
| `backend/app/models/user.py` | Atribuição ORM aplica apenas o helper; coluna tem índice único simples e índice funcional único `uq_users_email_identity`. |
| `backend/alembic/versions/20261031_01_email_identity.py` | Revisão existente cria/verifica a chave funcional e trata colisões antes de normalizar dados. Inspecionada/testada exclusivamente em estruturas descartáveis; não editada. |
| `backend/app/routers/auth.py` | Cadastro duplicado detectado antes do INSERT: HTTP 400. Colisão no flush: rollback e HTTP 409 com mensagem controlada. Login e recuperação consultam a chave SQL. Recuperação retorna resposta pública genérica e preserva cooldown. |
| `backend/app/routers/users.py` | Único fluxo de edição de e-mail inspecionado é PUT administrativo de clientes. Pré-consulta e conflito no commit retornam 409; omissão não regrava e-mail. Não foi criado fluxo de edição de perfil. |
| `backend/app/core/email.py` | SMTP chama `SMTP.send_message`; Brevo envia o destinatário em JSON UTF-8. Aceitação pelo schema não verifica caixa postal ou garante entrega. |

Aliases `+tag`, pontos e `straße`/`strasse` continuam identidades distintas. Não se adotou casefold, remoção de aliases, transliteração ou regra específica de Gmail. Senhas continuam com o comportamento anterior, inclusive trim global; nada neste lote altera hashes, JWT, cookies, sessões ou recuperação.

## Testes adicionados

- `backend/tests/test_email_identity_contract.py`: equivalência nos quatro schemas, caixa/espaços/NFC/NFD/IDNA, entradas inválidas, cadastro duplicado, login, recuperação genérica/cooldown, destinatário e identidade associados, aliases distintos, edição administrativa válida e conflitante, omissão/null e preservação de hash. Inclui caracterização explícita de conta legada NFD criada diretamente pelo ORM.
- `backend/tests/test_email_identity_postgres.py`: metadados reais, índice funcional, erro 23505 e reconhecimento da constraint, duas requisições HTTP concorrentes com conexões distintas, limites Unicode da collation C e diferença entre trim SQL e Python. A barreira sincroniza as pré-consultas; SELECT, INSERT, hashing, flush, commit, constraint e resposta HTTP permanecem reais.
- `backend/tests/test_email_identity_delivery.py`: serialização/negociação do `SMTP.send_message` real com envio/socket substituídos, servidor com/sem SMTPUTF8 e payload Unicode do Brevo com respostas simuladas. Nenhuma chamada de rede ou entrega é realizada.

Casos que reproduzem lacunas são **testes de caracterização**, não uma aprovação do comportamento como desejável. Não foram implementadas correções para fazê-los passar.

## PostgreSQL real descartável

Executado pelo launcher existente `tools/test-recovery-postgres.py`, que inicia cluster novo, gera credencial temporária, usa somente loopback e banco `*_test`, desabilita dotenv, encerra e remove o cluster ao final. Nenhuma URL de banco ou credencial consta no relatório.

- PostgreSQL **18.6** (`server_version=180006`), `server_encoding=UTF8`, `client_encoding=UTF8`, psycopg `info.encoding=utf-8`, `datcollate=C`, `datctype=C`.
- Índice funcional inspecionado no catálogo: único, com `lower(ltrim(rtrim((email)::text)))`. O cast para text é a representação do PostgreSQL para a coluna VARCHAR.
- Duas disputas reais de cadastro: equivalência ASCII/caixa/espaços e equivalência Unicode NFC/NFD. Em cada disputa, as duas pré-consultas ocorreram antes de qualquer INSERT; dois backend_pid distintos; resultados **201 e 409**, exatamente uma conta e mensagem de conflito sem detalhes internos.
- Violação direta da chave funcional produz SQLSTATE **23505**, tabela users e constraint `uq_users_email_identity`, reconhecidos pelo helper atual.
- O teste existente da revisão Alembic também executa em schema separado do banco descartável, verificando recusa de índice incompatível e aceitação da definição correta. Não há revisão nova neste lote.

Esses resultados não comprovam a versão, collation, índices ou integridade do PostgreSQL implantado. Nenhuma conexão de homologação/produção foi aberta.

## Lacunas confirmadas e propostas separadas

| Achado reproduzido apenas com fixtures | Impacto / proposta que exige nova aprovação |
| --- | --- |
| ORM aceita e preserva NFD, mas schema converte para NFC. Conta legada NFD da fixture não é localizada no login nem na recuperação, embora a resposta pública continue genérica. | Risco para importações/gravações fora dos schemas e eventuais dados legados. Primeiro fazer diagnóstico autorizado somente leitura com contagens/flags; depois propor canonicalização central e estratégia de colisões/compatibilidade. Não concluir que existem contas assim no ambiente real. |
| Na collation C, índice admite três linhas diretas: local-part com é minúsculo, É maiúsculo e e + acento combinante. | O índice não representa toda a equivalência do pipeline Python/EmailStr. Os fluxos HTTP testados normalizam esses casos e a corrida deles é contida; não há garantia universal para gravações alternativas/collations. Avaliar chave canônica persistida/índice correspondente em plano próprio, com análise de colisões e migração segura. |
| SQL ltrim/rtrim não remove U+00A0; Python strip remove. Duas representações coexistem quando inseridas diretamente por SQL. | Leituras/unicidade de possíveis registros legados podem divergir. Não alterar trim global nem reparar dados automaticamente. |
| Cadastro usa 400 no pré-check e 409 na corrida. Ambos têm erro controlado; atualização usa 409. | Contrato inconsistente, preservado. Uniformização de status/mensagem deve ser proposta e testada com clientes antes de alterar. Cadastro já informa duplicidade; a garantia anti-enumeração testada pertence à recuperação, não a todo endpoint de autenticação. |

## Endereços internacionalizados: limites separados

1. **Validação:** schemas aceitam as fixtures Unicode/IDNA testadas e rejeitam formatos inválidos. Isso é validação sintática/normalização, não prova de DNS ou existência da caixa.
2. **Armazenamento:** novos cadastros e atualizações via schema persistem a representação normalizada; ORM/SQL direto podem divergir conforme os achados acima.
3. **Autenticação/recuperação:** fixtures criadas pelo fluxo público normalizado fazem login e são localizadas para recuperação, inclusive IDN e local-part Unicode. Compatibilidade com todas as contas antigas permanece não comprovada.
4. **Entrega:** no caminho SMTP atual, tanto local-part Unicode quanto domínio IDN convertido para Unicode exigiram SMTPUTF8 no envelope. Sem essa extensão, stdlib rejeita antes de sendmail e a aplicação traduz para EmailDeliveryError genérico. Com extensão simulada, usa SMTPUTF8 e BODY=8BITMIME. Converter só domínio para A-label poderia mudar esse requisito para alguns endereços, mas não foi implementado. No Brevo, payload preserva Unicode; HTTP 201 simulado demonstra apenas o tratamento da aceitação, não suporte efetivo do provedor ou entrega final. Verificação operacional futura deve usar ambiente/provedor de teste autorizado, nunca inferir entrega a partir de EmailStr.

## Comandos, resultados e limites

Executados a partir da raiz, salvo indicação de `backend`:

```powershell
# Em backend: SQLite temporário, foco
rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_email_identity*.py -q
# Na raiz: PostgreSQL novo e descartável, foco
rtk proxy backend\.venv\Scripts\python.exe tools/test-recovery-postgres.py discover -s tests -p test_email_identity*.py -q
# Em backend: regressões SQLite
rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -q
# Na raiz: regressões Node e higiene
rtk proxy node --test frontend/tests/*.test.mjs
rtk proxy git diff --check
rtk proxy graphify update .
```

| Execução | Resultado efetivamente observado |
| --- | --- |
| Foco SQLite final | 23 executados em 8,893 s; 17 aprovados, 6 ignorados exclusivos de PostgreSQL, zero falhas. |
| Foco PostgreSQL final | 23 executados em 10,956 s; 23 aprovados, zero falhas/ignorados. Cluster encerrado e removido. |
| Suíte completa SQLite | 318 executados em 239,576 s; 305 aprovados, 13 ignorados exclusivos de PostgreSQL, zero falhas. Inclui regressões de Argon2/bcrypt legado, login, reset/uso único/expiração, JWT, sessões, autorização, nomes Lote 1 e migrações somente descartáveis. |
| Node existente | 35 aprovados, zero falhas/ignorados. Nenhum frontend editado neste lote. |

A suíte completa já estava em execução quando foi adicionado o último método de reforço da recuperação. Ela coletou 318 métodos antes dessa adição; **o método adicional foi executado nos focos finais SQLite e PostgreSQL acima**, não se declara uma suíte completa de 319 nesta etapa. A revisão independente encontrou essa lacuna de cobertura e confirmou sua resolução após reler o reforço. Nenhum código funcional foi alterado entre essas execuções. Suíte completa PostgreSQL e Playwright não executados neste lote.

`git diff --check`: código 0; aviso LF/CRLF em arquivo preexistente, sem erro de whitespace. Os seis arquivos deste lote também foram lidos como UTF-8 estrito e verificados contra whitespace no fim das linhas, inclusive os novos não rastreados: zero erros. `graphify update .`: código 0, AST local sem LLM, 11603 nós/23843 arestas; artefatos derivados atualizados. Status/diff revisados, sem edição de runtime neste lote.

Execuções preliminares: o sandbox impediu abertura/limpeza do SQLite temporário; repetido com autorização fora dele. Dois testes novos inicialmente liam argumento SMTP posicional como keyword; corrigidos somente os testes. Primeira execução PostgreSQL teve uma falha de asserção por não considerar o cast `::text`; corrigida somente a asserção e repetida, 22/22 aprovados. Não foram ocultadas falhas funcionais nem alterado runtime. Warning existente de reflexão de índice de expressão no SQLite não foi tratado como comprovação da definição PostgreSQL: esta foi consultada/testada no servidor real descartável.

## Próximos passos propostos, sem implementação

1. Aprovar diagnóstico somente leitura no alvo confirmado para versão/collation/índices e contagens de discrepâncias, sem exportar pessoas, tokens ou credenciais.
2. Se necessário, aprovar plano específico de identidade canônica, colisões e compatibilidade legada. Testar C e a collation efetiva do ambiente; nenhuma atualização automática ou migração real antecipada.
3. Aprovar separadamente a política de entrega internacionalizada e testes de integração em serviço de e-mail de teste. Manter respostas genéricas na recuperação.

Lotes 3/4, normalização de credenciais, correções funcionais, dependências, infraestrutura e publicação continuam fora da autorização.

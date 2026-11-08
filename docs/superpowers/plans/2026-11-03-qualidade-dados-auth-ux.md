# Ampliação proposta — qualidade dos dados e UX de autenticação

Estado atual: diagnóstico da Etapa 1 registrado com inspeção SQL real ainda pendente; Lote 1 da Etapa 2 autorizado e implementado localmente em 2026-11-04, conforme evidências ao final. Lote 2 e seguintes aguardam autorização explícita. Sem dependências novas, migração de ambiente real, correção automática de registros ou alteração da política de hashes. Este plano é separado da [auditoria de segurança](../../AUDITORIA_SUPERFICIE_API_20261103.md) e da [correção de recuperação/barbeiros](2026-11-03-recuperacao-e-barbeiros.md).

## Prioridade e limites

1. Não atrasar correções críticas de sessão, recuperação, revogação, autorização e abuso já identificadas.
2. Diagnóstico de codificação e validações de escrita podem avançar como trabalho independente após aprovação.
3. Visibilidade e medidor entram como UX localizada; não reescrever formulários, autenticação, armazenamento de sessão ou arquitetura.
4. Nenhum dado real será corrigido automaticamente. Não reaplicar migrações históricas para “corrigir acentos”: a revisão de identidade de e-mail existente altera dados e não faz parte desta proposta.

## Diagnóstico confirmado no código/local

| Área | Evidência | Consequência |
| --- | --- | --- |
| Terminal/Unicode | Simulação Python: `hidratação`.encode('cp1252').decode('cp850') produz exatamente `hidrataþÒo` | Forte hipótese de Windows-1252 interpretado como CP850. Não demonstra que os registros reais estejam íntegros. O erro pode ocorrer na saída ou ter sido gravado anteriormente. |
| Ambiente de inspeção | Subprocesso Windows PowerShell 5.1: Console.OutputEncoding 65001, OutputEncoding 20127 | Há configurações diferentes no pipeline; não é prova da configuração do terminal usado pelo usuário no incidente. Nenhuma configuração foi alterada. |
| Fonte frontend | `reset.html` decodifica estritamente como UTF-8; rótulo RECUPERAÇÃO tem os codepoints corretos; sem U+FFFD no arquivo inspecionado | A saída textual do PowerShell pode parecer corrompida mesmo quando o arquivo está correto. Não foram verificados todos os arquivos nem os headers do site publicado nesta etapa. |
| SQLAlchemy | `backend/app/database.py:15`: opções específicas somente para SQLite; PostgreSQL usa psycopg, sem client_encoding fixado no código | Encoding real é propriedade da conexão negociada; não inferir UTF-8 só pela linguagem Python ou pelo modelo String. |
| Nomes | `schemas/user.py`: StrictStr, 1–120; base usa str_strip_whitespace e rejeita Unicode Cc | Acentos, hífen, apóstrofo e outras escritas não são proibidos; vazio/espaços, controles e excesso de comprimento já têm proteção. |
| Lacunas de nomes | Sem NFC e sem colapso de espaços internos | “José” e “Jose + acento combinante” permanecem representações diferentes; “José  da Silva” conserva espaço duplo. Não é motivo para renomear registros existentes. |
| E-mail | EmailStr + BeforeValidator, normalize_email strip/lower; consultas e índice lower(ltrim(rtrim(email))); model valida escrita | Política adotada é identidade inteira sem distinção de caixa, sem remover pontos ou aliases +tag. Não trocar por casefold/regra Gmail silenciosamente. |
| Senhas | SchemaModel global também aplica strip às senhas | Verificado com string fictícia: espaços externos são removidos. Não alterar a base global para implementar normalização de nomes, nem corrigir esse comportamento como efeito colateral: exigiria plano de compatibilidade da autenticação. |
| Renderização | Home e área cliente usam textContent; admin usa templates com escapeHtml nos nomes/e-mails/serviços inspecionados | Não foi demonstrado XSS nesses pontos. Novos conteúdos variáveis devem usar nós/textContent; não confundir normalização de texto com sanitização HTML. |
| Formulários | Login, cadastro, reset e senha atual de exclusão usam type=password; sem botão de visibilidade/medidor | Mudança localizada possível com ES Modules e SVG inline. Não há confirmação de nova senha nem alteração de senha no perfil no fluxo inspecionado; não criar esses fluxos sem novo escopo. |

Não foram lidos registros reais, settings de sessão SQLAlchemy em produção, server_encoding ou client_encoding do PostgreSQL hospedado. Render MCP continua sem workspace confirmado; portanto esses valores e a integridade dos registros reais permanecem pendentes. A confirmação de workspace solicitada anteriormente continua necessária para inspeção remota pelo conector.

## Verificações de codificação propostas, somente leitura

Usar conexão explicitamente identificada e autorizada, sem copiar URL/segredos para comandos ou logs. Não executar app.render_start, lifespan, seed ou Alembic. Preferir um serviço de consulta com papel somente leitura. Primeiro conferir metadados da sessão de psql e depois da sessão real da aplicação: são clientes distintos e podem ter encodings diferentes.

```sql
BEGIN READ ONLY;
SHOW server_encoding;
SHOW client_encoding;
SELECT current_setting('client_encoding') AS client_encoding,
       current_setting('server_encoding') AS server_encoding;

-- Literal Unicode independente da codificação do texto digitado no terminal.
SELECT encode(convert_to(U&'hidrata\00E7\00E3o', 'UTF8'), 'hex') AS referencia_utf8;

-- Consulta parametrizada de UM serviço previamente identificado; não varrer pessoas.
SELECT id, char_length(nome) AS caracteres, octet_length(nome) AS bytes_servidor,
       encode(convert_to(nome, 'UTF8'), 'hex') AS valor_em_utf8
FROM services WHERE id = :service_id;
ROLLBACK;
```

`:service_id` é placeholder SQLAlchemy; em psql usar parâmetro/variável tipado, não colar esse placeholder como SQL executável. Hex de texto real também revela seu conteúdo: não publicar nomes/hex de pessoas em relatório ou telemetria. `convert_to(...,'UTF8')` mostra a representação UTF-8 do valor lógico, não bytes físicos da página do banco. Referência esperada para `hidratação`: `68696472617461c3a7c3a36f`.

Na conexão SQLAlchemy, executar a mesma consulta em transação READ ONLY e consultar `connection.connection.driver_connection.info.encoding` (psycopg), emitindo somente metadados de encoding. Não logar engine.url, DSN ou repr da conexão. Conferir também `psql \encoding`, PGCLIENTENCODING, página de código e codificações de entrada/saída do PowerShell sem mudá-las durante o diagnóstico.

Interpretação:
- Hex/codepoints do valor SQL corretos, exibição incorreta apenas em psql/PowerShell: corrigir configuração de exibição/pipeline, não os registros.
- Valor SQL já contém U+00FE/U+00D2 onde deveria haver U+00E7/U+00E3: dado lógico diferente do esperado; investigar origem de gravação. UTF-8 válido pode conter mojibake, portanto UTF-8 por si só não comprova qualidade.
- SQLAlchemy entrega codepoints corretos, API entrega outros: investigar serialização/transformação.
- Resposta JSON decodificada correta, DOM incorreto: inspecionar JS, HTML charset, headers e eventuais conversões; fonte visual é hipótese adicional. Usar dados fictícios para rastrear ponta a ponta.
- Não substituir automaticamente sequências suspeitas: þ/Ò podem ser legítimos em outros nomes/idiomas. Qualquer reparo de registro exige diagnóstico individual e aprovação específica.

Referências: [PostgreSQL — character sets](https://www.postgresql.org/docs/current/multibyte.html), [psycopg — adaptação de strings](https://www.psycopg.org/psycopg3/docs/basic/adapt.html#strings-adaptation).

## Proposta de implementação por área

### Nomes e textos

Criar um tipo/validador de nome para **entrada de criação e atualização**, sem normalizar automaticamente saída de UserResponse ou dados já persistidos. Ordem: rejeitar controles antes de colapsar whitespace; validar string Unicode; NFC; trim e colapso de espaços internos apropriados; validar 1–120 no resultado, com limite de entrada para evitar trabalho excessivo. Rejeitar também strings Unicode inválidas/surrogates e nomes visualmente vazios, sem blacklist geral de caracteres de formato legítimos. Detalhar casos de joiners/bidi em testes: não rejeitar toda categoria Cf indistintamente e prejudicar escritas legítimas.

Preservar acentos, caixa, hífens e apóstrofos retos/curvos. Não usar NFKC indiscriminadamente, transliteração, remoção de acentos, regex ASCII, exigência de duas palavras ou Title Case. Aceitar monônimos e nomes de outras escritas. NFC não repara mojibake. Não exigir unicidade de nome.

Aplicar a normalização somente ao campo efetivamente fornecido no update; omissão deve manter o valor antigo e null continua inválido. Não modificar SchemaModel global nem a interpretação de senhas/tokens como atalho. Nomes/serviços exibidos usarão textContent/createElement nos pontos tocados; templates antigos fora do escopo conservam escapeHtml e seus testes, sem reescrita de telas.

### E-mails

Manter EmailStr/email-validator no backend e a política existente strip/lower para cadastro, login, atualização administrativa e recuperação. Preservar aliases, pontos e domínio sem regras de provedor. Não adicionar normalização de e-mail ao JavaScript como fonte de verdade. O frontend só apresenta erro útil sem ecoar conteúdo sensível.

Verificar em PostgreSQL descartável o índice funcional e sua collation com os casos Unicode aceitos. Python lower, normalização Unicode do email-validator e PostgreSQL lower/trim não são equivalentes universais; testar representação decomposta/composta, domínio IDN e bordas de whitespace. Normalização de domínio não garante suporte de entrega de local-part internacionalizado (SMTPUTF8): testar transporte mockado/provedor em ambiente de teste antes de anunciar suporte completo.

Não alterar índices/revisões históricas nem normalizar registros existentes em massa. Se a verificação mostrar colisão ou necessidade de outra chave canônica, entregar diagnóstico separado antes de propor migração. Atualização de nome não deve regravar o e-mail. Não criar endpoint de autoedição de perfil: hoje UserUpdate atende gestão administrativa de clientes; a página de conta inspecionada exibe informações/exporta/exclui, não altera senha.

### Mostrar/ocultar senha

Adicionar módulo ES reutilizável para login, cadastro, reset e senha atual de exclusão. Campos de confirmação/alteração só recebem controle se vierem a existir em escopo aprovado. Botão type=button com SVG inline de olho aberto/fechado, SVG aria-hidden; aria-controls aponta para input; aria-label muda entre “Mostrar senha” e “Ocultar senha”.

Alternar somente input.type, preservando valor, id/name, autocomplete e conteúdo digitado, sem substituir nó ou enviar formulário. Tab/Enter/Espaço devem funcionar; foco visível e área de toque adequada, sem roubar foco ou quebrar navegação do diálogo. Estado inicial oculto; diálogo de exclusão volta ao estado oculto ao fechar/limpar. Não desabilitar colagem, autofill ou gerenciadores de senha.

### Medidor de força

Recomendo `@zxcvbn-ts/core` com pacotes common/en/pt-br, versões fixadas e assets hospedados no próprio site; **sem instalar nesta fase**. O projeto atual não tem bundler de aplicação (build-static copia arquivos), portanto bare imports npm não funcionariam diretamente no navegador. A implementação deve gerar um pequeno bundle ES compatível, com ferramenta de build fixa e justificada se necessária, sem mudar a stack Vanilla.

Custo: biblioteca/dicionários aumentam download, tempo de parsing e superfície de dependências; medir tamanho bruto/gzip e latência em mobile antes de fechar o orçamento. Carregar somente nos fluxos de criação/reset e, preferencialmente, por demanda. Conferir licença, dependências transitivas, advisories e atualização de versões; não usar CDN runtime nem matcher de API externa. Não substituir por pontuação caseira de quantidade de símbolos. Alternativa: bundle clássico zxcvbn local, integração menor porém dicionários menos modulares; confirmar suporte linguístico e peso antes de escolher.

Exibir escore 0–4 como estimativa, mapeando 0–1 para fraca/vermelho, 2–3 para moderada/amarelo e 4 para forte/verde. Sempre mostrar texto e sugestões em português, sem prometer inviolabilidade ou prazos de quebra. Usar elemento meter/semântica equivalente com descrição textual; aria-live=polite apenas quando categoria/feedback muda, com debounce para evitar ruído e trabalho por tecla. Não inserir senha ou trechos dela nas mensagens de feedback, atributos, logs ou resultado serializado.

Usar tokens existentes de installation.css para danger/warning/success, contraste e dark mode. Não aplicar medidor ao login ou à senha atual de exclusão. Enquanto carrega ou se falhar, exibir estado honesto (“Indicador indisponível”), sem assumir senha forte nem impedir autenticação existente.

O indicador é orientativo: a validação obrigatória permanece no backend. O contrato atual exige 6–128 caracteres em cadastro/reset; não será enfraquecido nem elevado silenciosamente por esta melhoria de UX. Mínimo de 6 é uma pendência de política de segurança: aumento de comprimento e eventual rejeição de senhas comuns devem ser aprovados como política para novas senhas, sem bloquear login legado ou reprocessar hashes. Nenhuma mudança automática na política baseada só no escore do browser.

Referências: [zxcvbn-ts — padrões detectados](https://zxcvbn-ts.github.io/zxcvbn/guide/), [pacotes e idiomas](https://zxcvbn-ts.github.io/zxcvbn/guide/languages/), [lazy loading](https://zxcvbn-ts.github.io/zxcvbn/guide/lazy-loading/), [EmailStr](https://docs.pydantic.dev/latest/api/networks/#pydantic.networks.EmailStr).

## Arquivos envolvidos, sem alterações de produto nesta etapa

| Área | Arquivos a tocar/verificar após aprovação |
| --- | --- |
| Validação | backend/app/schemas/user.py; novo helper de nome restrito a entradas; schemas/base.py apenas para avaliar isolamento/compatibilidade |
| Identidade | backend/app/core/email_identity.py, models/user.py, routers/auth.py, routers/users.py; manter contratos/índice existentes salvo achado específico |
| Encoding | backend/app/database.py; nova ferramenta de diagnóstico somente leitura, sem importar launcher, secrets no output ou correção de dados |
| Formulários | frontend/pages/login.html, cadastro.html, reset.html, client-account.html |
| JS | novo módulo de campos de senha e estimador; frontend/assets/js/auth.js e schedule.js apenas integração pontual |
| XSS | home.js, schedule.js, admin_management.js e escape-html.mjs nos pontos de texto efetivamente envolvidos |
| Estilo/build | frontend/assets/css/installation.css e style.css; package.json/lock; frontend/scripts/build-static.mjs e bundle local, se aprovado o estimador |
| Testes | backend/tests/test_schema_validation.py, test_authentication_regression.py, test_email_identity_migration.py, test_email_integrity_errors.py, test_password_reset.py; novos testes de normalização e Node para password fields/strength; Playwright essential-flows.spec.mjs |
| Documentação | README/REQUISITOS_STATUS somente na implementação; este plano registra diagnóstico e decisões pendentes |

## Testes e critérios de aceitação

- Nomes: José, João, Ana-Maria, D'Ávila, O’Connor, monônimo, 李 明, exemplos árabes/indianos com caracteres legítimos, NFC/decomposto e espaços repetidos/NBSP. Vazio/whitespace-only, controles NUL/tab/newline, surrogates, comprimento bruto excessivo e bordas 120/121. Sem perda de acentos/caixa, idempotência, sem alterar dados omitidos em update.
- E-mails: espaços externos, caixa, +tag/pontos preservados; múltiplos @, espaços internos, controles, domínio inválido, limites, Unicode/IDN e canonização. Cadastro concorrente em PostgreSQL real descartável: no máximo uma identidade conforme política; nenhuma consulta/erro revela senha/hash. Não usar mocks como prova de unicidade do banco.
- Autenticação: cadastrar/login com e-mail normalizado, atualizar nome sem mudar e-mail/hash, credenciais/contas legadas continuam válidas; verificar explicitamente tratamento atual de espaços em senha antes de qualquer política futura. Recuperação mantém resposta genérica, cooldown e concorrência; reset mantém expiração/uso único e preservação de tokens anteriores em falha.
- XSS: payloads fictícios em nomes/serviços/comentários nunca executam eventos/scripts no DOM. Texto seguro deve ser exibido como texto ou rejeitado pela validação com regra justificada, sem depender de blacklist HTML no backend. Conferir todas as interpolacões novas e preservar cobertura de escapeHtml antiga.
- Visibilidade: cada campo existente, valor/caret/autocomplete preservados, mouse/Tab/Enter/Espaço, labels dinâmicos, foco e diálogo, sem submit/requisição extra. Snapshot/log/trace de testes não deve carregar senhas reais; somente fixtures. Sem medidor em login/confirmação de senha atual.
- Estimador: senhas comuns longas, sequências, datas, repetições, padrões de teclado, passphrases e Unicode; mensagens determinísticas para corpus fictício e versão fixada, sem testar apenas “tem símbolo”. Medidor/texto/cor/ARIA concordam; loading/falha/offline não bloqueiam regra backend. Nenhuma senha ou resultado bruto sai para fetch/telemetria, console, storage ou atributos DOM.
- Mobile/dark mode/zoom, contraste, área de toque, ausência de overflow, leitor de tela e navegação por teclado. Medir bundle e processamento; usar worker apenas se a medição justificar, sem introdução automática de arquitetura nova.
- Verificar mínimo/tamanho/campos no servidor enviando requisições sem JS; o medidor não decide autorização. Testes Python/Node focados, regressão auth/recuperação e Playwright desktop/mobile; suites PostgreSQL somente em banco descartável explicitamente configurado. Sem banco real, migração remota ou e-mail real.

## Evidências efetivamente executadas agora

- Leitura dirigida de código/Graphify, requisitos, templates, build e tokens de UI.
- Simulação de encoding reproduziu exatamente `hidrata\u00fe\u00d2o`; nenhum registro do banco foi usado.
- Verificação estrita UTF-8 do reset.html confirmou rótulo correto e ausência de replacement character no arquivo selecionado.
- Validação em memória com schemas existentes: nomes com acentos, CJK e decomposição aceitos; vazio/controle rejeitados; espaço interno duplo e NFD preservados. Confirmado strip externo da senha fictícia, sem exibir seu conteúdo.
- EmailStr em memória: caixa/trim/+tag normalizados, malformados rejeitados, Unicode decomposto normalizado e domínio IDN aceito pelo validador. Isso não comprova entrega SMTPUTF8 nem collation/índice do PostgreSQL hospedado.
- Sem suítes novas, consultas de banco, instalação ou implementação. Os scripts pontuais só importaram schemas/helpers sem abrir app/database/lifespan. Git diff --check será usado no fechamento deste artefato.

## Aprovação e riscos de compatibilidade

Aprovação solicitada para diagnóstico de conexão somente leitura no alvo confirmado, normalização de nomes somente em futuras escritas, regressões de e-mail sem migração e UX de senha/estimador self-hosted com custo de build medido. Nenhum novo endpoint, confirmação de senha ou alteração de senha de perfil será criado por inferência.

Riscos principais: NFC/espaços alteram representação de novas entradas; nomes válidos não devem ser bloqueados por categorias Unicode abrangentes; e-mails Unicode dependem de collation/transporte; mudança global de strip afetaria credenciais; peso/atualizações do estimador precisam de orçamento; mudanças de política de senha e colisões legadas precisam de aprovação específica. Nenhum hash ou dado existente será reescrito para realizar esta melhoria.

Próximas etapas após aprovação: (1) confirmar encoding real e testes RED com fixtures; (2) nomes/e-mail com GREEN preservando contratos; (3) visibilidade; (4) estimador e medição; (5) regressões/revisão/Graphify/documentação. Manter commits/deploy e migração remota fora da autorização.

## Etapa 1 executada — evidências e limites

Autorização aplicada estritamente ao diagnóstico. O único arquivo editado nesta etapa é este plano. Não foram executados suites que criam/limpam bancos, migrations, app.render_start, seeds, login, cadastro, recuperação ou redefinição reais. Não houve hash de senha calculado/modificado, instalação, build que gere dist, commit ou push.

### Cadeia de codificação

| Camada | Evidência efetivamente obtida | Resultado / limite |
| --- | --- | --- |
| Reprodução sintética | Python, strings fictícias e saída JSON com ensure_ascii=True | Windows-1252 interpretado como CP850 reproduz exatamente `hidrata\u00fe\u00d2o`. Referência UTF-8 correta: `68696472617461c3a7c3a36f`. |
| Terminal desta inspeção | Windows PowerShell 5.1: InputEncoding 850, Console.OutputEncoding 65001, OutputEncoding 20127 | Configurações diferentes corroboram risco na cadeia de entrada/saída/pipeline. Não modificadas e não equivalem necessariamente ao terminal do incidente. |
| Arquivos locais | Leitura binária e decode UTF-8 estrito de login.html, cadastro.html, reset.html e client-account.html | Quatro arquivos válidos, com declaração UTF-8, sem U+FFFD. Não é uma varredura de todo o repositório. |
| API publicada | GET público `https://barbearia-homolog-api.onrender.com/services/`; decode UTF-8 estrito e análise em memória | HTTP 200, application/json, 11 serviços; todos os nomes em NFC; uma ocorrência correta de hidratação, zero do padrão relatado. Emitidas somente contagens/flags, sem nomes ou IDs de registros. |
| Frontend publicado | Playwright, contexto isolado anônimo, GET da página `https://barbearia-homolog-frontend.onrender.com/pages/index.html`, leitura dos títulos em memória | HTTP 200, document.characterSet UTF-8; 11 títulos no DOM; uma ocorrência correta, zero do padrão relatado e nenhum U+FFFD. Sem screenshot, dump de conteúdo, credenciais ou interação de formulário. Contexto fechado. |
| SQLAlchemy local | Inspeção de database.py e psycopg declarado nas dependências | Sem override PostgreSQL de client_encoding no código; negociar encoding não é prova do valor real de sessão. Não aberta conexão ao banco local ou hospedado. |
| PostgreSQL hospedado | Render MCP get_selected_workspace | Sem workspace selecionado. Não consultados server_encoding, client_encoding, collation, índice ou valor lógico do registro. Não presumir acesso confirmado nem buscar DSN em .env como contorno. |

Conclusão: **API e DOM publicados estão corretos para o serviço correspondente ao exemplo**, e o padrão visual foi reproduzido por incompatibilidade de code pages. A causa mais provável do sintoma é exibição/pipeline no terminal. Não é possível concluir que todo o banco está íntegro nem identificar a etapa exata do terminal sem a consulta SQL e as configurações do cliente usado no incidente. Não há evidência atual que justifique qualquer UPDATE.

A primeira consulta HTTP foi bloqueada pelo DNS do sandbox. Foi repetida com permissão de rede fora do sandbox e retornou os resultados acima. Dois comandos de inspeção em memória precisaram de correção de escapes (NUL/aspas); as reexecuções corretas são as evidências registradas, sem efeito sobre código ou dados.

Para encerrar a pendência SQL, usar o procedimento READ ONLY já descrito: confirmar workspace/instância e serviço alvo, consultar somente metadados e um serviço conhecido, sem exportar pessoas ou connection strings. O client_encoding informado pelo conector de consulta pertence à sessão do conector; não deve ser apresentado como o da SQLAlchemy. A sessão real da aplicação exige consulta pela conexão correspondente, sem alterar o processo/publicar endpoint de debug. Se esse acesso não estiver disponível, a pendência deve permanecer explícita.

### Normalização — verificações em memória

Todos os testes pontuais importaram somente schemas/helpers, sem importar app.main, app.database, suporte de testes com reset_database ou abrir conexões. Dados fictícios; valores de senhas, tokens, hashes e nomes pessoais reais não foram emitidos.

| Casos | Confirmação |
| --- | --- |
| 11 cenários de nome | Acento NFC, NFD, CJK, apóstrofo, hífen, espaços internos e 120 caracteres aceitos; vazio/espaços, NUL e 121 caracteres rejeitados. NFD continua NFD; espaços internos duplos preservados; trim externo aplicado. |
| Nome visualmente vazio U+200B | Aceito atualmente. Lacuna confirmada, pois não pertence a Cc e não é removido pelo strip. Corrigir futuramente sem proibir todos os joiners/caracteres de formato de nomes legítimos. |
| UserUpdate | Campo omitido não entra em model_dump(exclude_unset=True); espaços internos permanecem. Respeitar essa semântica para não regravar campos não enviados. |
| 7 cenários de e-mail × 4 schemas | UserCreate, UserUpdate, UserLogin e EsqueciSenhaRequest concordaram em todos os casos: trim/caixa/+tag, Unicode NFC/NFD e domínio IDN aceitos; múltiplos @, espaço interno e NUL rejeitados. |
| Unicode no e-mail | EmailStr converteu NFD para NFC. Logo a normalização efetiva não é apenas strip/lower: incorpora email-validator. Isso deve ser considerado ao comparar com SQL lower/trim e avaliar registros legados. |
| 4 schemas de segredo | UserCreate.senha, UserLogin.senha, RedefinirSenhaRequest.nova_senha e PasswordConfirmation.senha_atual removem espaços externos. Verificado só por booleanos com fixture; nenhum hash ou verificação contra conta real. |

Dependências relevantes: base.SchemaModel aplica trim/Cc antes da validação dos campos; user.NormalizedEmail usa BeforeValidator; email_identity é compartilhado entre modelos, autenticação, busca e cooldown; modelos/index usam chave funcional SQL. Pydantic responde a campos normalizados antes de register/login/reset chamar hashing/verify. Assim, mexer na base ou na normalização de e-mail poderia mudar credenciais reconhecidas, unicidade, lookup e chave do limiter. Normalização de nomes deve ser específica de entrada e não alterar esses helpers globais.

Não foi verificada nesta etapa a unicidade no PostgreSQL real, entrega SMTPUTF8, compatibilidade de todas as contas antigas ou ausência completa de XSS. Nos pontos inspecionados, home/schedule usam textContent e administração escapa valores com escapeHtml. Manter ambos até alterações localizadas com testes.

### zxcvbn-ts — compatibilidade do build

- Confirmado no repositório: package.json declara apenas Playwright como devDependency; não há zxcvbn-ts ou bundler declarado. build-static.mjs remove/recria dist, exclui node_modules/scripts/tests e copia assets. Não foi executado porque escreveria artefatos e esta etapa é diagnóstica.
- A documentação oficial oferece build .mjs para navegador e pacotes de idiomas, mas seus exemplos usam imports npm. **Copiar esses imports para auth.js não funciona com o build atual.** É necessário preparar assets ES resolvidos/bundle ou mapear explicitamente todas as dependências; .mjs sozinho não garante ausência de imports transitivos não resolvidos.
- Estratégia recomendada: adaptação pequena e reproduzível do build para gerar assets locais versionados do core/common/en/pt-br; preparar antes da cópia para dist ou gerar dentro de dist após a limpeza. Não gerar bundle em dist antes de chamar buildStaticSite, pois ele seria apagado.
- Carregar estimador/dicionários somente nas páginas de novas senhas, por demanda. Não executar os exemplos de console.log da documentação com senhas; não usar matcher remoto, CDN runtime nem API de força. Mesmo dados de feedback podem carregar o segredo no objeto bruto: guardar apenas score/feedback seguro necessário à UI.
- Compatibilidade **conceitual confirmada**, não integração executada: não houve download/instalação/execução da biblioteca, alteração de lockfile ou medição de bundle/latência. Tentativa de ler metadados do registry via ferramenta web ficou indisponível; não foram inferidos versões, tamanho, licença específica do artefato ou advisories. Esses itens são gate da preparação aprovada, antes de incorporar dependências.
- Critérios propostos para futura medição: nenhum request do estimador no login; assets somente da própria origem; nenhum bare import npm no artefato; offline/falha sem quebra do formulário; baseline/resultado medidos com ferramentas de browser. Orçamento inicial sugerido para aprovação: até 1 MiB gzip total carregado sob demanda e p95 de avaliação até 100 ms no perfil mobile documentado, com entrada limitada ao máximo do backend e debounce. Se exceder, apresentar medição antes de adicionar worker ou nova ferramenta arquitetural; não enfraquecer dicionários silenciosamente.

Fontes consultadas: [getting started](https://zxcvbn-ts.github.io/zxcvbn/guide/getting-started/), [languages](https://zxcvbn-ts.github.io/zxcvbn/guide/languages/), [lazy loading](https://zxcvbn-ts.github.io/zxcvbn/guide/lazy-loading/). São referências de viabilidade; a aprovação da Etapa 1 não autoriza instalação.

### Separação de trabalho e riscos de conflito

| Fronteira | Regra para futura implementação |
| --- | --- |
| Sessão/API privada/JWT | Fora deste plano de UX; não alterar api.js, cookies, refresh token, claims ou gateway para adicionar medidor/olho. |
| Recuperação já corrigida localmente | Preservar recoveryInFlight, recoveryAvailableAt, cooldown, lease/fencing, resposta genérica e testes anteriores. Medidor só acompanha nova senha no reset; nunca inicia pedidos de recuperação. |
| Schemas | Não alterar trim global nem hash/verify. Nome novo tem validador específico. Mudança em email_identity afeta lookup/index/cooldown e requer investigação separada. |
| Formulários auth.js | Módulo UX separado; toggle type=button não chama submit, não substitui input e não altera value. Preservar payloads, autocomplete, bloqueios de envio e tratamento de erro. |
| Perfil/exclusão | Visibilidade somente no campo existente de senha atual; sem criar alteração de senha de perfil ou confirmação nova. Preservar foco, limpeza e autorização do diálogo. |
| Política de senha | Backend mantém regra vigente e contas legadas; medidor orienta. Aumento de mínimo, bloqueio por score, alteração de strip ou rehash em massa não pertencem à autorização da Etapa 1 nem devem ser efeitos laterais da Etapa 2. |
| Dados/infraestrutura | Nenhuma migração é necessária para visibilidade/medidor/normalização de novas entradas. Reparos de dados, colisões de e-mail ou mudança de chave/índice exigem proposta própria. |

## Proposta refinada para autorização futura — lotes pequenos

| Lote | Entrega delimitada | Testes e aceite objetivo |
| --- | --- | --- |
| Pendência da Etapa 1 | Metadados e amostra de serviço em sessão READ ONLY no alvo confirmado; se possível repetir pela conexão SQLAlchemy real | Registrar apenas encoding/flags e diagnóstico, sem dados pessoais; nenhuma escrita, migração ou alteração de processo. Não bloquear UX independente por ausência de acesso, mas não declarar banco validado. |
| 2A — nomes | Validador de entrada para criação/update; NFC/espaços e vazio visual sem mexer na base global | Casos legítimos Unicode/monônimo preservados, Cc/Cs/vazio/121 caracteres rejeitados conforme política definida; idempotência e limite bruto explícito; nome omitido/e-mail/hash intactos; snapshots de payloads de senha iguais aos atuais. |
| 2B — e-mails | Testes de consistência/colisões em banco descartável, sem mudar política/índice de produção | Cadastro concorrente aceita no máximo uma identidade; aliases e IDN preservados; login/recuperação consistentes; se houver divergência Unicode/SQL, parar e propor correção antes de mudar normalização. |
| 2C — visibilidade | Helper ES e integração nos quatro campos existentes; CSS com tokens locais | Mouse/teclado, aria-label, foco, valor/caret/autocomplete preservados; nenhuma requisição/submit adicional, nenhum log; sem regressão de diálogo ou envio/cooldown. |
| 2D — estimador | Aprovar versões/licenças/custo de dependências e preparação de assets; depois UI local nos fluxos de criação | Bundle resolvido e self-hosted, orçamento medido, testes de comuns/sequências/passphrase/Unicode, texto/cores/ARIA coerentes; zero transmissão da senha, fallback/offline e ausência no login comprovados. |
| 2E — fechamento | Regressões/revisão/documentação | Python/Node e Playwright desktop/mobile; PostgreSQL somente descartável explicitamente configurado e nenhuma migração remota; git diff --check e revisão do diff sem sobrescrever trabalho anterior. |

Ao concluir a Etapa 1, nenhum lote 2A–2E estava autorizado ou iniciado. A autorização posterior exclusiva de nomes e sua execução estão registradas abaixo; os demais lotes continuam sem aprovação. Não foi solicitada autorização para commit, push, deploy, migração ou alteração de dados reais.

## Lote 1 autorizado e implementado localmente — 2026-11-04

Autorização posterior exclusiva para normalização de nomes; corresponde ao lote 2A da tabela acima, chamado Lote 1 da Etapa 2 pelo usuário. **Somente esse lote passa a autorizado.** O restante da autorização negativa acima continua válido para e-mail, visibilidade, estimador e lotes seguintes.

### Política implementada

- Novo helper `backend/app/core/person_name.py`, sem dependências novas; tipo Annotated/BeforeValidator em `schemas/user.py`, somente em `UserCreate.nome` e `UserUpdate.nome`.
- String estrita, teto bruto 4.096 caracteres antes de normalizar; rejeita categorias Cc/Cs. Depois aplica NFC e split/join para converter sequências de whitespace Unicode em um espaço ASCII e remover whitespace externo. Tab/newline/NUL não são reparados: são rejeitados antes.
- Exige conteúdo visível: pelo menos um caractere de categoria letra, número, pontuação ou símbolo, excetuados fillers em branco U+115F/U+1160/U+3164/U+FFA0/U+2800. Marcas e caracteres de formato sozinhos não tornam o nome visível, mas são preservados junto de conteúdo visível, incluindo ZWJ/ZWNJ em nomes internacionais.
- Máximo normalizado 120 codepoints, não 120 bytes ou grafemas. Acentos, caixa, apóstrofos e hífens preservados; sem NFKC, transliteração, exigência de duas palavras ou unicidade de nome.
- Omissão em UserUpdate preservada, null explícito continua inválido. UserBase/UserResponse e o modelo SQLAlchemy não recebem o helper; leituras não regravam nem normalizam nomes existentes. Services, nome de cliente avulso e nome institucional não estão neste lote.
- Nenhuma alteração de SchemaModel, email_identity, hash/verify, JWT/cookies/sessão/recuperação, frontend ou política de autenticação.

### Evidência de implementação e validação

- Antes do código: `rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_person_name.py -q`, em backend, reproduziu falta de NFC/colapso, aceitação de invisíveis e ausência de teto bruto; 11 métodos, 15 falhas de assertions/subtests e 1 erro de validação esperado pela falta de normalização antes do limite.
- Após código, o mesmo comando: 11 testes aprovados.
- `rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_person_name*.py -q`, em backend: 14 testes aprovados. A tentativa inicial de integração no sandbox foi bloqueada ao abrir SQLite temporário; a repetição autorizada fora do sandbox usou somente o harness isolado e transporte de e-mail mockado.
- Novos testes: `backend/tests/test_person_name.py` e `test_person_name_flows.py`. Cobrem NFC/NFD, espaços Unicode, invisíveis/fillers, Cc/Cs, Unicode internacional e joiners, limites após NFC, teto bruto, omissão/null, UserResponse legado, idempotência e igualdade do comportamento prévio de e-mail/senhas. Fluxos comprovam cadastro normalizado, login/recuperação, resposta genérica e update que não muda e-mail/hash da fixture.
- `rtk proxy node --test frontend/tests/*.test.mjs`: 35 testes existentes aprovados. Nenhum arquivo frontend foi editado neste lote.
- `rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -q`, em backend, fora do sandbox: **302 testes executados em 273,618 s; 294 aprovados, 8 ignorados por exigirem PostgreSQL; zero falhas**. Inclui regressões de cadastro/login, recuperação/reset, sessões, autorização, schemas e migrações exclusivamente em bancos descartáveis. PostgreSQL não executado neste lote.
- Revisão independente somente leitura dos quatro arquivos de código/testes do lote não encontrou bugs concretos. Nenhuma consulta a ambiente real ou migração foi realizada como parte desta alteração; eventuais testes de migração da suíte usam apenas bancos descartáveis.
- README e REQUISITOS_STATUS atualizados somente para a regra nova; `graphify update .` concluído (11555 nós); `git diff --check` sem erros. Revisão final do diff confirma que schemas/base.py, email_identity.py, runtime de autenticação/recuperação e frontend não foram editados por este lote. Alterações anteriores preservadas.

### Riscos e limites do lote

Nomes novos ou explicitamente atualizados podem ter representação diferente por NFC/espaços; registros não enviados mantêm a representação antiga. Conteúdo visível não prova que um nome seja real; não foi adicionada regra restritiva ASCII ou filtro HTML. A regra não corrige mojibake armazenado. Os limites são por codepoints, portanto nomes com sequências combinantes/grafemas complexos usam mais posições; isso é explícito e permanece limitado a 120 após NFC. Dados reais e PostgreSQL implantado não foram usados como teste.

Não avançar para Lote 2 sem nova autorização. Nenhum commit, push, merge, deploy, instalação ou migração de ambiente real foi autorizado ou realizado.

## Lote 2 autorizado — testes de identidade e unicidade — 2026-11-04

Autorização posterior exclusiva para testes da política atual de e-mail. Corresponde ao lote 2B; não autoriza correções funcionais, novas políticas/índices, reparos de dados, dependências ou Lotes 3/4. A restrição histórica de início do Lote 2 acima foi atendida por essa nova autorização, sem ampliar os demais escopos.

- Inspecionados schemas, helper Python/SQL, ORM/índices, revisão Alembic existente, cadastro/login, atualização administrativa e recuperação, além dos transportes de e-mail. Evidências, riscos e propostas separados no [relatório](../../VALIDACAO_IDENTIDADE_EMAIL_20261104.md).
- Adicionados apenas `backend/tests/test_email_identity_contract.py`, `test_email_identity_postgres.py` e `test_email_identity_delivery.py`. Sem alterações em runtime, frontend, normalização de e-mail/senha, hashes, JWT, cookies, sessões ou mecanismo de recuperação. Trabalho local anterior preservado.
- PostgreSQL real novo e descartável: **18.6**, UTF8 no servidor/cliente, driver utf-8, datcollate/datctype C. Índice único funcional confirmado no catálogo. Duas disputas HTTP reais de cadastro, ASCII e Unicode NFC/NFD, com duas conexões/backend_pid distintos e pré-consultas sincronizadas: **um 201, um 409 e uma conta persistida** em cada disputa. SQLSTATE 23505 da constraint reconhecido. Não se usaram mocks como prova de atomicidade.
- Foco final `rtk proxy backend\.venv\Scripts\python.exe tools/test-recovery-postgres.py discover -s tests -p test_email_identity*.py -q`: **23/23 aprovados em 10,956 s**, zero ignorados. Launcher encerrou e removeu o cluster. Inclui teste existente da revisão de identidade em schema isolado; nenhuma migração em banco real e nenhuma revisão criada/editada.
- Foco SQLite final, em backend, `rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -p test_email_identity*.py -q`: **23 executados, 17 aprovados/6 ignorados exclusivos de PostgreSQL**, 8,893 s. Suíte completa `rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -q`: **318 executados, 305 aprovados/13 ignorados exclusivos de PostgreSQL**, 239,576 s, zero falhas. Essa coleta ocorreu antes do último método de reforço de recuperação; o método adicional passou nos focos finais de ambos os bancos. Não se declara completa de 319 executada.
- Node `rtk proxy node --test frontend/tests/*.test.mjs`: **35/35 aprovados**. Completa PostgreSQL e Playwright não executados neste lote, sem alteração de frontend ou comportamento funcional.
- Revisão independente somente leitura identificou que resposta genérica+cooldown poderiam ocultar uma variante não localizada. Novo método testa cada variante como primeira recuperação, destinatário canônico, token associado à conta e resposta indistinguível; revisor confirmou resolução. Nenhum outro achado de teste.
- Lacunas reproduzidas somente em fixtures: ORM não NFC versus schemas NFC pode impedir lookup de conta legada NFD; collation C não unifica toda caixa Unicode nem NFC/NFD; trim SQL não remove NBSP como Python. Cadastros normalizados HTTP testados mantêm unicidade concorrente, mas isso não prova todos os dados/collations do ambiente. Nenhuma correção funcional ou de dado foi implementada.
- Endereços internacionais: validação/armazenamento/login/recuperação testados separados de entrega. Stdlib SMTP exige SMTPUTF8 para as representações Unicode atuais; sem extensão, erro genérico antes de sendmail; com extensão simulada, serialização apropriada. Brevo mantém payload Unicode em transporte mockado. Não houve envio real, teste de entregabilidade, DNS ou verificação de suporte efetivo do provedor.
- Tentativas iniciais de teste: sandbox bloqueou SQLite temporário; repetido fora dele com autorização. Erros de asserção nos testes novos (argumento SMTP posicional e cast PostgreSQL ::text) foram corrigidos somente nos testes; execuções finais acima sem falhas. Warning existente de reflexão SQLite de índice de expressão registrado, sem extrapolar paridade PostgreSQL a partir dele.
- Fechamento: `rtk proxy graphify update .` concluído com código 0, AST local sem LLM, 11603 nós/23843 arestas. `rtk proxy git diff --check` com código 0 (somente aviso de futura conversão LF/CRLF em teste preexistente). Leitura UTF-8 estrita e verificação de whitespace dos seis arquivos deste lote sem erros, inclusive novos não rastreados. Revisão do status/diff confirma preservação do trabalho anterior; nenhum arquivo funcional foi editado pelo lote.

Pendências: aprovar separadamente diagnóstico somente leitura de metadados/contagens no alvo confirmado, eventual estratégia de canonicalização/colisões e avaliação de entrega internacionalizada em ambiente de teste. Lotes 3/4 e correções funcionais permanecem aguardando autorização; sem instalação, banco real, commit, push, merge ou deploy.

## Lote 3 autorizado — visibilidade de senhas e acessibilidade — 2026-11-04

Autorização posterior exclusiva para o lote 2C da proposta, chamado Lote 3 pelo usuário. Não autoriza medidor, dependências, alterações de credenciais/autenticação, correções de e-mail, banco ou migrações. As pendências de autorização acima são históricas; somente visibilidade passa a autorizada aqui.

### Arquivos e implementação delimitada

- Inventário confirmou somente quatro campos: `login.html#login-password`, `cadastro.html#register-password`, `reset.html#reset-password` e `client-account.html#delete-password`. `forgot.html` pede apenas e-mail; não foi criado campo/fluxo novo de confirmação ou alteração de senha.
- Novo `frontend/assets/js/password-visibility.mjs`, carregado diretamente nas quatro páginas, com opt-in `data-password-visibility`. Preserva integralmente `auth.js`, `schedule.js`, API e handlers existentes. O input original mantém valor, id/name, autocomplete, validação e propriedade do formulário; o helper nunca lê/copia o valor. Somente a apresentação alterna password/text, com restauração de seleção/direção quando suportada e sem mover foco do botão.
- Botão nativo `type=button`, nomes de ação “Mostrar senha”/“Ocultar senha”, aria-controls, SVG decorativo oculto da árvore acessível. Sem aria-pressed com rótulo variável: é botão de ação, cujo nome informa a próxima ação. Estado inicial oculto, reset remascara; fechamento do diálogo já chama reset no fluxo preexistente. Disabled direto ou herdado de fieldset desabilita e remascara o controle.
- WeakMap torna a inicialização idempotente. MutationObserver trata campos opt-in inseridos/movidos e mudanças de disabled, incluindo fragmentos inicializados antes da inserção. Não há listener novo a cada reabertura de diálogo. Sem listener de input, rede, storage ou telemetria.
- CSS `.password-*` localizado em `frontend/assets/css/style.css`: botão separado do input para evitar sobreposição com autofill; alvo 46×46 px, grade flexível, borda fina/canto reto, tokens de installation.css e foco visível existente. Tokens e tema da instalação não foram alterados.
- `frontend/e2e/essential-flows.spec.mjs`: somente quatro linhas de Tab/Shift+Tab adicionadas à expectativa de foco do diálogo, preservando todas as alterações locais anteriores. Esse arquivo com backend não foi executado neste lote; a suíte estática nova cobre a navegação e handlers correspondentes sem banco.

### Decisões e compatibilidade

- Execução no workspace atual para preservar as dependências e alterações locais dos Lotes 1/2; sem checkout, descarte, commit ou reorganização. Plano existente reutilizado, sem expansão para outros lotes.
- Integração por módulo nas páginas evita acoplar o controle aos handlers de login/reset/recuperação e seus bloqueios preexistentes. Se JavaScript do controle falhar, os inputs HTML continuam password e os formulários conservam seu markup original.
- Ao habilitar revelação, spellcheck=false, autocorrect=off e autocapitalize=none são aplicados ao campo para não oferecer assistência de texto como se a credencial revelada fosse texto comum. Não normalizam valor, não alteram autocomplete nem regras de autenticação. São orientações ao navegador; não comprovam comportamento de todo IME, extensão ou serviço do sistema operacional.

### Testes e evidências

- Novos testes: `frontend/tests/password-visibility.test.mjs`, `frontend/e2e/password-visibility.spec.mjs` e configuração `password-visibility.config.mjs`. Reutilizam servidor estático local existente; toda API é fictícia/interceptada. Trace, vídeo e screenshots automáticos desativados para não gravar conteúdo de campos. Nenhum backend, banco, migração ou transporte de e-mail foi iniciado.
- RED do primeiro teste Chromium: botão não encontrado antes de implementar. Sandbox inicialmente não encontrava o executável Playwright; execução autorizada fora dele usou navegadores já instalados, sem instalação. Primeira matriz parcial encontrou erro no próprio teste, que tentava preencher e-mail na página reset; corrigida somente a condição do teste.
- Verificações cobrem os quatro formulários, Enter/Espaço/Tab e foco, rótulos acessíveis, aria-controls, valor/seleção/direção, autocomplete, repetição e reinicialização oculto/visível sem duplicação, disabled/fieldset, DOM dinâmico/desconectado, reset/fechamento/reabertura, payloads exatos e handlers de sucesso/erro com respostas fictícias, redirecionamentos existentes e limpeza/remascaramento. Revelar/ocultar não gera requests; nenhum segredo da fixture em HTML/atributos, console ou storage adicional. Auditoria do módulo e teste Node verificam ausência de leitura de value, logs, rede ou persistência.
- Contraste calculado nos tokens atuais ≥4,5:1, foco com outline ≥2 px, alvo ≥44 px e ausência de overflow horizontal. Matriz Chromium 1280×800 e 320×568, Firefox desktop e WebKit desktop. Capturas adicionais **somente do login vazio**, em 1280 e 320 px, revisadas visualmente; sem conteúdo de credenciais, rede externa bloqueada. Artefatos locais em test-results, não publicados.
- Revisão independente somente leitura não encontrou bloqueio. Observação menor de cobertura (reinit enquanto visível) atendida; asserções finais verificam que a senha continua revelada após duas inicializações e alterna uma vez por acionamento. Depois foi acrescentada regressão de sucesso dos handlers; verificação adicional do implementador identificou falta de flags de assistência de texto, reproduzida RED por atributo spellcheck ausente e corrigida somente no helper de apresentação. Matriz final reexecutada após essa alteração.

Comandos executados a partir da raiz:

```powershell
rtk proxy node --test frontend/tests/*.test.mjs
rtk proxy node --check frontend/assets/js/password-visibility.mjs
rtk proxy node node_modules/@playwright/test/cli.js test --config frontend/e2e/password-visibility.config.mjs
rtk proxy git diff --check
rtk proxy graphify update .
```

Node final: **37/37 aprovados**, zero falhas/ignorados. Playwright final após as flags de assistência: **32/32 aprovados em 1,1 min**, zero falhas/ignorados (8 por projeto: Chromium desktop, Chromium 320 px, Firefox desktop e WebKit desktop). `node --check` do helper com código 0. SHA-256 em memória confirmou igualdade byte a byte de auth.js, schedule.js, installation.css, schemas/user.py e core/email_identity.py antes/depois. Nenhuma dependência instalada, regra backend alterada, consulta real, e-mail, commit, push, merge ou deploy.

Fechamento: `graphify update .` após a última alteração de código concluiu com código 0, extração AST local sem LLM, 11617 nós/23862 arestas. `git diff --check` com código 0 (aviso LF/CRLF em teste preexistente, sem erro de whitespace). Quatro novos arquivos lidos em UTF-8 estrito e conferidos contra whitespace, sem erros; status e diff dos arquivos editados revisados. README e REQUISITOS_STATUS atualizados somente para esta apresentação e evidências.

### Limites e validação manual pendente

Nomes/roles acessíveis e teclado foram testados por Playwright; NVDA/JAWS/VoiceOver reais não foram executados. Autofill de gerenciadores externos e sugestão de teclado em aparelhos físicos não foram testados: nó e atributos apropriados foram preservados, mas isso não prova interoperabilidade com todos os fornecedores. Chromium mobile é emulação de viewport/toque, não Android/iOS real; WebKit Windows não é Safari em iPhone. Edge/Chrome por canais de marca e alto contraste/forced-colors não foram executados neste lote. Testes de backend, PostgreSQL e E2E com banco não repetidos, pois não houve mudança backend e esta autorização proíbe banco/migrações. Os resultados desses lotes anteriores continuam históricos, sem serem apresentados como executados agora.

Validação manual futura: em ambiente de teste autorizado, usar credencial fictícia nos quatro campos; conferir anúncio da próxima ação com leitor de tela, Tab/Enter/Espaço, foco e seleção; verificar colagem e autofill do gerenciador utilizado, teclado móvel sem autocorreção/capitalização, desabilitação, cancelamento e reabertura da exclusão. Confirmar login/cadastro/reset/exclusão nos fluxos existentes e que toggles não disparam requests. Não colocar senha em screenshots, relatórios ou logs. Publicação e qualquer teste com dados reais continuam exigindo autorização separada. Lote 4 e correções funcionais de e-mail não iniciados.

## Revisão integrada autorizada — Lotes 1, 2 e 3 — 2026-11-04

- Relatório com matriz de arquivos/origem, contratos, problemas, comandos e sequência exata de seis commits propostos: [revisão integrada](../../REVISAO_INTEGRADA_LOTES_1_2_3_20261104.md). Nenhum commit, staging, branch, push, merge ou deploy realizado; nenhum código funcional ou teste de produto editado nesta revisão. Alterados somente relatório/plano/status e novos artefatos de diagnóstico em pasta exclusiva.
- Backend completo SQLite: **319 executados em 254,232 s; 306 aprovados, 13 ignorados exclusivos de PostgreSQL, zero falhas**. Agora inclui também o último método de recuperação acrescentado no Lote 2, que não estava na coleta completa histórica de 318.
- Backend completo PostgreSQL 18.6 novo e descartável: **319 executados em 310,887 s; 317 aprovados, 2 ignorados específicos de SQLite, zero falhas**. UTF8/utf-8 e locale C confirmados; índice/cadastros concorrentes reais/migrações/paridade incluídos. Cluster encerrado e removido pelo launcher, sem usar banco existente.
- Node: **37/37**. Playwright essenciais com API real local e SQLite temporário migrado, desktop/mobile: **56/56**, 2,5 min. Playwright de visibilidade Chromium desktop/320 px, Firefox e WebKit: **32/32**, 1,2 min. Nenhum e-mail real; transportes mockados/desconfigurados. Saídas em diretório novo, sem limpar artefatos anteriores; captura de campos desativada no runner de revisão.
- `pip check` sem dependência quebrada; npm ls confirma Playwright 1.64.1. Manifestos/lockfiles/versões sem diff e nenhuma instalação. Sintaxe de 33 candidatos Python/JS verificada; padrões de segredo revisados com saída somente de metadados. Ocorrências encontradas classificadas como template do README, fixtures e interpolação de credencial descartável; nenhuma credencial real identificada. Não se auditou CVEs online ou conteúdo de arquivos locais excluídos da proposta.
- Revisão independente somente leitura não encontrou novo bloqueio. Confirmada dependência de organização: testes de recuperação do Lote 2 exigem o cooldown local anterior ainda ausente do HEAD. Proposta inclui primeiro os pacotes anteriores de recuperação/barbeiros, separados dos três lotes; se o pré-requisito for adiado, não considerar a extração isolada do Lote 2 verde. Estados intermediários de commits não foram montados/testados.
- Divergência preexistente de nome mínimo: HTML 2 versus API 1. Mantida sem alteração neste escopo, assim como lacunas de identidade Unicode/collation/SMTPUTF8, leitores de tela reais, gerenciadores e aparelhos físicos/forced-colors. Nenhuma correção de e-mail/sessão ou Lote 4 iniciada.
- Graphify consultado e não reconstruído: sem mudança no código do produto/testes candidatos. `git diff --check` com código 0; apenas aviso LF/CRLF de teste preexistente. Histórico e índice Git aguardam aprovação explícita.

## Organização local dos commits autorizada — 2026-11-04

Autorização posterior para criar feat/qualidade-auth-ux a partir da main e os seis commits da revisão integrada, sem push/PR/merge/deploy. HEAD inicial a2e849eac2aabe4f03a76232ef7500f9aaf2e7bc; índice vazio e backup existente preservado. A proposta histórica acima foi executada somente após essa autorização.

- Inventário inicial de nomes/hashes: 1.385 arquivos acessíveis (24 modificados e 1.361 não rastreados). Subpasta excluída de referências de skill sem permissão de leitura registrada como limitação; sem alteração ou inclusão. Todos os arquivos acessíveis permaneceram idênticos até o registro documental desta organização; somente plano/status/relatório recebem novas notas aprovadas.
- Pacotes selecionados por caminhos explícitos, com três trechos de essential-flows separados no índice. Diferenças staged, sintaxe e padrões de segredo conferidos antes de cada commit. Graphify/skills/arquivos pessoais/artefatos nunca staged; nenhuma dependência instalada ou funcionalidade adicional implementada.
- Estados intermediários exportados exclusivamente do índice. Recuperação: backend 55 aprovados/2 ignorados e Node30; barbeiros: backend6/Node5; nomes e regressão de autenticação:18; e-mails: SQLite21 aprovados/6 ignorados e PostgreSQL real descartável27; visibilidade: Node37/Playwright32. Zero falhas nos pacotes validados. Detalhes e hashes dos cinco primeiros commits no relatório integrado.
- Sexto commit somente documental; resultados da Etapa C, executada depois dele, constarão da entrega e de manifestos locais. Não antecipar aqui resultados ainda não executados. Permanecem as limitações funcionais/manuais já registradas; sem Lote 4, alteração de e-mail/senha/sessão ou operação em banco real.

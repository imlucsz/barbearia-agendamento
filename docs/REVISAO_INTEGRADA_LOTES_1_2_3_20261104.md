# Revisão integrada dos Lotes 1, 2 e 3 — 2026-11-04

**Conclusão:** o estado acumulado passou nas regressões executadas e pode ser organizado em commits, respeitando a dependência dos testes do Lote 2 na recuperação já corrigida localmente. Não equivale a aprovação para publicar ou migrar ambiente real. Nenhum defeito novo bloqueante foi encontrado; nenhuma funcionalidade ou teste de produto foi alterado nesta revisão. Apenas este relatório, plano/status e artefatos novos de diagnóstico foram escritos.

## Matriz de arquivos e origem

| Grupo | Arquivos / trechos | Orientação |
| --- | --- | --- |
| Lote 1 — nomes | `backend/app/core/person_name.py`; `backend/app/schemas/user.py`; `backend/tests/test_person_name.py`; `backend/tests/test_person_name_flows.py` | Helper novo e diff do schema restrito a nome em UserCreate/UserUpdate. Sem migração. |
| Lote 2 — identidade | `backend/tests/test_email_identity_contract.py`; `test_email_identity_delivery.py`; `test_email_identity_postgres.py` (todos em backend/tests); `docs/VALIDACAO_IDENTIDADE_EMAIL_20261104.md` | Testes e documentação apenas. Não contêm correção funcional de e-mail. |
| Lote 3 — controle | `frontend/assets/js/password-visibility.mjs`; bloco `.password-*` em `frontend/assets/css/style.css` | Módulo independente; não editar handlers para organizar o commit. |
| Lote 3 — páginas | `frontend/pages/login.html`, `cadastro.html`, `reset.html`, `client-account.html` | Só opt-in no input e script module. Forgot permanece só e-mail. |
| Lote 3 — testes | `frontend/tests/password-visibility.test.mjs`; `frontend/e2e/password-visibility.spec.mjs`; `password-visibility.config.mjs`; quatro linhas de Tab/Shift+Tab em `essential-flows.spec.mjs` | Essential-flows é misto: não incluir os demais hunks neste lote. |
| Documentação compartilhada | `README.md`; `docs/REQUISITOS_STATUS.md`; `docs/superpowers/plans/2026-11-03-qualidade-dados-auth-ux.md`; este relatório | README/status também descrevem recuperação anterior. Usar commit documental após os commits de código. |
| Recuperação anterior — código | `backend/.env.example`; `backend/app/config.py`; `backend/app/core/rate_limit.py`; `password_reset_limits.py`; `backend/app/models/user.py`; `backend/app/routers/auth.py`; `backend/alembic/versions/20261103_01_password_reset_limits.py`; `frontend/assets/js/auth.js` | Preexistia aos Lotes 1–3. O diff de auth.js é cooldown, não visibilidade. Não atribuir sessão/JWT a estes lotes. |
| Recuperação anterior — testes | `backend/tests/test_password_reset.py`; `test_password_reset_limits_migration.py`; `password_reset_process_worker.py`; `test_brevo_email.py`; `test_configuration.py`; `test_schema_migrations.py`; `frontend/tests/password-recovery.test.mjs`; `frontend/e2e/start-test-environment.mjs`; hunk de cooldown/reload em `essential-flows.spec.mjs`; `tools/test-recovery-postgres.py` | Pré-requisito para manter os testes de recuperação do Lote 2 verdes. Launcher PostgreSQL já existia e não foi alterado pela revisão. |
| Barbeiros anterior | `backend/app/booking.py`; `backend/app/routers/users.py`; `backend/tests/test_barber_service_assignments.py`; `frontend/assets/js/admin_management.js`; `frontend/tests/admin-reference-data.test.mjs`; teste de falha de clientes em `essential-flows.spec.mjs` | Pacote funcional anterior independente dos três lotes. |
| Documentação anterior desses pacotes | `docs/CORRECAO_RECUPERACAO_E_BARBEIROS_20261103.md`; `docs/superpowers/plans/2026-11-03-recuperacao-e-barbeiros.md` | Consolidar no commit documental depois dos pacotes correspondentes. |

Arquivos fora da seleção proposta, preservados sem remoção: `.agents/skills/`, `.codex/skills/`, `skills-lock.json`, `GUIA.md`, `codex-models.json`, arquivo local `cue-merge --oneline`, `docs/business/` e seu áudio, `docs/AUDITORIA_SUPERFICIE_API_20261103.md`, `docs/AUDITORIA_WORKTREE_20261103.md` e CSV correspondente. Não foram auditados como candidatos dos lotes nem autorizados para inclusão indiscriminada.

`graphify-out/` já estava não rastreado e agrega outros trabalhos/skills locais. Manter separado desta sequência; sua eventual inclusão precisa de recorte/revisão próprios. Os artefatos anteriores de test-results foram preservados. Os novos ficaram em `test-results/integrated-review-20261104-1793764211606/`, inclusive runner e auditor somente de diagnóstico; não são candidatos a commit.

## Contratos revisados

- **Cadastro:** frontend envia nome com trim externo, e-mail com trim e senha original do campo. API aplica o helper de nome antes do limite; e-mail conserva EmailStr + política vigente e senha conserva os validadores preexistentes. Checkbox de consentimento e payload não mudaram. Cadastro duplicado continua 400 no pré-check e 409 na corrida real.
- **Login:** não recebe normalizador de nome. Busca de e-mail, hash/verify, claims, cookies e sessões permanecem como estavam. Módulo de visibilidade não acessa o valor; trocar type não muda o payload. Regressões incluem Argon2 e bcrypt legado somente em fixtures.
- **Atualização administrativa:** helper atua apenas em nome explicitamente fornecido. Omissão permanece excluída de model_dump(exclude_unset=True); null explícito continua rejeitado. Testes preservam nome legado em leituras e e-mail/hash ao atualizar somente nome. Não foi criado endpoint de autoedição.
- **Recuperação/reset:** mesmos payloads e respostas públicas genéricas. Os testes do Lote 2 mockam apenas o transporte quando necessário; não alteram normalização, limites ou geração/consumo de tokens. A página forgot não ganhou controle nem campo. Reset preserva token no fragmento e o controle remascara o input quando o handler existente chama form.reset().
- **Exclusão:** o mesmo input id=delete-password continua sendo lido pelo handler existente. Botão de visibilidade não submete; navegação por Tab passa pelo novo controle. Fechar o diálogo chama o reset preexistente, limpa e oculta e devolve foco ao acionador. E2E real confirmou payload/fluxo com conta fictícia.
- **Acessibilidade/inicialização:** botões nativos, nomes da próxima ação, aria-controls, SVG decorativo, foco visível, seleção, disabled e fieldset coerentes. WeakMap e observer evitam duplicação em reinicialização/reabertura/inserção. Autocomplete e nó original preservados; flags de assistência de texto não alteram credenciais.

Inspeção Git confirmou ausência de diff em `core/email_identity.py`, `core/security.py`, `schemas/base.py`, `core/email.py`, `dependencies.py`, `frontend/assets/js/api.js` e `schedule.js`. O diff em schemas/user.py contém somente nomes. Alterações de recuperação em routers/auth.py são do pacote anterior, não uma mudança funcional do Lote 2. Revisão independente somente leitura concordou, sem novo bloqueio.

## Resultados executados nesta revisão

| Verificação | Executados | Aprovados | Ignorados | Falhas |
| --- | ---: | ---: | ---: | ---: |
| Backend completo SQLite temporário | 319 | 306 | 13 (PostgreSQL) | 0 |
| Backend completo PostgreSQL descartável | 319 | 317 | 2 (SQLite) | 0 |
| Node completo | 37 | 37 | 0 | 0 |
| Playwright essenciais, desktop 1280×800 e mobile 390×844 | 56 | 56 | 0 | 0 |
| Playwright visibilidade, Chromium desktop/320 px, Firefox e WebKit desktop | 32 | 32 | 0 | 0 |

SQLite: 254,232 s. PostgreSQL: 310,887 s. Essenciais: 2,5 min. Visibilidade: 1,2 min. Não se somam essas contagens como casos únicos, pois algumas coberturas se sobrepõem.

PostgreSQL **18.6** real em cluster novo, somente loopback, credencial temporária e schemas/banco exclusivos de teste. UTF8 no servidor/cliente, driver utf-8, datcollate/datctype C; índice funcional único confirmado. A suíte inclui cadastros concorrentes reais com duas conexões, resultados 201/409 e uma conta por identidade; não substituídos por mocks. Migrações/paridade e concorrência de recuperação também passaram no banco descartável. Launcher confirmou encerramento e remoção do cluster criado. Nenhum banco existente de desenvolvimento, homologação ou produção foi utilizado.

E2E essenciais usou API real local e SQLite criado/migrado pelo harness; transporte de e-mail explicitamente desconfigurado. Testes de e-mail em backend usaram mocks. Não houve e-mail real. O runner de revisão desativou trace/screenshot/vídeo e usou pasta de saída nova para preservar os artefatos anteriores.

Comandos reais principais:

```powershell
# Em backend
rtk proxy .\.venv\Scripts\python.exe -m unittest discover -s tests -q
rtk proxy .\.venv\Scripts\python.exe -m pip check
# Na raiz
rtk proxy backend\.venv\Scripts\python.exe tools/test-recovery-postgres.py
rtk proxy node --test frontend/tests/*.test.mjs
rtk proxy node node_modules/@playwright/test/cli.js test --config test-results/integrated-review-20261104-1793764211606/essential.config.mjs --project desktop-1280x800 --project mobile-390x844
rtk proxy node node_modules/@playwright/test/cli.js test --config frontend/e2e/password-visibility.config.mjs --output test-results/integrated-review-20261104-1793764211606/visibility
rtk proxy backend\.venv\Scripts\python.exe test-results/integrated-review-20261104-1793764211606/audit-candidates.py
rtk proxy npm ls --depth=0
rtk proxy git diff --check
```

## Higiene, dependências e credenciais

- `pip check`: No broken requirements found. `npm ls --depth=0`: Playwright 1.64.1 instalado conforme package.json; nenhuma instalação realizada. Manifestos/lockfiles, versões Python/Node e requirements sem diff. Não foi realizada auditoria online de CVEs; estes checks verificam consistência local e ausência de mudança de dependências.
- Auditor local revisou 46 candidatos dos lotes e pacotes anteriores propostos, incluindo este relatório atualizado, com AST Python e node --check em 33 arquivos; nenhum erro de sintaxe. Os padrões de segredo imprimem somente arquivo/linha/regra, nunca conteúdos. Não foram lidos arquivos .env reais.
- Ocorrências revisadas são URL de exemplo já existente no README, URLs fictícias de testes de configuração e interpolação da credencial gerada pelo launcher descartável. Nenhuma credencial real identificada nos candidatos. Fixtures de senha/token não são dados de usuários. Busca por padrões e revisão manual não constituem prova universal contra segredos em formatos desconhecidos; arquivos locais excluídos não estão aprovados para inclusão.
- `git diff --check`: código 0. Aviso de futura conversão LF/CRLF em test_brevo_email.py é preexistente e não foi normalizado. Warnings SQLite de reflexão de índice de expressão continuam; índice e paridade foram verificados em PostgreSQL real. Logs estruturados de falha de auditoria/recuperação aparecem em testes que simulam indisponibilidade, sem falhar a suíte nem imprimir tokens.
- Índice Git inicialmente vazio; nenhuma operação de staging, branch, commit, reset, push ou merge executada. Graphify foi consultado; não foi reconstruído nesta revisão, que não alterou código do produto ou seus testes.

## Problemas e riscos residuais

1. **Dependência de organização, confirmada:** testes de equivalência/recuperação do Lote 2 esperam um envio no cooldown. HEAD ainda não contém o pacote local de recuperação que fornece isso. Publicar apenas Lote 2 sobre HEAD não representa o estado verde validado. Integrar primeiro o pré-requisito mediante aprovação; não remover asserções, simular atomicidade ou modificar política para contornar a dependência.
2. **Baixa, preexistente:** cadastro HTML exige nome com minlength=2; API permite 1. Um nome legítimo de um caractere é aceito pela API e barrado pelo formulário. Já existia no HEAD e não foi ampliado/corrigido nesta revisão.
3. **Identidade/legados, preexistente:** EmailStr/ORM/SQL diferem em NFC/NFD, Unicode/locale e NBSP. Índice sob C não garante equivalência universal. Os testes caracterizam lacunas e não corrigem dados. Versão/collation/estado de homologação não foram inspecionados.
4. **Entrega:** aceitação de endereço internacional no schema não prova DNS, suporte SMTPUTF8 do provedor ou entrega. Nenhuma conta real, servidor SMTP real ou entrega Brevo foi testada.
5. **UX manual:** NVDA/JAWS/VoiceOver, gerenciadores externos, aparelhos físicos, IME/assistência de texto real e forced-colors continuam pendentes. Preservação de atributos e testes dos motores não garantem comportamento de todas as extensões/teclados. Mobile foi emulado; WebKit Windows não equivale a Safari iOS.
6. **Granularidade Git:** o estado acumulado foi testado. Estados intermediários de cada commit proposto não foram montados/testados, pois não houve alteração do índice ou checkout. Após aprovação, validar cada pacote antes do commit e repetir os checks finais sobre o staged diff.

Não foi necessária correção de bug. Não iniciar Lote 4, mudanças de sessão ou correção funcional de e-mail a partir destas observações.

## Sequência exata recomendada de commits (somente proposta)

Os dois primeiros pacotes são anteriores aos lotes e exigem aprovação explícita para sua inclusão na organização. A ordem abaixo produz o estado acumulado validado, sem misturar código de UX com limites de recuperação. Documentação compartilhada fica por último para evitar atribuição incorreta de hunks.

1. **`fix(auth): limitar solicitações de recuperação de senha`**
   - Código e testes da recuperação anterior conforme a matriz; inclui revisão 20261103_01, configuração, modelo/limiter/reserva, routers/auth.py, auth.js, limpeza de transportes do harness e launcher PostgreSQL.
   - Em essential-flows.spec.mjs incluir **somente** a asserção do contador desabilitado, comentário e reload do teste de recuperação.
   - Descrição: impedir envios repetidos com admissão compartilhada e preservar links/respostas genéricas.
2. **`fix(admin): corrigir seleção e elegibilidade de barbeiros`**
   - booking.py, routers/users.py, test_barber_service_assignments.py, admin_management.js e admin-reference-data.test.mjs.
   - Em essential-flows.spec.mjs incluir **somente** o teste de falha da referência de clientes que preserva barbeiros/serviços.
   - Descrição: carregar referências independentemente e impedir novos agendamentos com profissionais bloqueados/inativos.
3. **`feat(validation): normalizar nomes Unicode em novas entradas`**
   - Os quatro arquivos do Lote 1 da matriz, sem helpers globais, modelos persistidos ou migração.
   - Descrição: aplicar NFC/espaços e validação localizada a nome fornecido em criação/atualização, preservando leituras e credenciais.
4. **`test(auth): caracterizar identidade e unicidade de e-mails`**
   - Os três novos testes do Lote 2 e docs/VALIDACAO_IDENTIDADE_EMAIL_20261104.md.
   - Descrição: cobrir contratos, colisões, PostgreSQL concorrente e limites de transporte internacionalizado sem alterar a política.
5. **`feat(ui): adicionar visibilidade acessível de senhas`**
   - Os dez arquivos/trechos do Lote 3 da matriz: módulo/CSS/quatro páginas/três novos arquivos de teste-config e quatro linhas de teclado em essential-flows.spec.mjs.
   - Descrição: mostrar/ocultar no mesmo input, preservando teclado, autofill, seleção e handlers, com remascaramento no reset/disabled.
6. **`docs: registrar correções locais e revisão integrada de autenticação`**
   - README.md; docs/REQUISITOS_STATUS.md; plano de qualidade; este relatório; docs/CORRECAO_RECUPERACAO_E_BARBEIROS_20261103.md; plano de recuperação e barbeiros.
   - Descrição: consolidar evidências, dependências, limitações, validação manual e futura migração sem confundir pronto para commit com pronto para deploy.

Não usar git add . nem incluir essential-flows inteiro antecipadamente: há três origens distintas. Na execução futura aprovada, selecionar os hunks correspondentes e inspecionar git diff --cached, --stat e --check antes de cada commit. Nada dessa sequência foi executado nesta revisão. Se os pacotes anteriores forem adiados, a extração do Lote 2 deve aguardar seu pré-requisito; os testes não serão enfraquecidos para parecer independentes.

## Organização local posteriormente autorizada — 2026-11-04

A seção anterior registra a revisão e proposta antes da autorização. O usuário aprovou depois a criação de `feat/qualidade-auth-ux` e exatamente os seis commits propostos, sem publicação. A branch foi criada a partir da main em `a2e849eac2aabe4f03a76232ef7500f9aaf2e7bc`, com índice inicialmente vazio. A main e a branch `backup/feat-back-auth-lucas-unpublished-9353a9f` não foram movidas.

O inventário anterior ao staging registrou nomes e SHA-256 de 24 arquivos modificados e 1.361 não rastreados acessíveis (1.385 arquivos). Uma subpasta excluída `.codex/skills/graphify/references/` recusou leitura mesmo fora do sandbox; sua limitação foi registrada, sem alterar ACLs, acessá-la por contorno ou incluí-la em commit. Os demais excluídos, inclusive Graphify, permaneceram intactos. Manifesto inicial, patches staged e cópias de teste ficam em pasta nova/ignorada de test-results; nenhum artefato anterior foi removido.

Cada pacote usou lista explícita de caminhos. Em essential-flows.spec.mjs, o índice recebeu separadamente o trecho de recuperação, o teste de barbeiros e, por último, as quatro linhas de foco; o arquivo no worktree não foi substituído. Antes dos commits, foram conferidos nomes exatos, diff --cached --check, --stat, sintaxe e padrões de segredo nos blobs staged. Nenhum arquivo pessoal, skill, artefato ou grafo entrou no índice.

Para validar estados intermediários reais, exportou-se somente o índice para diretórios novos. Os testes backend confirmaram importação de app dentro dessa cópia, sem acesso aos arquivos ainda não staged. Dependências instaladas foram reutilizadas; sem instalação.

| Pacote | Commit criado | Validação na cópia do índice antes do commit |
| --- | --- | --- |
| Recuperação | `fd4e55aa171fdc4ac40a4bd1aae9304f296aa0e9` | Backend: 57 executados, 55 aprovados/2 ignorados PostgreSQL; Node 30/30. |
| Barbeiros | `6178169d4f4d40f89322afe04052e39591efcf93` | Backend 6/6; Node 5/5. |
| Nomes | `07b6f3ebc973f222c747df52c64433f79eb34ccf` | Nomes/fluxos/regressão de autenticação: 18/18. |
| E-mails | `f05f53797f725f05f852de61bfc47a72ccead798` | SQLite: 27 executados, 21 aprovados/6 ignorados; PostgreSQL 18.6 descartável: 27/27, incluindo concorrência real e remoção do cluster. |
| Visibilidade | `4389b75e55d4c7a03ee28f585e702b3bcc724214` | Node 37/37; Playwright multibrowser 32/32, 58,8 s. |

Os testes acima terminaram sem falhas. O sexto pacote contém somente os seis documentos da proposta, com este registro e o plano/status atualizados. Seu hash e os resultados da validação completa **posterior aos seis commits** serão informados na entrega final e nos manifestos locais; esta seção não apresenta como executada antecipadamente a Etapa C. Nenhuma mudança funcional adicional, política de credenciais, banco real, push, PR, merge ou deploy foi autorizada ou realizada por esta organização.

# 01 — Produto e arquitetura: o que existe de verdade

Análise seletiva em 31/10/2026. Os caminhos são relativos à raiz do repositório. Este documento distingue implementação, documentação operacional e capacidade comercial validada. Nenhuma funcionalidade foi implementada nesta tarefa.

## 1. Resumo verificável

**FATO CONFIRMADO NO CÓDIGO:** aplicação web com backend FastAPI, SQLAlchemy e Pydantic; frontend HTML/CSS/JavaScript com ES Modules. O modelo é uma instalação por barbearia. O núcleo não depende de um identificador de tenant para separar clientes comerciais. Cada instalação deve usar banco e configuração próprios.

**FATO DOCUMENTADO:** README descreve origem acadêmica e operação por instalação; `docs/REUTILIZACAO_E_ATUALIZACAO.md` orienta checkouts, domínios, credenciais e bancos separados. Isso não comprova a existência de clientes pagantes, receita ou operação em produção.

Fluxo principal: visitante conhece a barbearia e serviços → cadastra conta/login → escolhe serviço, profissional e horário disponível → reserva → consulta histórico → cancela/reagenda conforme regras → avalia atendimento concluído. Equipe acompanha agenda; administrador mantém serviços, vínculos, horários, informações e relatórios.

## 2. Inventário com evidências

| Capacidade | Evidência inspecionada | Benefício possível e limite |
|---|---|---|
| Catálogo público com preço/duração/descrição | `routers/services.py`, `schemas/service.py`; `frontend/pages/catalog.html` | Antecipar dúvidas; não é catálogo de estoque de produtos. |
| Informações institucionais editáveis | `routers/institucional.py`; `admin_management.js`; `home.js` | Manter contatos/endereço/horários públicos; depende de preenchimento correto. |
| Identidade por instalação | `installation-config.mjs`, `installation.css`, `installation-brand.mjs` | Nome, logo, textos e tokens visuais; alterações funcionais não são simples tema. |
| Cadastro/login e perfis | `routers/auth.py:register_user/login_user`; `models/user.py:RoleEnum` | Cliente, barbeiro e admin com permissões distintas. Cadastro público sempre cria cliente. |
| Sessões e recuperação de senha | `routers/auth.py:refresh_session/esqueci_senha/redefinir_senha`; `core/email.py` | Refresh rotativo e recuperação por SMTP/Brevo; entrega externa ainda exige teste operacional. |
| Disponibilidade por profissional/serviço/data | `routers/appointments.py:get_available_slots`; `booking.py` | Respeita jornada, duração, bloqueios e reservas ativas. Não elimina erros de agenda mantida fora do sistema. |
| Proteção contra conflito de reserva | `booking.py:lock_barber_for_booking/validate_booking_slot` | Lock PostgreSQL por profissional; SQLite usa transação imediata. Capacidade sob carga ainda não foi medida aqui. |
| Histórico, cancelamento e reagendamento | `routers/appointments.py:get_user_appointments/update_appointment` | Cliente controla próprias reservas conforme limites; não é política livre por instalação. |
| Agenda administrativa e do barbeiro | `routers/admin.py:get_agenda_by_date/get_my_agenda_by_date` | Admin vê agenda geral; barbeiro vê a própria. |
| Reserva manual pela equipe | `routers/admin.py:create_manual_appointment` | Aceita cliente cadastrado ou nome avulso sem conta, conforme schema; barbeiro reserva para si, admin escolhe profissional. |
| Serviços, vínculo com profissional e horários | `routers/services.py`, `barbeiro_servico.py`, `horario.py` | Admin configura oferta; barbeiro administra seus horários/bloqueios nas permissões existentes. |
| Registro do atendimento e estados | `booking.py:ALLOWED_APPOINTMENT_STATUS_TRANSITIONS`; `appointments.py` | Confirmar/concluir/falta/cancelamento; depende da disciplina da equipe. |
| Avaliações e moderação | `appointments.py:create_avaliacao/get_avaliacoes`; `admin.py:toggle_avaliacao_oculta` | Avaliação vinculada ao atendimento e publicação filtrada; não importar reputação de outros canais. |
| Relatório e CSV | `admin.py:get_financial_report/export_financial_report_csv`; `financeiro_admin.js` | Total e ticket de concluídos/avaliados, por serviço/profissional/dia. Não é conciliação de pagamentos ou contabilidade. |
| Dados pessoais e exclusão | `users.py:exportar_meus_dados/export_pdf/excluir_minha_conta` | JSON/PDF do titular e anonimização autenticada; não equivale à exportação integral do negócio. |
| Auditoria e observabilidade | `core/audit.py`, `core/observability.py`, `main.py` | Histórico operacional, health/readiness e métricas; coleta, alertas e retenção externos exigem configuração. |

## 3. Regras que afetam a venda e o suporte

**FATO CONFIRMADO NO CÓDIGO:** `booking.py` define janela de 14 dias e intervalos de oferta de horários de 30 minutos. A disponibilidade exige perfil cliente ou admin; a matriz documental lista também barbeiro, mas a dependência atual de `get_available_slots` o exclui. Ao explicar comportamento, prevalece o código, sujeito à validação de execução.

Cliente deve respeitar antecedência de 24 horas para reagendar/cancelar conforme tratamento em `appointments.py`; reagendamento tem teto de duas alterações. A equipe tem permissões próprias. Não anunciar que toda regra é configurável pelo dono: constantes de negócio e validações estão no core. Na descoberta, perguntar se esses limites se encaixam na operação antes de fechar.

Cadastro exige e-mail, senha, nome e aceite. A necessidade de conta pode aumentar desistência em comparação com agenda por mensagem; isso é **HIPÓTESE**, a medir no fluxo real. Confirmação de propriedade do e-mail está tratada como evolução na documentação, não como recurso já disponível.

O cadastro público cria somente cliente. Não foi encontrada rota de criação de barbeiro na superfície inspecionada de `users.py`; o painel lista profissionais e gerencia vínculos, jornadas e bloqueios, mas isso não comprova CRUD completo da equipe. **RECOMENDAÇÃO:** fechar procedimento seguro de provisionamento de profissionais antes de vender autonomia total ao dono; não usar seed de desenvolvimento em produção.

## 4. Arquitetura e dados

`backend/app/models/user.py` reúne usuários, serviços, reservas, avaliações, instituição, jornadas, bloqueios, vínculos, tokens de recuperação, consentimentos, refresh tokens, tentativas de login e auditoria. Reservas preservam informações de preço/duração, evitando depender apenas do catálogo atual. Relatórios usam valor cobrado quando presente e preço como fallback; valores registrados não provam dinheiro recebido.

SQLite atende desenvolvimento/testes; a documentação direciona produção a PostgreSQL. Revisões Alembic estão em `backend/alembic/versions/`, incluindo `20261031_01_email_identity.py`. O startup não deve criar tabelas nem aplicar migração silenciosa. `/ready` verifica schema esperado; um serviço pode estar vivo e indisponível por falta de migração.

**FATO CONFIRMADO NO CÓDIGO:** marca fica parcialmente em arquivos de configuração; contatos e oferta ficam no banco. **RECOMENDAÇÃO:** manter essa separação, sem transformar cada novo contrato em fork funcional. Ver arquivo 06 para desenho futuro; não há plataforma central de frotas pronta demonstrada nesta análise.

## 5. Segurança: capacidades e limites

Autorização por papel e propriedade, hashing de senha, JWT, refresh, rate limiting e configurações de produção têm implementação e testes identificados. `main.py` desativa documentação interativa em produção e aplica controles de host; não interpretar existência desses controles como auditoria completa.

`docs/REQUISITOS_STATUS.md` registra access token em localStorage e risco XSS. CSP de frontend no `render.yaml` está limitada a `frame-ancestors 'none'`, com outros cabeçalhos separados; não é CSP restritiva completa de scripts. Permissões mínimas, dependências externas e fronteira de proxy precisam ser validadas no ambiente escolhido.

A exclusão anonimiza conta e trata relações; não elimina automaticamente todos os backups já produzidos. PDF tem limite de caracteres, com JSON como alternativa preservadora. Isso pode gerar dúvidas de suporte e exige explicação na política de dados.

## 6. Deploy, testes e lacunas operacionais

**FATO CONFIRMADO NO CÓDIGO:** `render.yaml` atual contém API, frontend estático e PostgreSQL em configuração gratuita de homologação; `/ready` é health check. Não há `preDeployCommand` aplicando Alembic nesse arquivo atual. A configuração usa produção para controles da aplicação, o que não transforma o plano de infraestrutura em serviço de produção validado.

O registro histórico de requisitos cita preparação com pre-deploy, mas uma atualização posterior e o YAML atual indicam processo gratuito sem esse comando. Não prometer migração automática já pronta. `FORCE_HTTPS=false` no Blueprint depende da terminação TLS na borda; não copiar para VPS sem revisar cadeia de proxy e redirecionamento.

CI em `.github/workflows/ci.yml`: testes Python SQLite e PostgreSQL de serviço descartável, Node, auditorias de dependências e Playwright Chromium/Firefox/WebKit. Arquivos `test_booking_integrity.py`, `test_authorization.py`, `test_schema_migrations.py`, `test_installation_isolation.py` e E2E dão evidências de intenção de cobertura. Resultados históricos registrados em docs não são resultados desta análise. Nenhuma suíte ou banco foi executado aqui.

`tools/new-installation/create.py` já cria árvore limpa e exclui dados/segredos/branding original, mas não provisiona automaticamente infraestrutura, DNS, SSL e toda a equipe. Seu template de configuração precisa passar pela validação atual de produção; por exemplo, o código de produção exige hosts permitidos. Um gerador existente não implica implantação comercial em minutos hoje.

Scripts de backup e procedimento existem em `tools/backup/` e `docs/PLANO_RECUPERACAO_DESASTRES.md`. RPO de 24h e RTO de 4h são metas documentadas, sem recuperação real comprovada neste levantamento. Monitoração depende de serviço/host externo; métricas por processo reiniciam junto com o worker.

## 7. O que não vender como implementado

Não foram identificadas, na superfície de modelos, rotas, frontend e documentação relevante inspecionada: automação oficial de WhatsApp, lembretes de reserva, checkout/Pix integrado, cobrança recorrente do seu serviço, estoque, comissões, emissão fiscal, aplicativo nativo ou painel central de todas as instalações. Isso é limite do levantamento, não prova matemática de ausência em todo arquivo do repositório.

Link de contato do WhatsApp não é envio automático. Recuperação por e-mail não é campanha ou lembrete de atendimento. Relatório financeiro não é ERP. Exportação do titular não é migração de toda a base. Domínio próprio não transfere propriedade intelectual do software ao contratante.

## 8. Consequências comerciais

Facilitam venda: jornada visível no celular, marca configurável, site com catálogo, agenda da equipe, relatórios e implantação assistida possível. Dificultam: concorrentes com muitas funções a baixo preço, cadastro antes da reserva, regras ainda fixas, provisionamento de equipe a resolver e prontidão externa por validar.

**HIPÓTESE:** o melhor comprador inicial prefere alguém que configure e acompanhe a adoção a uma longa lista de módulos. **RECOMENDAÇÃO:** validar com demonstração e pagamento, não somente elogios ao visual.

## DADOS QUE PRECISAMOS MEDIR

Conclusão do cadastro/reserva, consultas que geram dúvida, tempo de provisionamento de equipe, carga PostgreSQL, entrega real de e-mail, recuperação real de backup, erros por dispositivo e uso da agenda pela equipe. Antes disso, não declarar escalabilidade comprovada, eliminação de faltas ou produto totalmente pronto para produção.

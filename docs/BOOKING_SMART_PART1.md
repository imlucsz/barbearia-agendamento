# Agendamento inteligente — Parte 1

Base eaa942a (main com etapa 2 integrada), branch feat/booking-smart-part1.
Sem publicação, alterações Render, dependências novas ou migrações.

## Comportamento
GET autenticado /appointments/calendario?service_id=…&barbeiro_id=… retorna
hoje até +14 dias, com date/working/status/slots. Estados: off (sem jornada),
blocked (bloqueios cobrem toda a jornada), full (com jornada, sem slot que comporte
o serviço) e available. A janela termina no instante exato de agora +14 dias,
não ao final do último dia. Todos os cálculos usam America/Sao_Paulo.

JornadaTrabalho é individual. BloqueioHorario contém folgas, exceções, feriados
cadastrados e intervalos. Não inferimos expediente a partir do texto institucional.
Não há cadastro separado de feriados nacionais nem calendário externo.
Jornadas múltiplas no mesmo dia são períodos separados: manhã e tarde são
oferecidas, sem permitir que um serviço atravesse o intervalo. Corrigida a
divergência anterior entre a primeira jornada na gravação e a última na leitura.

/disponiveis mantém o formato de lista anterior e compartilha a mesma projeção.
Ambos rejeitam profissionais bloqueados/inativos ou não associados ao serviço.
Até cinco consultas carregam a janela, sem consultas por dia/slot; histórico de
reservas é limitado à janela mais um dia (duração contratual máxima: 1440 minutos).
Motivos de bloqueios e identidades de clientes não são retornados.

O calendário usa botões nativos, rótulos de estado, disabled e aria-pressed.
Sem expediente/bloqueio integral não são selecionáveis; full permite consultar
alternativas. Serviço/profissional novos limpam a seleção. Respostas atrasadas,
inclusive falhas, são descartadas por versão. Até três sugestões posteriores
usam slots reais da mesma janela, sem requests extras por sugestão. Selecionar
uma data/sugestão reconsulta /disponiveis; atualização manual permite renovar
a janela. A consulta é uma fotografia, nunca uma reserva de vaga.

Reagendamento passa appointment_id opcional nos dois endpoints: verifica dono
ou administrador e serviço/profissional originais, usa duração snapshot e exclui
o próprio agendamento. A API de gravação continua validando sob lock de barbeiro:
expediente, duração, bloqueios, sobreposição, janela, antecedência de 24 horas,
limite de dois reagendamentos e snapshots. Teste rejeita reagendamento em dia
sem expediente e confirma que data/reschedule_count não mudam.

## Entradas e XSS
Nenhuma execução de XSS foi demonstrada nos caminhos revisados. Serviço,
descrição, profissional, comentário, texto institucional e cliente administrativo
foram exercitados no Chromium com payloads literais: sem criação de img/script/svg
do payload e sem execução. Catálogo/cliente usam textContent/criação DOM;
templates administrativos usam escapeHtml centralizado. IDs/tipos numéricos são
validados na API; URLs de contato/logo/mapas já possuem validadores próprios.
Mensagens de erro usam texto; CSP não foi relaxada.

Schemas mantêm texto legítimo (acentos, aspas, &, < e >), limites de tamanho e tipos.
Testes cobrem igualdade criação/atualização de serviços, limites de duração/preço,
comentários e rejeição de javascript/data/credenciais em URLs institucionais.
O teste institucional de navegador usa resposta controlada; os demais payloads
de serviços/profissionais/clientes/avaliações são persistidos na fixture local.
Isso valida os sinks revisados, não constitui auditoria completa de todo o produto.

## Reprodução
Usar um Python existente com backend/requirements.txt instalado (nenhuma instalação
é feita pelos runners). Comandos a partir deste worktree:

- Em backend: python -m unittest discover -s tests -p "test_booking*.py" -q
- Em backend: python -m unittest discover -s tests -p test_authorization.py -q
- Em backend: python -m unittest discover -s tests -p test_schema_validation.py -q
- node --test frontend/tests/*.test.mjs
- python tools/run-booking-postgres.py
- Definir PYTHON com o executável do venv e executar:
  npx --no-install playwright test --config frontend/e2e/booking-smart.config.mjs

O runner PostgreSQL exige Docker já disponível e imagem postgres:16-alpine local;
usa --pull never, porta aleatória em 127.0.0.1, senha temporária em memória, banco
booking_test e container/volumes exclusivos removidos em finally. Recusa compartilhar
o container de testes preexistente. Os testes verificam a identidade e criam schemas
exclusivos antes de usar PostgreSQL.

O runner Chromium inicia booking-smart-server.py em 127.0.0.1:4186, migra SQLite
temporário via Alembic e usa apenas dados fictícios. booking-smart-browser.mjs também
é executável com uma Page Playwright existente. Nenhum token é impresso.

## Evidências desta execução
- Python 3.14.7, FastAPI 0.162.0, Pydantic 2.14.1 do venv existente.
- SQLite: 44 testes de booking +14 autorização +5 schemas = 63 aprovados, zero ignorados/falhos.
- PostgreSQL 16.15: 36 testes realmente usando PostgreSQL, incluindo sessões
  HTTP independentes e barreiras na concorrência. Os cinco testes legados de migração
  usam SQLite e os três de inputs são validação pura: não contam como PostgreSQL.
- Node: 56 aprovados, zero falhos/ignorados.
- Chromium 156.0.8078.48: 29 verificações reais, desktop e mobile 390px, teclado,
  cookie/login, slots, duração, sugestões, respostas invertidas, erro/retry e XSS.
- Revisão independente: P2 de leitura histórica ilimitada corrigido; revisão posterior
  sem outro bug concreto. graphify update . executado somente neste worktree.

A configuração Playwright dedicada ficou persistida, mas a CLI @playwright/test não
está instalada neste worktree/cache. A execução real usou o Chromium/Playwright já
disponível no conector e a função persistida, com backend real. A suíte geral antiga
não foi repetida; suas três seleções de data foram adaptadas ao novo calendário.
O CI executará a configuração dedicada antes da suíte geral; isso ainda precisa
ser confirmado na futura publicação autorizada da branch.
A falha preexistente de response.json durante navegação não foi investigada nem
usada para ignorar falhas novas. Falhas intermediárias de fixture (.test no email,
seletores antigos) foram corrigidas e a rodada final passou.

Pendências: repetir CI com pins exatos (requirements declara Pydantic 2.14.2),
suíte geral de navegador, outros motores e validação publicada em implantação
futura autorizada. Sem garantia de vaga entre leitura e confirmação; concorrência
é resolvida pela API. Dados legados fora do contrato de duração exigem revisão
específica antes de usar a projeção limitada.

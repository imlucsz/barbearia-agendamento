# Parte 1 — disponibilidade e entradas

Base: origin/main eaa942a; branch/worktree exclusivos. Autonomia técnica conforme pedido.

## Decisão
Reutilizar validate_slot_against_loaded_data e a consulta em lote de disponibilidade.
Adicionar GET /appointments/calendario (autenticado, profissional/serviço obrigatório,
somente hoje até +14 dias), mantendo /disponiveis compatível. Até cinco consultas de
leitura por janela, sem chamadas por dia; a gravação continua validando sob lock.
Cada dia informa expediente, bloqueio integral, slots e estado. Folgas/feriados
cadastrados são BloqueioHorario; não inventar calendário externo.

O date nativo não desabilita dias individuais: substituí-lo por botões de datas
com disabled, aria-pressed e rótulo de estado. Mostrar dias sem expediente e sem vagas
separadamente; até três sugestões futuras derivadas da mesma janela. Seleções e
respostas antigas não sobrevivem à troca de contexto; reconsultar o dia ao selecionar.
Preservar fluxo de páginas e reagendamento, CSP e texto seguro.

Alternativas: consultas de /disponiveis por dia multiplicam requests e não distinguem
expediente; calendário externo acrescenta dependência sem necessidade.

## Execução e aceite
- [x] Testes de calendário falhando, incluindo bloqueio integral, lotação, duração e janela.
- [x] Extrair leitura compartilhada; endpoint limitado; manter regras e locks existentes.
- [x] Calendário/sugestões e testes Node para corrida/limites; regressão Chromium real.
- [x] Revisar sinks/URLs e schemas dos dados solicitados; corrigir apenas caminhos comprovados.
- [x] Python temporal/integridade/autorização, Node e Chromium; PostgreSQL só descartável.
- [x] Atualizar README/status/evidências, diff check, revisão e commit local seletivo.

Revisão: limite histórico corrigido; projeção de reagendamento preserva snapshot/
ownership; jornadas múltiplas antes divergiam entre leitura/escrita, agora validadas
como períodos independentes. Evidência detalhada em docs/BOOKING_SMART_PART1.md.

Sem schema/migração, dependências novas, produção, Render, push ou PR.

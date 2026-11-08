# Benchmark de horários disponíveis (RNF-08)

Executado com `python tools/bench_disponiveis.py` a partir de `backend`, usando SQLite em diretório temporário. O script cria dados fictícios para cinco barbeiros, jornadas para todos os dias, cinco bloqueios e 500 agendamentos futuros; executa 100 chamadas ao handler `get_available_slots` e conta SELECTs SQLAlchemy por chamada. O handler é medido diretamente, sem rede, autenticação e serialização HTTP. Não houve conexão com banco local, de desenvolvimento ou produção.

| Medida | Antes (consulta slot a slot) | Depois (leituras em lote) |
|---|---:|---:|
| p50 | 240,71 ms | 12,93 ms |
| p95 | 286,26 ms | 14,72 ms |
| máximo | 314,62 ms | 46,73 ms |
| SELECTs por chamada | 442 | 5 |

Os números são uma referência reproduzível neste ambiente, não uma garantia para qualquer hardware ou banco. A medição PostgreSQL não foi executada: `BOOKING_TEST_POSTGRES_URL` não estava configurada. O script só aceita banco PostgreSQL explicitamente nomeado `*_test` em localhost e opera dentro de schema descartável.

A reserva e a consulta de disponibilidade compartilham `validate_slot_against_loaded_data` em `backend/app/booking.py`. `test_booking_temporal.py` compara os slots resultantes com a validação individual legada em cenários de jornada parcial, bloqueio, conflito, duração longa e limite de 14 dias. `test_booking_integrity.py` mantém os testes de não-overbooking concorrente.

# 04 — Precificação, unit economics e planilha conceitual

Todos os números deste arquivo são **SIMULAÇÕES em reais**, data-base 31/10/2026. Não são impostos apurados, capacidade comprovada ou previsão de lucro. Validar tributação com contador. O custo da sua hora existe mesmo se você ainda não retirar dinheiro.

## 1. Dicionário e fórmulas

| Métrica | Como calcular neste negócio | Cuidado |
|---|---|---|
| MRR | Soma das mensalidades recorrentes normalizadas dos contratos ativos | Implantação e projeto avulso não entram. Anuidade deve ser dividida por 12. |
| ARR | MRR × 12 | Receita anualizada, não receita histórica nem recebimento garantido. |
| Ticket médio comercial | Receita de contratos fechados / contratos, no período e escopo definidos | Não confundir com ticket dos cortes do cliente. |
| ARPU | MRR / clientes pagantes ativos | Usar unidade “barbearia/instalação”; não usuários finais. |
| CAC | Despesas de aquisição + horas comerciais valorizadas / novos clientes pagos atribuídos | Usar parênteses: (despesas + custo das horas) / clientes. Sem vendas, não dividir por zero. |
| Churn de clientes | Cancelados no mês / clientes ativos no início | Separar pausa, inadimplência e cancelamento; registrar motivo. |
| Churn de receita | MRR perdido da base inicial / MRR inicial | Separar expansão e contração. Novos clientes não escondem churn. |
| Custo de suporte | Horas efetivas × custo/hora + ferramentas atribuíveis | Registrar duração, categoria e cliente, sem dados sensíveis. |
| Margem bruta gerencial | (Receita − custos diretos de entregar serviço) / receita | Definir tratamento consistente de taxas e tributos. Contabilidade pode classificar diferente. |
| Margem de contribuição | Receita − custos variáveis/degrau alocados segundo modelo | Financia estrutura fixa, produto, vendas e remuneração. |
| LTV simplificado | ARPU × margem de contribuição percentual / churn mensal | Só com base estável e churn > 0; não é infinito quando não há cancelamento observado. |
| Payback de CAC | CAC / contribuição mensal por cliente | Sem contribuição positiva não há retorno desse modelo. |
| Ponto de equilíbrio | Custos fixos / contribuição unitária, arredondado para cima | Recalcular se servidor/equipe crescem em degraus. |

Use definições fixas no controle: neste pacote, “margem bruta” inclui entrega direta (infraestrutura, terceiros e suporte), antes de taxas percentuais e tributos; “contribuição” desconta também essas taxas. Isso evita comparar margens calculadas de formas diferentes.

```text
margem em R$ por cliente = P − I − T − P×t − H×Vh
P = mensalidade; I = infraestrutura atribuída; T = terceiros não incluídos em I
t = impostos/taxas percentuais; H = horas médias de suporte; Vh = custo/hora
margem % = margem em R$ / P
resultado operacional gerencial = soma das contribuições − custos fixos não alocados
preço mínimo para contribuição-alvo m = (I + T + H×Vh) / (1 − t − m)
```

O denominador precisa ser positivo. Gateway com taxa fixa deve ser somado em T; não aplicar duas vezes. Se infraestrutura já foi rateada por cliente, não subtrair novamente o mesmo servidor nos custos fixos.

## 2. Seis mensalidades, mesmas premissas

**SIMULAÇÃO A:** infraestrutura marginal/alocada I = R$ 25 por cliente, terceiros T = R$ 5, suporte H = 0,5h/mês a R$ 40/h, tributos + taxas t = 8%. Logo custo direto antes de taxas = R$ 50. Essas premissas são um exercício de operação compartilhada, não equivalem a Render dedicado e não asseguram que R$ 25 cubra servidor real.

| P | Receita por cliente | Infra | Terceiros | Suporte | Taxas 8% | Margem bruta R$ / % | Contribuição R$ / % | Clientes para cobrir F=R$1.500 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 99 | 99 | 25 | 5 | 20 | 7,92 | 49 / 49,5% | 41,08 / 41,5% | 37 |
| 149 | 149 | 25 | 5 | 20 | 11,92 | 99 / 66,4% | 87,08 / 58,4% | 18 |
| 199 | 199 | 25 | 5 | 20 | 15,92 | 149 / 74,9% | 133,08 / 66,9% | 12 |
| 249 | 249 | 25 | 5 | 20 | 19,92 | 199 / 79,9% | 179,08 / 71,9% | 9 |
| 299 | 299 | 25 | 5 | 20 | 23,92 | 249 / 83,3% | 225,08 / 75,3% | 7 |
| 399 | 399 | 25 | 5 | 20 | 31,92 | 349 / 87,5% | 317,08 / 79,5% | 5 |

F é estrutura adicional não incluída nos custos diretos: reserva de trabalho de produto, administração e ferramentas fixas, por exemplo. Não representa orçamento real nem remuneração suficiente do fundador. O preço mais alto também pode reduzir conversão; tabela financeira não prova disposição de pagar.

Com P=199, I=100 e H=2h a R$40, mantendo T=5 e t=8%, contribuição cai a **−R$1,92**. O mesmo preço pode ser bom ou inviável conforme infraestrutura e suporte. Para contribuição de 50%, o preço mínimo com custo direto de 50 é 50/(1−0,08−0,50)=R$119,05; isso ainda precisa pagar F e aquisição.

## 3. Oito tamanhos de carteira

**SIMULAÇÃO B:** repetir P=199 e contribuição unitária de R$133,08 da simulação A, F=1.500. Extrapolação matemática, não recomendação de capacidade. Nenhuma instalação foi testada para 100 clientes comerciais. Custos em degrau e contratação de suporte devem substituir o modelo quando aparecerem.

| Clientes | MRR | ARR anualizado | Entrega direta (50×N) | Margem bruta | Taxas | Contribuição | Suporte h/mês | Resultado após F |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 199 | 2.388 | 50 | 149 | 15,92 | 133,08 | 0,5 | −1.366,92 |
| 3 | 597 | 7.164 | 150 | 447 | 47,76 | 399,24 | 1,5 | −1.100,76 |
| 5 | 995 | 11.940 | 250 | 745 | 79,60 | 665,40 | 2,5 | −834,60 |
| 10 | 1.990 | 23.880 | 500 | 1.490 | 159,20 | 1.330,80 | 5 | −169,20 |
| 20 | 3.980 | 47.760 | 1.000 | 2.980 | 318,40 | 2.661,60 | 10 | 1.161,60 |
| 30 | 5.970 | 71.640 | 1.500 | 4.470 | 477,60 | 3.992,40 | 15 | 2.492,40 |
| 50 | 9.950 | 119.400 | 2.500 | 7.450 | 796,00 | 6.654,00 | 25 | 5.154,00 |
| 100 | 19.900 | 238.800 | 5.000 | 14.900 | 1.592,00 | 13.308,00 | 50 | 11.808,00 |

Resultado acima não inclui novo CAC, implantação, juros, inadimplência ou custos não previstos em F; portanto, não chamar de lucro líquido. Receita é venda; recebimento é caixa; margem remunera os custos ainda restantes. Trabalho já valorizado no suporte não deve ser cobrado novamente como custo idêntico do fundador, mas suas horas de vendas/produto precisam entrar em algum lugar.

## 4. Implantação e aquisição

```text
custo de onboarding = horas × custo/hora + despesas diretas + terceiros
preço de implantação = custo de onboarding / (1 − taxas − margem desejada)
onboarding não recuperado = max(0, custo − receita líquida da implantação)
payback econômico inicial = (CAC + onboarding não recuperado) / contribuição mensal
```

**SIMULAÇÃO:** 8h × R$40 + R$40 de despesa = R$360. Implantação de R$600, após taxa de 8%, deixa R$552 e saldo de R$192 sobre esse custo. A taxa de implantação é receita não recorrente e demanda trabalho; não somá-la ao MRR. Se vender sem implantação, os R$360 precisam de financiamento e recuperação futura.

CAC fictício: R$200 de despesas + 10h comerciais a R$40 = R$600 para três clientes pagos: CAC de R$200. Com contribuição de 133,08, payback de CAC ≈1,50 mês; sem implantação e onboarding de R$360 não recuperado, ≈4,21 meses. Calcular também recuperação de caixa se as horas não geraram desembolso: são perspectivas diferentes.

## 5. LTV, churn e limites da amostra

Com churn mensal hipotético de 3% e contribuição de R$133,08, LTV simplificado ≈R$4.436. LTV/CAC com CAC de R$200 ≈22,18. Um índice muito alto com poucos clientes pode refletir premissas otimistas, horas omitidas e retenção desconhecida. Não usá-lo para justificar expansão imediata.

Um cancelamento em três clientes equivale a 33,3% naquele denominador, mas não estima bem o mercado. Zero cancelamentos em 60 dias não comprova vida útil infinita. Acompanhar coortes por mês de entrada, retenção em 30/60/90 dias, MRR perdido e motivo. O modelo 1/churn supõe risco constante e ignora desconto temporal; em base jovem, preferir contribuição acumulada observada e cenários de permanência de 6, 12 e 24 meses.

## 6. Planilha conceitual: campos e fórmulas

Uma aba de parâmetros guarda moeda, custo/hora, alíquotas estimadas e data. Uma aba por cliente guarda preço, início, plano, horas e custos. Uma aba mensal agrega resultados. Usar apenas identificadores internos; não enviar planilha identificável para IA de estudo.

| Campo | Entrada ou fórmula |
|---|---|
| Clientes iniciais / novos / cancelados / finais | finais = iniciais + novos − cancelados |
| Mensalidade / descontos | Preço contratual; desconto temporário com término |
| MRR | Soma do recorrente normalizado, após descontos vigentes |
| Infraestrutura | Custo do pool real + dedicados; escolher rateio OU lançamento total |
| Domínios | Despesa anual / 12, se você paga; não esquecer obrigação de renovação |
| E-mail / monitoramento / backup | Valores reais atribuíveis, com mínimos e excedentes |
| Gateway | Receita efetivamente cobrada × percentual + transações × taxa fixa |
| Impostos | Base tributável × alíquota aplicável validada; pode diferir do caixa |
| Horas de suporte | Soma de minutos / 60; separar bug/dúvida/configuração |
| Custo do suporte | Horas × custo/hora + contratação externa |
| CAC | (Gastos comerciais + horas valorizadas) / clientes novos atribuídos |
| Margem | Receita − entrega − taxas/tributos segundo definição adotada |
| Fixos e resultado | Contribuição − fixos − despesas adicionais do período |
| Caixa | Recebimentos − pagamentos; separar provisões e investimentos |
| Inadimplência | Valores vencidos / valores devidos; acompanhar recuperação |

Não tirar média simples das margens percentuais de planos de tamanhos diferentes: somar valores e dividir pela receita total. Uma conta paga pelo cliente diretamente pode ficar fora da sua despesa, mas registrar a dependência operacional.

## 7. Cenários integrados

**SIMULAÇÕES independentes**, com t=8%, custo/hora=R$40; infraestrutura já por cliente; F=R$1.500 adicional. Churn/CAC são entradas hipotéticas, não projeções.

| Cenário | N / P | Infra / terceiros | Suporte por cliente | MRR | Contribuição total | Resultado após F | CAC / churn mensal |
|---|---|---|---|---:|---:|---:|---|
| Conservador | 5 / 149 | 60 / 5 | 1,5h = 60 | 745 | 60,40 | −1.439,60 | 400 / 6% |
| Base a validar, chamado “realista” apenas para planejamento | 10 / 199 | 25 / 5 | 0,5h = 20 | 1.990 | 1.330,80 | −169,20 | 200 / 3% |
| Otimista | 20 / 249 | 20 / 5 | 0,25h = 10 | 4.980 | 3.881,60 | 2.381,60 | 150 / 1,5% |

Nada comprova que o cenário base seja o mais provável. Se adquirir três clientes no mês base, subtrair mais R$600 de aquisição, caso ainda não esteja no F; contabilizar implantação separadamente. Não usar o cenário otimista para assumir dívida.

## 8. Sensibilidade e critérios de decisão

Em P=199, cada hora adicional a R$40 reduz contribuição em R$40; em 20 clientes, +1h por cliente consome R$800/mês. Um aumento de R$20 em infraestrutura por cliente consome R$400 nessa carteira. Cinco pontos percentuais extras de taxas consomem R$199 sobre MRR de R$3.980. Pequenos desvios se acumulam.

Defina piso de contribuição e teto de horas antes de vender. Se personalização elevar custo permanente, reajustar preço/escopo antes de aceitar. Se demanda não sustenta o preço mínimo, mudar entrega ou ICP; vender abaixo do custo não é validação de negócio saudável.

## DADOS QUE PRECISAMOS MEDIR

Custo por pool, despesas em moeda estrangeira, taxa efetiva, minutos de suporte, onboarding ativo, CAC por canal, atraso de pagamento, churn e expansão por coorte. Revisar mensalmente e substituir hipóteses por valores com origem e período.

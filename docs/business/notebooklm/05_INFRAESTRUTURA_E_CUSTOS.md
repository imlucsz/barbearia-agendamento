# 05 — Infraestrutura, preços e redução de custos

Data das consultas: **31/10/2026**. Preços públicos são referências, não contratos ativos. As estimativas em BRL abaixo não usam cotação cambial atual: quando houver conversão exemplificativa, a taxa é explicitamente fictícia.

## 1. Ponto de partida e método

**FATO CONFIRMADO NO CÓDIGO:** API Python e frontend estático permitem hospedagem separada; `render.yaml` descreve homologação gratuita com PostgreSQL. **FATO DOCUMENTADO:** produção por instalação com banco exclusivo. Não há razão comercial demonstrada para reescrever como multi-tenant antes de vender.

Compare **custo total de operação**, não só servidor: compute + banco + disco + tráfego + IP + backup externo + domínio + e-mail + logs + monitor + trabalho + reserva para incidentes. Custo baixo com seis horas extras de operação pode sair caro. Contrato com cliente deve indicar quem paga cada serviço e quem controla a conta.

## 2. Registro de preços oficiais

| Fonte pública / URL | Moeda e referência consultada | Natureza / ressalva |
|---|---|---|
| [Render — artigo oficial de custos](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses) | USD; artigo cita aproximadamente US$13/mês para Starter web + Basic-256mb Postgres em julho de 2026 | Referência histórica dentro de página oficial, não cotação atual garantida. Armazenamento/tráfego/crescimento adicionais. |
| [Render — preços](https://render.com/pricing) e [compute plans](https://render.com/docs/compute-plans) | USD; tabela monetária dinâmica não foi extraída com segurança nesta análise | Reconfirmar plano/recursos no painel; nomenclaturas de compute mudaram. Não tratar US$13 como orçamento aprovado. |
| [Render — gratuito](https://render.com/docs/free) | USD 0 para ofertas gratuitas, com limites | A própria documentação orienta não usar instâncias gratuitas para aplicações de produção. Frontend estático tem oferta gratuita sujeita a quotas. |
| [DigitalOcean — Droplets](https://www.digitalocean.com/pricing/droplets) | USD/mês, Basic regular: 1GiB/1vCPU US$6; 2GiB/1vCPU US$12; 4GiB/2vCPU US$24; 8GiB/4vCPU US$48 | Preço de tabela exibido, não promoção. Não inclui todos os custos do negócio; configurações são referências, não dimensionamento comprovado. |
| [Cloudflare — Free](https://www.cloudflare.com/plans/free/) | USD 0 para plano Free | Serviço de borda com condições; adicionais pagos existem. Não substitui host FastAPI/PostgreSQL. |

Não foi cotado domínio, WhatsApp, gateway ou serviço jurídico específico. Para esses itens, os valores financeiros são parâmetros até orçamento. Nenhum gasto foi realizado nesta tarefa.

**SIMULAÇÃO de câmbio**, para estudar sensibilidade: se USD custasse R$5,50, US$24 corresponderia a R$132 antes de encargos; a R$6,50, R$156. Não são cotações vigentes. Fórmula: custo BRL = custo estrangeiro × câmbio efetivo + encargos aplicáveis. Usar custo do pagamento efetivo na apuração.

## 3. Alternativas comparadas

As opções se combinam: Docker é embalagem/processo, PostgreSQL é banco, Cloudflare é borda. Não somar todos como fornecedores obrigatórios.

| Opção | Custo aproximado de planejamento | Complexidade / isolamento | Backup e manutenção | Escala e risco |
|---|---|---|---|---|
| A. Render por cliente | Referência oficial histórica ~US$13/cliente/mês, mais extras; recotar | Baixa/média; serviços e bancos distintos por cliente | Plataforma reduz operação de host; ainda precisa testar restore e separar segredos | Custo cresce por instalação; dependência de fornecedor e região. |
| B. VPS compartilhada sem containers | Referências US$12–48/mês por VM, mais extras | Alta responsabilidade; processos/usuários separados, isolamento mais manual | Você mantém SO, Python, PostgreSQL, proxy e backups | Rateio melhora com ocupação; falha de host afeta o grupo. |
| C. Docker com múltiplas instalações | Custo da VPS + registro/CI se exceder franquias; reserva fictícia de R$0–50/mês para ferramentas iniciais | Média/alta; redes/volumes por cliente, containers não equivalem a VMs | Imagens facilitam repetibilidade; host/volumes e secrets continuam sob sua responsabilidade | Limites de memória/CPU e pools são essenciais. Comprometimento do host pode afetar todos. |
| D. PostgreSQL único com bancos separados | Sem segundo servidor se couber na VPS; custo marginal não é zero | Usuário runtime exclusivo, sem superuser/CREATEDB; revisar CONNECT e grants | Dump/restore de cada banco; upgrade da instância afeta todos | Menor overhead, mas CPU, disco e indisponibilidade compartilhados. |
| E. PostgreSQL em instância separada por cliente | R$80–250/mês por cliente como reserva fictícia, não cotação | Isolamento maior se host/conta também separados; container no mesmo host mantém risco comum | Mais backups, patches, conexões e inventário | Pode caber em plano premium; margem menor se preço não acompanhar. |
| F. Frontend estático | Possível US$0 dentro das quotas, ou custo já coberto pela VPS | Simples; artefato de marca correto por instalação | Guardar versão do artefato; evitar publicar configuração de outro cliente | CDN ajuda assets, não resolve lentidão de consulta ao banco. |
| G. Cloudflare Free | US$0 na oferta básica; domínio/host continuam pagos | DNS, proxy e TLS precisam configuração correta | Não é backup de banco; revisar cache e origem | Não fazer cache de dados autenticados. Erro global de DNS pode afetar carteira. |
| H. Serviços gerenciados | Orçamento fictício R$100–400/instalação/mês conforme conjunto; recotar | Menos operação de plataforma, maior fragmentação de contas e dependências | Confirmar retenção, restauração, região e exportação | Útil quando horas poupadas valem mais que a diferença de preço. |

Estimativas E/H são envelopes amplos de planejamento. Não apresentam comparação de produtos equivalentes e não devem ir para proposta sem cotação. Docker/Compose, Caddy/Nginx e qualquer serviço gratuito têm condições/licenças a verificar no desenho final.

## 4. Rateio e capacidade

**SIMULAÇÃO:** pool de servidor + backups + ferramentas custa R$180/mês: com 1 cliente custa R$180/cliente; 3 → R$60; 5 → R$36; 10 → R$18. Não afirma que dez instalações cabem nesse servidor. A ocupação inicial muda completamente a margem; modelar capacidade ociosa e degraus de expansão.

```text
custo do pool por cliente = custo total do pool / clientes ativos nele
capacidade estimada por RAM = piso((RAM total − SO − proxy − banco − reserva) / RAM de pico por instalação)
capacidade admitida = menor limite medido entre RAM, CPU, conexões, disco, I/O e latência
```

Somar limites de memória de todos os containers, inclusive PostgreSQL e monitoramento. Pool de conexões × workers × instalações pode esgotar banco antes da RAM. A consulta de disponibilidade e relatórios merecem carga representativa com dados fictícios. A capacidade de 100 clientes não pode ser extrapolada de cinco reservas de teste.

## 5. Como economizar em ordem prática

1. **Eliminar trabalho repetido:** oferta padrão, treinamento e uma versão de core. Medir horas poupadas; customização permanente costuma custar mais que disco.
2. **Escolher operação que você domina:** gerenciado pode ser melhor para o primeiro piloto se VPS atrasar vendas e aumentar incidentes.
3. **Compartilhar somente após validar isolamento:** bancos, usuários, volumes, configurações e backups exclusivos mesmo com host comum.
4. **Servir assets estáticos eficientemente:** comprimir imagens, cachear conteúdo público e desativar recurso opcional pesado se não trouxer valor. Widget opcional já tem configuração; não é necessário mexer nesta tarefa.
5. **Criar alertas de custo e limites:** quotas de logs, disco, tráfego, e-mail e retenção. Não depender de franquia gratuita permanente.
6. **Otimizar pelo gargalo medido:** RAM/consulta/índice antes de introduzir cache/Redis sem necessidade. Cache de disponibilidade tem risco de resposta desatualizada.

Não economizar com banco exposto publicamente, backup no mesmo disco apenas, segredo compartilhado, fim dos testes ou patch ignorado. O barato só é bom se a recuperação e a separação continuarem funcionando.

## 6. Decisão por estágio

Para 1–3 pilotos, minimizar tempo até entrega segura; escolher gerenciado ou VPS conforme competência. Para 5–10, medir custo por cliente, automatizar configuração e testar isolamento. Para 20–30, separar pools para limitar impacto de falha e revisar cobertura do operador. Para 50–100, formalizar capacidade, recuperação e equipe antes de vender cobertura maior. São marcos de processo, não limites técnicos medidos.

## DADOS QUE PRECISAMOS MEDIR

RAM/CPU por processo e pool, conexões máximas, p95 por rota, consultas lentas sem conteúdo pessoal, tráfego, armazenamento/mês, tamanho e duração de backup/restore, consumo de e-mail, custo de patch e tempo de atendimento. Escolher região observando latência e requisitos de transferência de dados, com validação profissional quando aplicável.

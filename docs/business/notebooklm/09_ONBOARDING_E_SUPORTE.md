# 09 — Implantação, suporte e retenção

Modelo **RECOMENDADO** para operação individual. Franquias e prazos são propostas para validar, não obrigações já contratadas. Infraestrutura, equipe e cobertura devem permitir cumprir o que for vendido.

## 1. Implantação é um projeto com aceite

Separar coleta de materiais, preparação técnica, validação e ativação. O tempo esperando domínio ou logo não é hora ativa de implantação, mas afeta o prazo percebido; acompanhar ambos. Definir um responsável de cada lado evita pedidos conflitantes de funcionários.

### Checklist de entrada comercial e dados

- [ ] Escopo, preço, pagamento, suporte, responsabilidades e saída aprovados em documento privado.
- [ ] Identificação do contratante e responsável, minimizando coleta e sem copiar esses dados para fontes de estudo.
- [ ] Nome público, logo autorizado, cores com contraste, textos e links públicos revisados.
- [ ] Titularidade do domínio, acesso delegado e responsabilidade pela renovação definidos; nunca solicitar senha por chat comum.
- [ ] Telefone comercial, endereço público, e-mail institucional e mapa conferidos com autorização.
- [ ] Serviços: nome, descrição, preço, duração, disponibilidade e profissionais habilitados.
- [ ] Profissionais: contas e permissões definidas por procedimento seguro; confirmar lacuna de provisionamento descrita em 01.
- [ ] Jornadas por dia, pausas/bloqueios, feriados, fuso e exceções acordados.
- [ ] Regras atuais de reserva, antecedência e reagendamento aceitas; não prometer configuração que não existe.
- [ ] Políticas de privacidade/uso, bases legais e versão do consentimento revisadas por responsáveis competentes.

### Checklist técnico por instalação

- [ ] Árvore/artefatos limpos de release conhecida, sem copiar base, conta, segredo ou marca de outro cliente.
- [ ] Banco novo e usuário restrito exclusivos; ambiente e segredos fora do repositório.
- [ ] Hosts/CORS/origem da API/fuso/reset e transporte de e-mail validados contra requisitos atuais.
- [ ] DNS e TLS corretos, incluindo redirecionamento e comportamento de proxy; não expor banco publicamente.
- [ ] Migrações aplicadas pelo procedimento aprovado; sem stamp e sem alteração de revisões históricas.
- [ ] Admin inicial por canal seguro; profissionais provisionados pelo procedimento aprovado, sem seed de desenvolvimento.
- [ ] Catálogo, vínculos, jornadas, instituição e tema conferidos; sem dados de demonstração visíveis.
- [ ] Backup diário criptografado, cópia externa, alerta e restauração ensaiada em ambiente descartável.
- [ ] Monitor externo, validade de certificado, logs sem conteúdo sensível e alerta para falha de backup.
- [ ] Health/readiness e smoke não mutante aprovados; fluxo completo com dados fictícios em staging.
- [ ] Entrega real de recuperação de senha validada no domínio/remetente correto, sem expor token.
- [ ] Isolamento entre clientes e orçamento de recursos verificados.

### Treinamento, aceite e go-live

- [ ] Dono e equipe conseguem consultar agenda, registrar status, criar bloqueio e ajustar dados permitidos.
- [ ] Explicar que reservas por telefone/WhatsApp precisam entrar na agenda principal; agenda paralela pode gerar conflito externo.
- [ ] Explicar que relatório reflete registros concluídos/avaliados, não conciliação financeira completa.
- [ ] Cliente testa catálogo e jornada de reserva no celular, sabendo que há cadastro e regras de prazo.
- [ ] Canal de suporte, janela, contingência e responsável por dados entregues.
- [ ] Lista de pendências e aceite explícito por escopo; registrar versão e data sem dados pessoais no pacote de estudo.
- [ ] Publicar link nos canais autorizados pelo dono e acompanhar primeiros dias; não fazer postagem em seu nome sem autorização.
- [ ] Realizar check-in após 7 dias e revisão em 30 dias, como proposta inicial de acompanhamento.

Go-live é condicionado aos controles mínimos, não ao entusiasmo da venda. Se algo essencial estiver pendente, informar e reagendar em vez de lançar operação insegura.

## 2. Classificar atendimento antes de agir

| Categoria | Exemplo | Tratamento recomendado |
|---|---|---|
| BUG | Reserva válida falha por erro do produto | Corrigir no core; reproduzir com fixture fictícia; comunicar prazo após diagnóstico. Não consumir franquia de dúvida para esconder defeito. |
| DÚVIDA | Como bloquear férias? | Orientação/documentação na franquia; identificar se treinamento inicial falhou. |
| ALTERAÇÃO DE DADOS | Dono pede atualizar todos os preços | Autonomia pelo painel quando existir; execução pelo fornecedor em franquia ou serviço adicional. |
| PERSONALIZAÇÃO | Novo layout exclusivo de uma seção | Estimar projeto e manutenção; não assumir como correção. |
| NOVA FUNCIONALIDADE | Comissões automáticas | Descoberta, priorização e orçamento; não prometer data por ticket. |
| URGÊNCIA | Site indisponível para todos | Priorizar por impacto; urgência é severidade, podendo também ser bug ou infraestrutura. |

“Preciso trocar a cor hoje” não vira incidente crítico porque veio em maiúsculas. Da mesma forma, falha geral não é dúvida comum. Registrar categoria, severidade, tempo ativo e desfecho permite melhorar preço e produto.

## 3. Escopo sustentável da mensalidade

**PROPOSTA inicial:** hospedagem acordada, monitoramento configurado, backup/retensão definida, correções do produto, atualizações compatíveis e até 30 minutos mensais de orientação operacional. Uma pessoa autorizada centraliza pedidos em canal comercial/tickets. Correções de defeitos reconhecidos não devem ser interrompidas quando a franquia de orientação acabar.

Fora do escopo: cadastros em massa, treinamento de toda nova equipe, relatórios exclusivos, importação complexa, integrações, design exclusivo e atuação fora da janela contratada. Orçar antes de executar. Não cobrar uma surpresa no fim do mês por um pedido sem aceite.

Se 30 minutos forem insuficientes para o ICP, corrigir onboarding ou preço; não usar franquia para tornar impossível o uso normal. Medir média e percentil alto: um cliente com 5h pode consumir a margem de vários com 10 minutos.

### Janela e severidade propostas

| Nível | Definição | Meta de primeira resposta a testar |
|---|---|---|
| S1 | Indisponibilidade geral ou suspeita de exposição de dados | Até 2 horas dentro da cobertura contratada |
| S2 | Função importante falha, com alternativa segura | Até 1 dia útil |
| S3 | Dúvida ou ajuste sem impedir operação | Até 2 dias úteis |

Janela inicial possível: dias úteis, 9h–18h, fuso de Brasília, com feriados definidos. É hipótese de serviço, não promessa presente. Barbearias podem ter pico à noite e sábado: validar compatibilidade antes de vender; se exigirem cobertura adicional, planejar substituto e preço ou recusar.

Primeira resposta é acolhimento/triagem, não solução. Incidente suspeito de dados precisa escalonamento técnico/jurídico imediato conforme processo, sem esperar uma meta comercial para começar. Cobertura 24×7 exige capacidade real, não apenas monitor automático.

## 4. Fluxo de suporte e segurança

Receber → identificar instalação e impacto → orientar a não enviar senha/token/dump → coletar passos de reprodução sanitizados → classificar → tentar em staging → corrigir no core/configuração apropriada → verificar → comunicar → atualizar guia ou prevenção.

Nunca pedir senha do cliente final. Acesso administrativo do operador deve ser individual, autorizado, mínimo e auditável. Exportações e capturas podem conter dados pessoais: evitar em canal aberto e não colar em NotebookLM. Se não houver ambiente de reprodução, montar cenário fictício, sem copiar produção por conveniência.

## 5. Retenção orientada por uso

No primeiro mês, acompanhar adoção: o link está sendo usado? Equipe mantém a agenda única? Há horários vazios por jornada mal cadastrada? Resolver causa, não mandar relatório de vanity metrics. Baixa reserva pode indicar pouco tráfego, fricção ou inadequação; não vender função extra sem diagnóstico.

Relatório mensal recomendado: reservas pelo canal, atendimentos registrados, cancelamentos/faltas registrados, tempo de indisponibilidade observado, status de backup e ações feitas. Separar números do sistema de resultados estimados do negócio. Sem analytics de origem implementado, não inventar quantidade de visitas ou atribuição de venda; propor medição futura com minimização de dados.

Check-in de 15 minutos pode avaliar maior dificuldade, valor percebido e prioridade. Novas funcionalidades ajudam quando resolvem dor recorrente; mais botões não garantem retenção. Avisar manutenção e reajuste com antecedência contratual e explicar mudanças com clareza.

## 6. Inadimplência, cancelamento e saída

Definir lembretes, contato, negociação, eventual suspensão e encerramento com revisão jurídica. Não há cobrança/suspensão automática identificada no produto: processo inicial é operacional, com trilha e autorização. Não apagar base imediatamente após vencimento nem usar dados como ameaça.

Na saída, confirmar responsável autorizado, escopo e formato de exportação do negócio por procedimento específico, prazo, custo se houver e retenção. Exportação JSON/PDF do titular e CSV financeiro não equivalem a exportação completa de todos os dados. Se oferecer portabilidade integral, preparar e testar antes de assinar essa obrigação. Informar política de backups antigos e tratamento de pedidos de titulares após encerramento.

## DADOS QUE PRECISAMOS MEDIR

Onboarding ativo/decorrido, tickets por categoria, horas por cliente, primeira resposta/solução por severidade, custo de retrabalho, adoção em 7/30 dias, atraso de pagamento, motivos de saída e retenção por coorte. Não atribuir melhora ao suporte sem observar evidência.

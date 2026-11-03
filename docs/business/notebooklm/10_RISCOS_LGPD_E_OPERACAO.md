# 10 — Riscos, dados, contrato e operação

Material de planejamento em 31/10/2026, sem parecer jurídico definitivo. **Probabilidades abaixo são avaliações qualitativas hipotéticas**, não frequência histórica. Impacto considera uma operação individual com infraestrutura concentrada. Revisar após pilotos e incidentes.

## 1. Registro de riscos

| Risco | Probabilidade inicial / impacto | Mitigação e indicador |
|---|---|---|
| Suporte excessivo | Alta / alto | ICP, treinamento, franquia razoável, guia e escopo; medir horas e clientes extremos. |
| Inadimplência | Média / alto | Condições claras, lembrete e conciliação; medir vencidos e recuperação, sem suspensão arbitrária. |
| Host compartilhado indisponível | Média / alto | Backup externo, capacidade, pools e contingência; medir disponibilidade e RTO em ensaio. |
| Acesso indevido/segredo exposto | Média / crítico | Menor privilégio, chaves exclusivas, patch, revisão, logs sanitizados e resposta; medir controles, não alegar risco zero. |
| Perda de dados | Média / crítico | Backup criptografado externo e restauração provada; alertar idade do último backup e falhas de restore. |
| Dependência de fornecedor | Média / alto | Dados exportáveis, artefatos reproduzíveis e plano de migração; revisar custo e prazo de saída. |
| Personalização divergente | Alta / alto | Core/config/tema/dados, orçamento e manutenção; medir overrides e conflitos de atualização. |
| Churn por falta de uso | Média / alto | Ativação, agenda única e check-in; medir uso e motivo de cancelamento. |
| Preço abaixo do custo | Alta / alto | Custo da hora, piso de contribuição e sensibilidade; comparar margem real com oferta. |
| Margem aparentemente alta por custo omitido | Alta / alto | Separar receita/caixa/lucro e contabilizar fundador; fechar demonstrativo mensal. |
| Crescimento acima da capacidade | Média / alto | Limitar onboarding, distribuir pools e ter substituto; medir fila, atrasos e carga. |
| Falha de deploy/migração | Média / crítico | Release imutável, staging, backup, canário e parada de lote; medir falhas e tempo de recuperação. |
| Dados/LGPD e obrigações mal definidas | Média / crítico | Inventário, contrato, bases legais, minimização e revisão profissional; acompanhar pedidos/incidentes. |
| Promessa de disponibilidade incompatível | Alta / alto | Vender cobertura real, metas ensaiadas e limites; medir falha externa e resposta. |
| Fundador indisponível | Média / alto | Runbooks, acesso de emergência controlado e substituto contratual; ensaiar recuperação sem memória pessoal. |
| E-mail de recuperação não chega | Média / alto | Remetente/domínio autenticado, testes de entrega e monitor do fornecedor; medir falhas sem registrar tokens. |
| Regras fixas não servem ao cliente | Média / alto | Demonstrar janela/prazos antes da contratação; medir perdas e pedidos de exceção. |
| Dados operacionais errados | Alta / médio/alto | Aceite de preços/jornadas e treinamento; medir reservas impedidas por configuração e retrabalho. |

Uma matriz não elimina risco. Para os riscos críticos, definir responsável, evidência do controle e próxima revisão. “Temos backup” sem resultado de restauração não encerra risco de perda.

## 2. O que o projeto oferece em dados e segurança

**FATO CONFIRMADO NO CÓDIGO:** registro de consentimento versionado, exportação do titular, anonimização autenticada, auditoria e autorização por papel/propriedade. **FATO DOCUMENTADO:** há inventário em `docs/LGPD.md`, política operacional em `docs/PLANO_RECUPERACAO_DESASTRES.md` e orientação de monitor em `docs/MONITORAMENTO.md`.

Esses mecanismos ajudam a implementar processos, mas não tornam o produto “certificado LGPD”. Aceite obrigatório na interface não determina sozinho a base legal correta. Também não transforma todos os agentes em operadores nem exclui direitos dos titulares. Validar com profissional a adequação da coleta e do fluxo atual.

## 3. Técnico versus jurídico

**RECOMENDAÇÃO TÉCNICA:** mapear dados, restringir acessos, criptografar backups, evitar conteúdo sensível em logs, separar clientes, registrar alterações, testar recuperação e manter dependências atualizadas. São controles implementáveis e verificáveis.

**PAUTA JURÍDICA:** definir finalidade/base legal, papéis de controlador/operador, atendimento a titulares, retenção, transferência internacional, terceiros, incidentes, responsabilidade e condições comerciais. As conclusões dependem da relação e do tratamento real, não do nome dado no contrato.

Hipótese usual a validar: barbearia decide finalidades da agenda de seus clientes e fornecedor trata por instrução ao hospedar/manter; fornecedor pode ser controlador de sua própria relação comercial/cobrança. Não assumir que um único papel vale para todos os dados.

## 4. Pauta de contrato e documentos

| Tema | O que levar ao advogado/contador | Evidência/decisão necessária |
|---|---|---|
| Objeto e licença | Direito de uso, instalação, limites e propriedade intelectual | Core permanece do fornecedor? Marca e materiais pertencem a quem? |
| Escopo e aceite | Entregas, exclusões, critérios, retrabalho e prazo de insumos | Proposta e checklist de 07/09. |
| Suporte | Canal, cobertura, severidade, franquia e extras | Capacidade real de atendimento, não prazo aspiracional. |
| Disponibilidade | Meta, medição, manutenção, dependências e consequência de falha | Histórico e ensaios; não vender 100% nem prometer indenização sem análise. |
| Dados e terceiros | Instruções, agentes, suboperadores, região e transferência | Inventário de tratamento e fornecedores escolhidos. |
| Privacidade/termos | Transparência, direitos, contato e versões | Textos aprovados e coerentes com coleta atual. |
| Backup/retenção | Frequência, local, acesso, chave e descarte | Metas de RPO/RTO versus medidas; backups após exclusão. |
| Incidente | Aviso entre partes, responsabilidades e comunicações aplicáveis | Runbook, contatos e fonte regulatória vigente. |
| Preço/reajuste | Base, índice/período, aviso, extras e tributos | Simulação financeira validada pelo contador. |
| Inadimplência | Lembretes, suspensão, reativação e preservação de dados | Procedimento executável e proporcional. |
| Cancelamento/portabilidade | Aviso, formato, escopo, prazo, custo e eliminação | Processo de exportação integral quando prometido, não só export pessoal. |
| Responsabilidade | Limites, obrigações, exceções e remédios | Não copiar cláusula genérica para excluir toda responsabilidade. |
| Customização | Financiamento, titularidade, uso no core e manutenção | Orçamento separado e critério de atualização. |
| Formalização fiscal | Atividade, enquadramento, emissão e regime | Validação com contador; não assumir MEI ou alíquota universal. |

Política de privacidade, termos de uso, contrato comercial e acordo de tratamento têm funções diferentes; não presumir que um checkbox substitui todos. Não copiar documentos de concorrentes como contrato próprio.

## 5. Incidentes e fontes oficiais

**DADO EXTERNO**, consulta em 31/10/2026: a ANPD mantém procedimento de comunicação de incidente pelo controlador, por representante/encarregado, em seu canal oficial. Ver [Comunicação de Incidente de Segurança — ANPD](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis). A referência normativa inclui a Resolução CD/ANPD nº 15/2024; verificar texto vigente, enquadramento e prazos com assessoria. Este pacote não fixa prazo jurídico universal nem substitui avaliação de risco relevante.

Para bases legais, direitos e agentes, consultar a [LGPD — Lei 13.709/2018, texto oficial](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm), com validação profissional antes de adotar cláusulas. O documento não faz interpretação conclusiva de artigos.

Runbook técnico recomendado: detectar e registrar horário/escopo → conter acesso sem destruir evidência → acionar responsável → preservar registros necessários com acesso restrito → avaliar dados e instalações afetados → recuperar em ambiente limpo → coordenar comunicações com controlador e jurídico → verificar retorno → revisar causa e controles. Não mandar dump de incidente à ferramenta de estudo.

## 6. Continuidade e disponibilidade

O plano existente registra RPO 24h e RTO 4h como metas. Se houver apenas backup diário, perder reservas de parte do dia é possível; transparência é essencial. Restauração deve usar versão/schema compatíveis, com comparação e prova de funcionamento. Chave de descriptografia perdida torna backup inútil; mantê-la protegida fora do host com recuperação controlada.

Contingência da barbearia: registrar manualmente alterações durante interrupção e reconciliar com cuidado após retorno. Isso não exige entregar todos os dados em papel diariamente; minimizar exposição. Definir quem comunica clientes e quem resolve conflitos de reservas criadas no intervalo.

## DADOS QUE PRECISAMOS MEDIR

Disponibilidade observada, incidentes, tempo de detecção/triagem/recuperação, RPO real, teste de acesso cruzado, restauração, fornecedores e regiões, pedidos de titulares, custo de conformidade e capacidade de substituição do fundador. Revisar matriz mensalmente no início e após qualquer incidente relevante.

# 06 — Crescer com várias instalações, sem multi-tenancy prematura

Este é um **PLANO RECOMENDADO**, não implementação. O produto atual já orienta bancos e configurações próprios e possui gerador de árvore limpa; não existe provisionamento integral nem orquestrador de frotas comprovado no escopo inspecionado.

## 1. Desenho futuro

```text
Internet → DNS / borda opcional → VPS: proxy Nginx ou Caddy
                                 ├── cliente-a
                                 │   ├── frontend da marca A
                                 │   ├── API imagem core:1.2.0
                                 │   └── config/secrets/volume A
                                 ├── cliente-b
                                 │   ├── frontend da marca B
                                 │   ├── API imagem core:1.1.3
                                 │   └── config/secrets/volume B
                                 └── PostgreSQL em rede privada
                                     ├── banco A / usuário A
                                     └── banco B / usuário B
Backup criptografado por cliente → destino fora da VPS
Monitor externo → alertas → operador responsável
```

Cada API atende uma barbearia. Compartilhar host ou motor PostgreSQL não obriga compartilhar tabelas/contas nem selecionar tenant por requisição. Isso é consolidação de infraestrutura, preservando o modelo por instalação. É possível manter versões diferentes por curto período; controlar atraso para não criar suporte permanente a dezenas de releases.

Docker empacota runtime e dependências. Compose descreve serviços, redes e volumes de uma instalação/pool. Proxy associa domínio a frontend/API e termina TLS. Caddy pode simplificar certificados; Nginx permite controle explícito com renovação configurada. A escolha deve refletir familiaridade e procedimento de recuperação, não preferência estética.

## 2. Separação mínima entre clientes

| Camada | Controle recomendado | Verificação antes de liberar |
|---|---|---|
| DNS/proxy | Domínio exato e backend explícito, sem fallback para outro cliente | Host desconhecido não deve cair em instalação alheia. |
| API | Configuração, JWT secret, CORS e hosts exclusivos | Token emitido em A não autentica em B; origens não autorizadas recusadas. |
| Banco | Banco e usuário próprios, sem privilégios globais; grants e acesso à rede limitados | Credencial runtime A não lê nem escreve B; revisar permissão CONNECT além de tabelas. |
| Arquivos | Volumes, branding, temporários e diretórios de backup distintos | Logo/export/backup A não aparece no artefato B. |
| Rede | Só proxy público; PostgreSQL interno; APIs sem portas públicas desnecessárias | Portas expostas conferidas; administração em canal restrito. |
| Recursos | Limites de CPU/RAM/processos e rotação de logs | Uso intenso em A não derruba B dentro da carga admitida. |
| Segredos | Cofre/arquivos protegidos fora do Git e do frontend | Nenhuma chave em imagem, log, shell history ou pacote de estudo. |
| Operação | Inventário por ID, trilha de mudança e permissões humanas mínimas | Operador seleciona explicitamente instalação, ambiente e versão. |

Containers compartilham kernel; usuário root do host ainda pode alcançar a carteira. Bancos separados no mesmo motor não são isolamento de máquina. Cliente que exige fronteira maior deve ter pool/VM/conta e preço compatíveis. Não prometer “isolamento absoluto”.

## 3. Implantação e domínio

Preferir frontend e API sob o mesmo domínio registrável e HTTPS, com origens explícitas. O refresh usa cookie; combinações de domínios independentes podem ter restrições de navegador. Verificar fluxo real em celular antes de vender um desenho de domínio. Certificado e DNS são dependências operacionais, não só configuração inicial.

Inventário mínimo: ID não pessoal da instalação, domínio público, versão/digest da API, versão do frontend, revisão Alembic, pool, referência do segredo no cofre, plano de backup, última restauração, responsável e janela. Não guardar conteúdo dos segredos no inventário.

Logs devem informar instalação, horário, rota normalizada, status e correlação sem corpo do pedido, tokens ou dados pessoais. Métricas atuais são por processo e voláteis; persistir séries agregadas no sistema de monitoramento, com acesso controlado. Monitorar externamente catálogo, health, ready e certificado; fluxo sintético de gravação apenas em ambiente de teste autorizado.

## 4. Futuro create-client

**FATO CONFIRMADO:** `tools/new-installation/create.py` copia núcleo limpo, gera exemplos e checklist, evitando bases e segredos da origem. **RECOMENDAÇÃO:** evoluir por etapas, mantendo revisão humana para dados legais, credenciais e entrada em produção. Não executar o plano abaixo nesta tarefa.

Entrada desejada, sem secrets em argumentos:

```text
create-client --manifest <arquivo-validado> --product-version <release>
manifest: ID, nome público, domínio, logo, tema, telefone comercial,
endereço público, serviços/preços/duração, profissionais, jornadas e fuso
secrets: referências no cofre, geradas/selecionadas por canal protegido
```

Profissionais e cadastros iniciais podem conter dados pessoais: manifest operacional deve ser privado e temporário, nunca exemplo público ou fonte de NotebookLM. No material de treinamento usar nomes fictícios. Credencial inicial não pode ser senha padrão compartilhada.

Etapas futuras:

1. Validar unicidade do ID/domínio, formato de valores, limites, versão e posse do domínio; mostrar plano sem segredos.
2. Criar diretórios e permissões próprios, sem copiar instalação ativa. Registrar estado “preparando”.
3. Criar banco e usuário via credencial de provisionamento separada do runtime; armazenar referências seguras.
4. Renderizar frontend/configuração de marca a partir do core. Validar hosts, origens e fuso com requisitos atuais, não só template antigo.
5. Subir banco/rede e aplicar revisões publicadas em banco novo; nunca stamp ou editar revisão existente.
6. Criar admin e profissionais por mecanismo seguro futuro, com autorização e trilha. O gerador atual não oferece toda essa etapa; não reutilizar seed dev.
7. Importar apenas dados iniciais permitidos e idempotentes. Serviços e horários são dados de implantação, não migração Alembic por cliente.
8. Preparar proxy/DNS/SSL usando permissões mínimas; alterações externas exigem fluxo operacional próprio.
9. Configurar backup externo/alertas; validar restauração em ambiente descartável e testes de isolamento.
10. Smoke, aceite e liberação; registrar versão, duração, pendências e prova de entrega sem PII.

Para chegar a minutos, medir primeiro tempo ativo versus espera por logo/domínio. Automatizar os passos repetidos, não os erros. Comando deve ser retomável e idempotente: se falhar no SSL, não recriar banco e perder estado. Falha preserva recursos para diagnóstico e exige limpeza explícita; nunca “apagar tudo” como recuperação automática.

## 5. Release e atualização de carteira

```text
core v1.2.0 → CI → imagem imutável por digest + artefato frontend
                    ↓ homologação fictícia + ensaio de migração
                    ↓ instalação canário autorizada
                    ↓ pequeno lote saudável
                    ↓ demais instalações com checkpoint individual
```

Uma release contém notas de mudança, compatibilidade, versão de schema, imagem assinada/verificada conforme política futura, instruções e riscos. CI testa Python SQLite/PostgreSQL descartável, Node, migrações/paridade, E2E e auditorias. O pipeline atual já descreve essas famílias de checagem, mas publicação de imagem e distribuição por frota são evolução.

Não usar tag mutável `latest` como prova de versão. Core deve ser o mesmo; frontend pode ser gerado para cada marca. Hoje a configuração reside em arquivos: externalizar/montar configuração exige alteração futura deliberada, não acontece só por escrever uma proposta arquitetural.

### Runbook por instalação

1. Selecionar release, conferir instalação e revisão atual, janela e responsável. Bloquear deploy simultâneo sobre o mesmo cliente.
2. Produzir backup pré-deploy com cópia externa e confirmar integridade/recuperabilidade. Não confundir checksum com prova de restauração.
3. Quando a migração exigir, suspender gravações e drenar processos. Planejar duração informada ao cliente.
4. Aplicar upgrade Alembic uma vez por banco, com conexão restrita ao alvo. Nunca reaproveitar URL de outra instalação.
5. Iniciar versão nova, consultar `/ready` e `/health`, checar catálogo, autenticação e reserva fictícia em staging; em produção usar smoke sem mutação e verificações autorizadas.
6. Reabrir tráfego, observar erros/latência, atualizar inventário e só então promover próximo lote.

Um canário saudável por alguns minutos não comprova a semana inteira. Definir janela de observação proporcional à mudança e ao tráfego. Se falhar em um cliente, parar lote; não promover erro porque os demais ainda estão sem reclamação.

### Rollback tem duas dimensões

Rollback de imagem só é seguro se a versão anterior compreender o schema atual. Migrações devem preferir evolução compatível em etapas: adicionar, migrar dados, adotar leitura/escrita e só retirar estrutura em release posterior quando seguro. O histórico contém revisões sem downgrade destrutivo permitido; não pressupor `downgrade` universal.

Se o schema ficou incompatível, manter manutenção e escolher correção adiante ou recuperação em **novo banco**, preservando original e registrando perda potencial de gravações após o backup. Restaurar cegamente sobre banco vivo pode apagar reservas válidas. Testar procedimento em ambiente descartável antes da primeira janela comercial.

## 6. Não criar vinte versões do produto

Manter core versionado + configuração + tema + dados. Os docs atuais admitem repositórios/branches privados de instalação; isso não deve virar licença para divergir regras. Inventariar overrides e fazer cada release validar marca, contatos e termos. Não resolver pedido temporário com if por nome da barbearia.

Automação de frota pode começar como inventário e execução sequencial com revisão de resultado. Não exige Kubernetes, plano de controle multi-tenant ou uma arquitetura nova. Multi-tenancy só merece estudo quando custo operacional medido e demanda justificarem migração, com análise de isolamento, dados e retorno do investimento.

## DADOS QUE PRECISAMOS MEDIR

Tempo de create-client por etapa, taxa de falhas, tempo de migração, atraso de versão por cliente, restore, rollback ensaiado, impacto entre vizinhos e horas mensais de atualização. Sem esses dados não prometer “20 instalações em um clique” ou tempo de recuperação contratual.

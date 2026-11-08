# Privacidade e atendimento de solicitações LGPD

Este documento descreve o tratamento implementado como referência operacional. A base legal aplicável, os prazos obrigatórios e as exceções de retenção devem ser confirmados pelo controlador com assessoria jurídica. **Este documento não substitui parecer jurídico.**

## Inventário de dados

| Tabela | Dados pessoais ou relacionados | Finalidade e base legal operacional considerada | Retenção e tratamento na exclusão |
| --- | --- | --- | --- |
| `users` | Nome, e-mail, hash de senha, perfil, bloqueio, estado da conta e consentimento atual | Cadastro, autenticação, agendamento e administração; execução de contrato e, para comunicações opcionais, consentimento | Enquanto a conta estiver ativa. Na exclusão, nome/e-mail/hash são substituídos, a conta é desativada e o consentimento atual é limpo. |
| `consentimentos_lgpd` | Versão e data de aceite, IP e origem | Evidência do aceite; consentimento e exercício regular de direitos | Na exclusão, o vínculo de usuário e IP são removidos; versão/data são preservadas sem ligação ao titular. |
| `appointments` | Cliente, barbeiro, horários e histórico de atendimento | Prestação do serviço e manutenção dos registros financeiros; execução de contrato e obrigação legal aplicável | Dados operacionais enquanto necessários. Na exclusão, vínculo/nome do cliente são removidos; valores, datas, serviço e status permanecem. A conta de barbeiro fica anonimizada para manter a referência histórica exigida pelo esquema. |
| `avaliacoes` | Nota, comentário e vínculo ao atendimento | Qualidade e moderação; legítimo interesse, sujeito à avaliação do controlador | Na exclusão do titular, comentário e vínculo são apagados; nota e data são preservadas sem identificação. |
| `services` | Catálogo, preço e duração (sem dados de titular) | Oferta e faturamento dos serviços; execução de contrato | Mantida conforme necessidade operacional. |
| `jornadas_trabalho`, `bloqueios_horario`, `barbeiros_servicos` | Identificador do barbeiro, horários e serviços associados | Organização da agenda; execução de contrato/gestão operacional | Removidos quando a conta de barbeiro é excluída. |
| `password_reset_tokens` | Hash do token, validade e usuário associado | Redefinição segura de senha; execução de contrato e segurança | Token consumido/expirado é inutilizado; todas as linhas são removidas na exclusão da conta. |
| `refresh_tokens` | Hash SHA-256, família, datas e estado de revogação | Renovação e revogação de sessão; execução de contrato e segurança | Revogados no encerramento; na exclusão, vínculo ao usuário é removido e a linha permanece revogada. |
| `login_attempts` | IP, rota, resultado e data/hora | Proteção contra força bruta; legítimo interesse/segurança | Limpeza limitada a registros antigos, atualmente 30 dias. |
| `audit_logs` | Usuário (opcional), perfil, ação, entidade, IP, resultado, detalhes e data/hora | Rastreabilidade e segurança; legítimo interesse e exercício regular de direitos | `RETENTION_DAYS` (padrão 365). Na exclusão, vínculo, IP, identificador de entidade e detalhes associados ao titular são removidos. |
| `informacoes_institucionais` | Dados de contato da empresa; podem incluir contato profissional | Divulgação institucional e atendimento; legítimo interesse/execução de contrato | Mantidos enquanto atuais; o controlador deve atualizar ou remover contatos que identifiquem pessoa física quando deixarem de ser necessários. |

Senhas são armazenadas como hash de verificação, refresh tokens como SHA-256 e tokens de redefinição como hash. Os endpoints de exportação nunca devolvem esses valores.

## Como atender ao titular

1. **Confirme a identidade** usando a sessão autenticada. Para excluir a conta, a API exige também a senha atual; a exclusão do último administrador ativo é recusada para evitar bloquear a instalação.
2. **Acesso e portabilidade:** na página “Minha conta”, use **Exportar meus dados**. A API `GET /users/me/exportacao` entrega JSON versionado com cadastro, consentimentos, agendamentos e avaliações próprios. A rota limita exportações por IP. O arquivo não inclui credenciais ou dados pessoais de outros usuários.
3. **Exclusão:** na mesma página, confirme a ação e informe a senha atual. `DELETE /users/me` anonimiza a conta, revoga sessões, remove tokens de redefinição e desvincula registros pessoais em uma transação. Dados financeiros necessários permanecem sem nome ou vínculo de cliente; notas de avaliação permanecem sem comentário ou vínculo.
4. **Outros pedidos** (correção, informação sobre compartilhamento, oposição ou revisão) devem ser encaminhados ao controlador da instalação. A aplicação não tem workflow para esses pedidos; registre a solicitação fora do sistema e valide a resposta, o prazo e eventuais obrigações legais aplicáveis.
5. **Verifique a conclusão** sem copiar dados pessoais para logs. Se o pedido exigir retenção legal de algum registro, documente a justificativa, o prazo e o acesso restrito antes de responder.

Os prazos de retenção dependem do contexto da instalação e da legislação aplicável. O controlador deve revisar esta tabela, configurar `RETENTION_DAYS` e estabelecer rotina para os demais registros antes de operar em produção.

# Arquivo histórico da PR36

Os commits 345aa03 e 9353a9f foram preservados no histórico desta branch. Sua implementação de cadastro, autorização, agendamento e telas é anterior às revisões atuais e foi substituída pelas versões da main durante a resolução dos conflitos.

Nenhuma funcionalidade antiga foi reaplicada sobre JWT por ID, CAS, refresh/logout, LGPD, disponibilidade, cookies ou CSP atuais. Os arquivos de produção são idênticos aos da main e não exigem migração.

Os dois scripts foram mantidos integralmente como `.py.txt`, para consulta e sem descoberta/importação automática por runners de testes. Eles possuem caminhos absolutos, dados de seed e expectativas antigas de `dev_token`; não são testes atuais nem devem ser executados contra bancos existentes. As credenciais literais são fixtures históricas, não instruções de acesso.

As suítes isoladas atuais em backend/tests e frontend/tests substituem essa cobertura. Esta PR agora só adiciona o arquivo histórico; não é uma correção funcional nova.

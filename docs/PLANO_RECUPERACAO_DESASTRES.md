# Plano de backup e recuperação de desastres

## Objetivos e responsáveis

Objetivos operacionais para cada instalação:

- **RPO:** no máximo 24 horas de dados.
- **RTO:** serviço restaurado em até 4 horas.
- **Frequência:** backup diário do PostgreSQL, em formato custom, com snapshot transacional consistente.
- **Retenção local:** 30 dias. Configure retenção equivalente ou maior no destino externo.
- **Estado de validação:** os objetivos são metas documentadas; não foram medidos em uma recuperação real. O teste de restauração PostgreSQL deste repositório está **não executado** enquanto não houver uma instância descartável disponível.

Preencha e revise em cada instalação:

| Responsabilidade | Responsável / contato |
|---|---|
| Proprietário do serviço e aprovação de recuperação | A preencher |
| Operador PostgreSQL e restauração | A preencher |
| Operador do armazenamento externo e chaves age | A preencher |
| Comunicação com usuários e decisão de retorno | A preencher |
| Local do procedimento e inventário de dependências | A preencher |

## Preparação do backup

Os scripts em `tools/backup/` criam `pg_dump` em formato custom, mantêm o diretório privado, calculam SHA-256 e criptografam cada dump com `age` antes de gravá-lo. O manifesto JSON registra a revisão Alembic e as contagens por tabela na mesma transação/snapshot MVCC que o `pg_dump` usa; ele não contém linhas ou dados pessoais. A cópia opcional para outro host/serviço transfere o dump já criptografado.

Use uma conta PostgreSQL dedicada com permissão de leitura consistente em todas as tabelas e configuração adequada para ignorar RLS quando necessário. Instale `pg_dump` compatível com a versão do servidor, `age`, `rsync`, `rclone` ou AWS CLI conforme o destino, e as dependências do projeto no ambiente virtual.

Configure variáveis no ambiente do usuário de serviço, sem colocar senha em argumento ou arquivo versionado:

```text
PGHOST=db-interno
PGPORT=5432
PGDATABASE=barbearia
PGUSER=backup_reader
PGPASSFILE=/etc/barbearia/backup.pgpass
BACKUP_DIR=/var/lib/barbearia-backup
BACKUP_AGE_RECIPIENT=age1...chave-publica-do-operador...
BACKUP_RETENTION_DAYS=30
BACKUP_REMOTE_MODE=rsync
BACKUP_REMOTE_DEST=backup-externo:/srv/backups/barbearia/
```

`BACKUP_REMOTE_MODE` e `BACKUP_REMOTE_DEST` são obrigatórios para concluir o job. Modos aceitos: `rsync` por SSH, `rclone` com remote previamente configurado pelo operador, ou `s3://bucket/prefixo` via AWS CLI. O modo S3 pede criptografia de servidor AES-256; a criptografia cliente `age` permanece obrigatória. O repositório não cria contas, buckets, remotes nem serviços de nuvem.

Proteja o `PGPASSFILE` com acesso apenas à conta de serviço e use uma entrada de banco `*` limitada ao host/usuário de backup, pois a instância criada para teste trimestral recebe nome aleatório. Em Linux/macOS use `chmod 600`; no Windows aplique ACL somente à conta de serviço e `SYSTEM`. Não use `PGPASSWORD`, URL com senha, nem `--password` na linha de comando. Mantenha a chave privada age fora do servidor da aplicação, em cofre/armazenamento offline controlado. A chave pública pode estar no ambiente do job.

## Execução e verificação

Linux/macOS:

```bash
bash tools/backup/backup.sh
```

Windows PowerShell, com o ambiente configurado para a conta de serviço:

```powershell
& .\tools\backup\backup.ps1
```

Um sucesso produz três arquivos com o mesmo nome-base datado: `.dump.age`, `.sha256` e `.manifest.json`. A rotina remove somente arquivos diretos do diretório configurado cujo nome completo corresponda ao padrão `barbearia-postgres-YYYYMMDDTHHMMSSZ-xxxxxxxx.dump.age` e cuja data ultrapasse a retenção. A remoção remota fica sob controle do operador do destino e deve preservar pelo menos 30 dias.

Valide periodicamente se os três arquivos existem, checksum confere, última execução foi bem-sucedida e cópia externa foi recebida. Não considere um backup bem-sucedido como proteção suficiente sem teste de restauração.

### Teste trimestral de restauração

Execute a cada três meses em uma máquina/VM ou container PostgreSQL **descartável**, acessível somente por loopback. O usuário precisa poder criar e remover bancos nesse servidor de teste. Nunca use produção, homologação com dados reais ou host remoto. A base configurada em `PGDATABASE` deve terminar em `_test`; o script também exige `RESTORE_TEST_ALLOW` literal como barreira explícita, cria um banco com prefixo `barbearia_restore_test_` e remove somente esse banco gerado.

Exemplo Linux/macOS, com o daemon PostgreSQL de teste publicado em `127.0.0.1:55432`:

```bash
export PGHOST=127.0.0.1 PGPORT=55432 PGDATABASE=restore_runner_test PGUSER=restore_test
export PGPASSFILE=/etc/barbearia/restore-test.pgpass
export BACKUP_DIR=/var/lib/barbearia-backup
export BACKUP_AGE_IDENTITY_FILE=/etc/barbearia/keys/backup-age-identity.txt
export RESTORE_TEST_ALLOW=I_UNDERSTAND_DISPOSABLE_DATABASE
tools/backup/restore-test.sh
```

No Windows, configure as variáveis de ambiente da conta de teste e rode:

```powershell
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '55432'
$env:PGDATABASE = 'restore_runner_test'
$env:PGUSER = 'restore_test'
$env:PGPASSFILE = 'C:\ProgramData\Barbearia\restore-test.pgpass'
$env:BACKUP_DIR = 'D:\BarbeariaBackup'
$env:BACKUP_AGE_IDENTITY_FILE = 'C:\ProgramData\Barbearia\keys\backup-age-identity.txt'
$env:RESTORE_TEST_ALLOW = 'I_UNDERSTAND_DISPOSABLE_DATABASE'
& .\tools\backup\restore-test.ps1
```

O teste valida hash e manifesto, transmite a descriptografia diretamente ao `pg_restore` por pipe (sem dump plaintext temporário), executa `python -m alembic current` e compara revisão e contagem de todas as tabelas contra o snapshot salvo. Falha em qualquer diferença e tenta remover o banco descartável mesmo em erro. Registre data, duração, operador, identificador do backup, contagens comparadas e resultado; não copie dados ou logs com PII para o relatório. Se não houver PostgreSQL descartável, registre **não executado** e reagende.

## Exemplos de agendamento

Os exemplos pressupõem que a conta de serviço já tenha ambiente/credenciais configurados. Ajuste caminhos, conta, fuso e horário conforme política local. Não passe segredos nos argumentos.

**Cron diário, Linux:**

```cron
15 2 * * * cd /opt/barbearia-agendamento && set -a && . /etc/barbearia/backup.env && set +a && bash tools/backup/backup.sh >> /var/log/barbearia-backup.log 2>&1
```

Restrinja `backup.env` e o log à conta de serviço/administradores. Inclua somente `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSFILE`, `BACKUP_DIR`, `BACKUP_AGE_RECIPIENT`, `BACKUP_REMOTE_MODE` e `BACKUP_REMOTE_DEST`; a senha fica no arquivo passfile protegido.

**systemd timer diário:** `/etc/systemd/system/barbearia-backup.service`:

```ini
[Unit]
Description=Encrypted PostgreSQL backup for barbearia

[Service]
Type=oneshot
User=barbearia-backup
Group=barbearia-backup
WorkingDirectory=/opt/barbearia-agendamento
EnvironmentFile=/etc/barbearia/backup.env
ExecStart=/usr/bin/bash /opt/barbearia-agendamento/tools/backup/backup.sh
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/barbearia-backup
```

`/etc/systemd/system/barbearia-backup.timer`:

```ini
[Unit]
Description=Daily barbearia PostgreSQL backup

[Timer]
OnCalendar=*-*-* 02:15:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Ative com `systemctl daemon-reload`, `systemctl enable --now barbearia-backup.timer`; confirme `systemctl list-timers` e monitore `journalctl -u barbearia-backup.service`.

**Agendador de Tarefas do Windows:** crie uma tarefa diária às 02:15 para uma conta de serviço dedicada, com “Executar estando o usuário conectado ou não”, “Não armazenar senha” apenas se a política e o acesso remoto permitirem, e ação:

```text
powershell.exe -NoProfile -NonInteractive -File C:\Barbearia\tools\backup\backup.ps1
```

Defina as variáveis no perfil/ambiente protegido dessa conta. Não coloque senha em “Adicionar argumentos”. Restrinja a pasta de backup e o passfile com ACLs.

Agende também o teste trimestral em um host/VM temporário de restore. Cron: `15 3 1 1,4,7,10 * ... bash tools/backup/restore-test.sh`. Para systemd, crie um timer separado com quatro diretivas `OnCalendar=*-01-01 03:15:00 UTC`, `OnCalendar=*-04-01 03:15:00 UTC`, `OnCalendar=*-07-01 03:15:00 UTC` e `OnCalendar=*-10-01 03:15:00 UTC`, ligado a um service que define o ambiente exclusivo do PostgreSQL descartável. Windows Task Scheduler: tarefa mensal, meses `1,4,7,10`, dia `1`, ação `powershell.exe -NoProfile -NonInteractive -File C:\Barbearia\tools\backup\restore-test.ps1`. Nunca reutilize a tarefa/env de restore para apontar a produção.

## Restauração após incidente

1. Declare o incidente, nomeie o responsável pela recuperação e registre horário, sintomas, escopo conhecido e decisão de continuidade. Preserve evidências e impeça gravações no ambiente afetado quando isso for seguro.
2. Prepare host limpo e isolado, PostgreSQL compatível, versão correta da aplicação, ferramentas `age`/`pg_restore`, rede e armazenamento. Crie novo usuário PostgreSQL restrito e banco vazio; não sobrescreva o banco antigo.
3. Obtenha do destino separado o backup mais recente cuja cópia e checksum estejam íntegros. Compare SHA-256; não restaure arquivo sem manifesto correspondente.
4. Recupere a chave privada age por procedimento de cofre com dupla autorização, descriptografe o arquivo em diretório privado e execute `pg_restore --exit-on-error --no-owner --dbname=<banco-vazio> <dump-custom>`.
5. Garanta que a conta usada para restaurar seja proprietária dos objetos ou aplique grants mínimos ao usuário runtime após a importação. Configure `DATABASE_URL` para o banco restaurado e execute `python -m alembic current` a partir de `backend/`. Não rode upgrade automático durante a recuperação sem avaliar compatibilidade com a versão restaurada.
6. Compare a revisão Alembic e contagens por tabela com o manifesto do backup. Confirme conectividade, `/health`, autenticação, leitura de agenda, disponibilidade e consulta administrativa/financeira com contas de teste autorizadas. Confirme também cabeçalhos, CORS, SMTP, armazenamento externo e observabilidade antes de reabrir tráfego.
7. Registre o horário em que o serviço foi validado e reaberto. Calcule RPO real desde a última gravação recuperada e RTO desde o início do incidente; se exceder a meta, abra ação corretiva.
8. Faça a troca controlada de DNS/proxy e acompanhe erros, taxa 5xx e logs. Mantenha o banco antigo isolado e preservado até autorização do responsável e encerramento dos requisitos legais/forenses.

### Rotação de `SECRET_KEY` após incidente

- [ ] Trate a chave anterior como comprometida; revogue o acesso ao cofre e identifique ambientes que a receberam.
- [ ] Gere uma nova chave de alta entropia fora da linha de comando versionada e guarde-a no cofre de segredos.
- [ ] Atualize somente o ambiente limpo e reinicie os processos. Não grave a chave em logs, tickets ou relatórios.
- [ ] Revogue sessões/refresh tokens e tokens de redefinição ativos; reautentique administradores e operadores.
- [ ] Confirme tokens antigos rejeitados e login novo funcional. A rotação invalida JWTs assinados pela chave anterior.
- [ ] Revise contas, passfiles, credenciais PostgreSQL, SMTP, SSH/rclone/AWS e a chave privada age conforme o escopo do incidente; rotacione cada segredo afetado separadamente.
- [ ] Registre responsáveis, data, confirmação de revogação e evidências sem incluir os valores das chaves.

## Proteção de dados pessoais

Backups incluem dados pessoais e financeiros de clientes e equipe. O arquivo de dados é cifrado no cliente com `age` antes da cópia externa; mantenha a chave privada separada do servidor da aplicação e limite a custódia a operadores nomeados. Use TLS/SSH ou transporte cifrado para cópia, volume/disco cifrado para arquivos temporários e destino, ACL/Unix permissions restritas, contas individuais, MFA onde disponível e trilha de acesso. Não habilite URLs públicas, links compartilháveis ou permissões amplas no bucket/remote. Teste rotação e recuperação das chaves sem expor dados. Aplique retenção definida, registre exclusões e avalie pedidos de titulares conforme a política LGPD da instalação; cópias antigas podem manter dados até expirar a retenção e devem ter acesso restrito. Este procedimento operacional não substitui parecer jurídico.

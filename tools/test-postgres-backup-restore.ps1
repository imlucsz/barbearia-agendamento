$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"
$image = "postgres:16-alpine"
$containerName = "barbearia-backup-restore-test-$([guid]::NewGuid().ToString('N'))"
$backupPath = Join-Path ([IO.Path]::GetTempPath()) "barbearia-backup-test-$([guid]::NewGuid().ToString('N')).dump"
$seedScriptPath = Join-Path ([IO.Path]::GetTempPath()) "barbearia-backup-seed-$([guid]::NewGuid().ToString('N')).py"
$snapshotScriptPath = Join-Path ([IO.Path]::GetTempPath()) "barbearia-backup-snapshot-$([guid]::NewGuid().ToString('N')).py"
$containerStarted = $false
$environmentNames = @(
  "APP_ENV", "DATABASE_URL", "SECRET_KEY", "CORS_ALLOWED_ORIGINS", "ALGORITHM",
  "ACCESS_TOKEN_EXPIRE_MINUTES", "SCHEDULING_TIMEZONE", "SMTP_HOST", "SMTP_PORT",
  "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_TIMEOUT_SECONDS",
  "PASSWORD_RESET_URL", "POSTGRES_PASSWORD", "BOOKING_TEST_BACKEND",
  "BOOKING_TEST_POSTGRES_URL", "PYTHONPATH"
)
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
  $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
  [Environment]::SetEnvironmentVariable($name, "", "Process")
}

function Invoke-CheckedNative {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$ArgumentList
  )

  $previousErrorAction = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $output = & $FilePath @ArgumentList 2>&1
    $exitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $previousErrorAction
  }
  if ($exitCode -ne 0) {
    $safeDiagnostics = ($output | ForEach-Object { $_.ToString() }) -join "`n"
    if ($testPassword) {
      $safeDiagnostics = $safeDiagnostics.Replace($testPassword, "[REDACTED]")
    }
    $safeDiagnostics = [regex]::Replace(
      $safeDiagnostics,
      "postgresql\+psycopg://[^@\s]+@",
      "postgresql+psycopg://[REDACTED]@"
    )
    throw "A required isolated backup/restore command failed (exit code $exitCode): $safeDiagnostics"
  }
  return $output
}

try {
  if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Backend virtualenv not found. Install backend/requirements.txt into backend/.venv first."
  }
  $null = Invoke-CheckedNative "docker" @("info", "--format", "{{.ServerVersion}}")
  $null = Invoke-CheckedNative "docker" @("image", "inspect", $image)
  if (Test-Path -LiteralPath $backupPath) {
    throw "Refusing to overwrite the randomly named temporary backup path."
  }

  $randomBytes = New-Object byte[] 32
  $secretBytes = New-Object byte[] 48
  $randomGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
  try {
    $randomGenerator.GetBytes($randomBytes)
    $randomGenerator.GetBytes($secretBytes)
  }
  finally {
    $randomGenerator.Dispose()
  }
  $testPassword = [BitConverter]::ToString($randomBytes).Replace("-", "")
  $testSecret = [BitConverter]::ToString($secretBytes).Replace("-", "")
  [Environment]::SetEnvironmentVariable("POSTGRES_PASSWORD", $testPassword, "Process")
  [Environment]::SetEnvironmentVariable("APP_ENV", "test", "Process")
  [Environment]::SetEnvironmentVariable("SECRET_KEY", $testSecret, "Process")
  [Environment]::SetEnvironmentVariable("CORS_ALLOWED_ORIGINS", "", "Process")
  [Environment]::SetEnvironmentVariable("SCHEDULING_TIMEZONE", "America/Sao_Paulo", "Process")
  [Environment]::SetEnvironmentVariable("PYTHONPATH", $backendRoot, "Process")

  $null = Invoke-CheckedNative "docker" @(
    "run", "--detach", "--rm", "--name", $containerName,
    "--pull=never",
    "--env", "POSTGRES_DB=barbearia_backup_test",
    "--env", "POSTGRES_USER=barbearia_backup_test",
    "--env", "POSTGRES_PASSWORD",
    "--publish", "127.0.0.1::5432",
    $image
  )
  $containerStarted = $true

  $portOutput = Invoke-CheckedNative "docker" @("port", $containerName, "5432/tcp")
  $portMatch = [regex]::Match(($portOutput -join "`n"), "127\.0\.0\.1:(\d+)")
  if (-not $portMatch.Success) {
    throw "The temporary PostgreSQL container did not bind to a loopback-only port."
  }
  $port = $portMatch.Groups[1].Value
  $databaseUrl = "postgresql+psycopg://barbearia_backup_test:$testPassword@127.0.0.1:$port/barbearia_backup_test"
  [Environment]::SetEnvironmentVariable("DATABASE_URL", $databaseUrl, "Process")

  $ready = $false
  for ($attempt = 0; $attempt -lt 45; $attempt++) {
    $null = & docker exec $containerName pg_isready -U barbearia_backup_test -d barbearia_backup_test 2>$null
    if ($LASTEXITCODE -eq 0) {
      $ready = $true
      break
    }
    Start-Sleep -Seconds 1
  }
  if (-not $ready) {
    throw "The isolated PostgreSQL test container did not become ready."
  }

  Write-Output "Applying Alembic migrations to the isolated source database..."
  Push-Location $backendRoot
  try {
    $null = Invoke-CheckedNative $python @("-m", "alembic", "upgrade", "head")

    $seedCode = @'
from datetime import datetime
from app.database import SessionLocal
from app.models.user import (Appointment, AppointmentStatusEnum, Avaliacao,
    BarbearioServico, BloqueioHorario, InformacaoInstitucional,
    JornadaTrabalho, RoleEnum, Service, User)

with SessionLocal() as db:
    admin = User(nome="Admin Restore Fixture", email="admin.restore@example.test",
        senha_hash="fictional-test-only", role=RoleEnum.ADMIN)
    barber = User(nome="Barber Restore Fixture", email="barber.restore@example.test",
        senha_hash="fictional-test-only", role=RoleEnum.BARBEIRO)
    client = User(nome="Client Restore Fixture", email="client.restore@example.test",
        senha_hash="fictional-test-only", role=RoleEnum.CLIENTE,
        consentimento_lgpd=True)
    service = Service(nome="Restore Fixture Service", preco=35.0, duracao_minutos=30)
    db.add_all([admin, barber, client, service])
    db.flush()
    appointment = Appointment(user_id=client.id, nome_cliente=client.nome,
        service_id=service.id, barbeiro_id=barber.id,
        data_hora=datetime(2030, 1, 2, 10, 0),
        status=AppointmentStatusEnum.CONCLUIDO, preco=35.0,
        duracao_minutos=30, valor_cobrado=35.0)
    db.add_all([
        appointment,
        BarbearioServico(barbeiro_id=barber.id, service_id=service.id),
        JornadaTrabalho(barbeiro_id=barber.id, dia_semana=2,
            hora_inicio="08:00", hora_fim="18:00", ativo=True),
        BloqueioHorario(barbeiro_id=barber.id,
            inicio=datetime(2030, 1, 2, 12, 0), fim=datetime(2030, 1, 2, 12, 30),
            motivo="Fictional restore fixture", tipo="feriado", ativo=True),
        InformacaoInstitucional(nome="Restore Fixture Shop", endereco="Fictional Street",
            telefone="0000000000", horario_funcionamento="08:00-18:00",
            dias_atendimento="Tuesday"),
    ])
    db.flush()
    db.add(Avaliacao(appointment_id=appointment.id, nota=5,
        comentario="Fictional restore fixture", oculta=False))
    db.commit()
'@
    [IO.File]::WriteAllText($seedScriptPath, $seedCode, [Text.UTF8Encoding]::new($false))
    $null = Invoke-CheckedNative $python @($seedScriptPath)

    $snapshotCode = @'
import json
from sqlalchemy import inspect, text
from app.database import engine

inspector = inspect(engine)
tables = sorted(inspector.get_table_names())
schema = {}
with engine.connect() as connection:
    counts = {table: connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar_one()
        for table in tables}
    revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    fixture = connection.execute(text("""
        SELECT u.email, b.email, s.nome, a.status, a.preco, a.duracao_minutos
        FROM appointments a JOIN users u ON u.id = a.user_id
        JOIN users b ON b.id = a.barbeiro_id JOIN services s ON s.id = a.service_id
        WHERE u.email = 'client.restore@example.test'
    """)).one()
    orphan_appointments = connection.execute(text("""
        SELECT count(*) FROM appointments a
        LEFT JOIN users u ON u.id = a.user_id LEFT JOIN users b ON b.id = a.barbeiro_id
        LEFT JOIN services s ON s.id = a.service_id
        WHERE (a.user_id IS NOT NULL AND u.id IS NULL) OR b.id IS NULL OR s.id IS NULL
    """)).scalar_one()
    if orphan_appointments:
        raise RuntimeError("Restored appointment foreign-key query failed")

for table in tables:
    schema[table] = {
        "indexes": sorted(inspector.get_indexes(table), key=lambda item: item["name"] or ""),
        "foreign_keys": sorted(inspector.get_foreign_keys(table), key=lambda item: item["name"] or ""),
        "unique_constraints": sorted(inspector.get_unique_constraints(table), key=lambda item: item["name"] or ""),
        "check_constraints": sorted(inspector.get_check_constraints(table), key=lambda item: item["name"] or ""),
        "primary_key": inspector.get_pk_constraint(table),
    }

if counts.get("users") != 3 or counts.get("appointments") != 1 or counts.get("avaliacoes") != 1:
    raise RuntimeError("Fictional restore fixture row counts do not match")
print(json.dumps({"counts": counts, "revision": revision,
    "fixture": list(fixture), "schema": schema}, sort_keys=True, separators=(",", ":")))
'@
    [IO.File]::WriteAllText($snapshotScriptPath, $snapshotCode, [Text.UTF8Encoding]::new($false))
    $sourceSnapshotOutput = Invoke-CheckedNative $python @($snapshotScriptPath)
    $sourceSnapshot = ($sourceSnapshotOutput | Select-Object -Last 1).ToString().Trim()

    Write-Output "Creating and restoring a custom-format backup into a second isolated *_test database..."
    $null = Invoke-CheckedNative "docker" @("exec", $containerName, "pg_dump", "-U", "barbearia_backup_test", "--format=custom", "--file=/tmp/barbearia-backup.dump", "barbearia_backup_test")
    $null = Invoke-CheckedNative "docker" @("cp", "${containerName}:/tmp/barbearia-backup.dump", $backupPath)
    if ((Get-Item -LiteralPath $backupPath).Length -le 0) {
      throw "The isolated PostgreSQL backup artifact is empty."
    }
    $null = Invoke-CheckedNative "docker" @("exec", $containerName, "createdb", "-U", "barbearia_backup_test", "barbearia_backup_restore_test")
    $null = Invoke-CheckedNative "docker" @("cp", $backupPath, "${containerName}:/tmp/barbearia-backup-restore.dump")
    $null = Invoke-CheckedNative "docker" @("exec", $containerName, "pg_restore", "--exit-on-error", "--no-owner", "-U", "barbearia_backup_test", "--dbname=barbearia_backup_restore_test", "/tmp/barbearia-backup-restore.dump")

    $restoredUrl = "postgresql+psycopg://barbearia_backup_test:$testPassword@127.0.0.1:$port/barbearia_backup_restore_test"
    [Environment]::SetEnvironmentVariable("DATABASE_URL", $restoredUrl, "Process")
    $restoredSnapshotOutput = Invoke-CheckedNative $python @($snapshotScriptPath)
    $restoredSnapshot = ($restoredSnapshotOutput | Select-Object -Last 1).ToString().Trim()
    if ($sourceSnapshot -cne $restoredSnapshot) {
      throw "The restored database differs from the source in rows, Alembic revision, indexes, keys, or constraints."
    }

    Write-Output "Running PostgreSQL migration and booking integration tests in isolated test schemas..."
    [Environment]::SetEnvironmentVariable("BOOKING_TEST_BACKEND", "postgresql", "Process")
    [Environment]::SetEnvironmentVariable("BOOKING_TEST_POSTGRES_URL", $restoredUrl, "Process")
    foreach ($pattern in @("test_schema_migrations.py", "test_postgres_booking_migration.py", "test_booking_integrity.py", "test_booking_temporal.py")) {
      $null = Invoke-CheckedNative $python @("-m", "unittest", "discover", "-s", "tests", "-p", $pattern, "-v")
    }
  }
  finally {
    Pop-Location
  }

  Write-Output "PASS: Alembic-created PostgreSQL schema, fictional records, relationships, indexes, foreign keys, unique/check constraints, and Alembic revision survived pg_dump/pg_restore. PostgreSQL migration/booking tests passed in isolated schemas."
}
finally {
  if ($containerStarted) {
    $null = & docker stop --time 5 $containerName 2>$null
  }
  if (Test-Path -LiteralPath $backupPath) {
    Remove-Item -LiteralPath $backupPath -Force
  }
  foreach ($temporaryScript in @($seedScriptPath, $snapshotScriptPath)) {
    if (Test-Path -LiteralPath $temporaryScript) {
      Remove-Item -LiteralPath $temporaryScript -Force
    }
  }
  foreach ($name in $environmentNames) {
    [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], "Process")
  }
}

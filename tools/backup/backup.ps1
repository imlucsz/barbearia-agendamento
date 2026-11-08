$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$python = if ($env:BACKUP_PYTHON) { $env:BACKUP_PYTHON } else { Join-Path $repoRoot "backend\.venv\Scripts\python.exe" }
$backupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { Join-Path $scriptDir "archive" }

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Install backend requirements in backend/.venv or set BACKUP_PYTHON." }
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $backupDir /inheritance:r /grant:r "${identity}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not restrict backup directory permissions." }
if (-not $env:PGPASSFILE -or -not (Test-Path -LiteralPath $env:PGPASSFILE -PathType Leaf)) { throw "Set PGPASSFILE to a protected PostgreSQL password file." }
& icacls $env:PGPASSFILE /inheritance:r /grant:r "${identity}:F" "*S-1-5-18:F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not restrict PostgreSQL passfile permissions." }
& $python (Join-Path $scriptDir "backup.py") backup
if ($LASTEXITCODE -ne 0) { throw "Encrypted PostgreSQL backup failed." }

$ErrorActionPreference = "Stop"
$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$python = if ($env:BACKUP_PYTHON) { $env:BACKUP_PYTHON } else { Join-Path $repoRoot "backend\.venv\Scripts\python.exe" }
$backupDir = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { Join-Path $scriptDir "archive" }

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Install backend requirements in backend/.venv or set BACKUP_PYTHON." }
if (-not (Test-Path -LiteralPath $backupDir -PathType Container)) { throw "Backup directory does not exist." }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $backupDir /inheritance:r /grant:r "${identity}:(OI)(CI)F" "*S-1-5-18:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not restrict backup directory permissions." }
foreach ($protectedFile in @($env:PGPASSFILE, $env:BACKUP_AGE_IDENTITY_FILE)) {
  if (-not $protectedFile -or -not (Test-Path -LiteralPath $protectedFile -PathType Leaf)) { throw "PGPASSFILE and BACKUP_AGE_IDENTITY_FILE must point to protected files." }
  & icacls $protectedFile /inheritance:r /grant:r "${identity}:F" "*S-1-5-18:F" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Could not restrict restore secret file permissions." }
}
& $python (Join-Path $scriptDir "backup.py") restore-test
if ($LASTEXITCODE -ne 0) { throw "Disposable PostgreSQL restore verification failed." }

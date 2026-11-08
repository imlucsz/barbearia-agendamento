param(
  [Parameter(Mandatory = $true)][string]$Target,
  [Parameter(Mandatory = $true)][string]$Name,
  [Parameter(Mandatory = $true)][string]$ApiUrl
)
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { $python = "python" }
& $python (Join-Path $PSScriptRoot "create.py") $Target --name $Name --api-url $ApiUrl
if ($LASTEXITCODE -ne 0) { throw "Could not create a clean installation scaffold." }

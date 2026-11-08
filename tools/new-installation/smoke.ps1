$ErrorActionPreference = "Stop"
$api = if ($env:API_URL) { $env:API_URL.TrimEnd('/') } else { throw "Set API_URL to the public HTTPS API origin." }
$frontend = if ($env:FRONTEND_URL) { $env:FRONTEND_URL.TrimEnd('/') } else { throw "Set FRONTEND_URL to the public HTTPS site origin." }
foreach ($path in @("/health", "/ready", "/services/")) {
  $response = Invoke-WebRequest -Uri "$api$path" -Method Get -TimeoutSec 8
  if ($response.StatusCode -ne 200) { throw "Smoke check failed: $path" }
}
$page = Invoke-WebRequest -Uri "$frontend/pages/index.html" -Method Get -TimeoutSec 8
if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'id="services-list"') { throw "Public home smoke check failed." }
Write-Output "PASS: health, readiness, public service catalog and home page responded successfully."

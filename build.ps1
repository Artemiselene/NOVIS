$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$zip = Join-Path $root "astra-mind-extension.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path (Join-Path $root "*") -DestinationPath $zip -Force
Write-Host "Built $zip"

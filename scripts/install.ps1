# HALOFLUX for Hermes - one-click installer (Windows, PowerShell 5.1+): copies dashboard\ into <HERMES_HOME>\plugins\haloflux\; no network, no elevation, no config changes, no service restarts.
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $RepoRoot 'dashboard'

if (-not (Test-Path (Join-Path $Src 'manifest.json')) -or -not (Test-Path (Join-Path $Src 'plugin_api.py'))) {
    Write-Error "dashboard\ not found next to scripts\ (looked in $RepoRoot)"
    exit 1
}

$FreshDefault = $false
if ($env:HERMES_HOME) {
    $HermesDir = $env:HERMES_HOME
} else {
    $HermesDir = Join-Path $HOME '.hermes'
    if (-not (Test-Path $HermesDir)) {
        $FreshDefault = $true
    }
}

$PluginsDir = Join-Path $HermesDir 'plugins'
$Dest = Join-Path $PluginsDir 'haloflux'

if (-not (Test-Path $PluginsDir)) {
    New-Item -ItemType Directory -Path $PluginsDir -Force | Out-Null
}

if (Test-Path $Dest) {
    $Ts = Get-Date -Format 'yyyyMMddHHmmss'
    $Backup = Join-Path $PluginsDir ("haloflux.bak-" + $Ts)
    Move-Item -Path $Dest -Destination $Backup
    Write-Host "Existing installation backed up to: $Backup"
}

New-Item -ItemType Directory -Path $Dest -Force | Out-Null
Copy-Item -Path $Src -Destination $Dest -Recurse -Force

# Self-check
if (-not (Test-Path (Join-Path $Dest 'dashboard\plugin_api.py'))) {
    Write-Error 'plugin_api.py missing after copy'
    exit 1
}
$ManifestPath = Join-Path $Dest 'dashboard\manifest.json'
if (-not (Test-Path $ManifestPath)) {
    Write-Error 'manifest.json missing after copy'
    exit 1
}
$Manifest = Get-Content -Raw -Path $ManifestPath | ConvertFrom-Json
Write-Host "Installed HALOFLUX for Hermes v$($Manifest.version) -> $Dest"

if ($FreshDefault) {
    Write-Host "Note: no existing Hermes directory was detected; installed to the default path $HermesDir."
}

Write-Host 'Next steps:'
Write-Host '  1. Restart hermes-dashboard so it picks up the plugin.'
Write-Host '  2. Open /haloflux in your dashboard.'
Write-Host '  3. If you are not logged in yet, log in to the dashboard first.'

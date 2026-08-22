[CmdletBinding()]
param(
    [ValidateSet('ci', 'install')]
    [string]$Command = 'ci',
    [switch]$Official
)

$ErrorActionPreference = 'Stop'
$mirror = 'https://npmmirror.com/mirrors/electron/'
$previousMirror = [Environment]::GetEnvironmentVariable('ELECTRON_MIRROR', 'Process')

try {
    if ($Official) {
        Remove-Item Env:ELECTRON_MIRROR -ErrorAction SilentlyContinue
        Write-Host '[deps] Electron binary source: official GitHub releases'
    }
    else {
        $env:ELECTRON_MIRROR = $mirror
        Write-Host "[deps] Electron binary source: $mirror"
    }

    & npm.cmd $Command
    if ($LASTEXITCODE -ne 0) {
        throw "npm $Command failed with exit code $LASTEXITCODE"
    }
}
finally {
    if ($null -eq $previousMirror) {
        Remove-Item Env:ELECTRON_MIRROR -ErrorAction SilentlyContinue
    }
    else {
        $env:ELECTRON_MIRROR = $previousMirror
    }
}

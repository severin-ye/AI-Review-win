[CmdletBinding()]
param([switch]$SkipBuild)

$ErrorActionPreference = 'Stop'

function Invoke-Checked([string]$Label, [scriptblock]$Command) {
    Write-Host "`n=== $Label ==="
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Invoke-Checked 'TypeScript typecheck' { npm.cmd run typecheck }
Invoke-Checked 'Electron license tests' { npm.cmd run test:license }
Invoke-Checked 'Business backend tests' {
    Push-Location app\server
    try { & .\.venv\Scripts\python.exe -m pytest tests -q }
    finally { Pop-Location }
}
Invoke-Checked 'License center tests' {
    Push-Location app\license-server
    try { & ..\server\.venv\Scripts\python.exe -m pytest tests -q }
    finally { Pop-Location }
}
if (-not $SkipBuild) {
    Invoke-Checked 'Electron build' { npm.cmd run build }
}
Invoke-Checked 'Node dependency audit' { npm.cmd audit --audit-level=low }
Invoke-Checked 'Business backend dependency audit' {
    # 上游截至 2026-07-18 对 X-CLIP 转换器项尚无修复版本；Caret 不加载 X-CLIP。
    & app\server\.venv\Scripts\python.exe -m pip_audit -r app\server\requirements.txt `
        --ignore-vuln PYSEC-2025-217
}
Invoke-Checked 'License center dependency audit' {
    & app\server\.venv\Scripts\python.exe -m pip_audit -r app\license-server\requirements.txt
}
Invoke-Checked 'Codebase boundary check' { & scripts\check-boundaries.ps1 }

if (-not $SkipBuild) {
    $rendererFiles = Get-ChildItem -File out\renderer\assets
    $rendererBytes = ($rendererFiles | Measure-Object -Property Length -Sum).Sum
    Write-Host "`nRenderer assets: $($rendererFiles.Count) files, $rendererBytes bytes"
    $rendererFiles | Sort-Object Length -Descending | Select-Object Name, Length
}

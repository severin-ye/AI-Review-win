$ErrorActionPreference = 'Stop'

$patterns = @(
    '(?i)(from|import)\s+legacy',
    '(?i)(require|import)\s*\([^)]*(legacy|archive)',
    '(?i)(legacy|archive)[\\/].*\.(py|ts|tsx|js|jsx)$'
)

$violations = @()
foreach ($pattern in $patterns) {
    $matches = & rg -n --pcre2 $pattern app `
        --glob '*.py' --glob '*.ts' --glob '*.tsx' --glob '*.js' --glob '*.jsx' 2>$null
    if ($LASTEXITCODE -eq 0) {
        $violations += $matches
    }
    elseif ($LASTEXITCODE -ne 1) {
        throw "rg boundary check failed with exit code $LASTEXITCODE"
    }
}

if ($violations.Count -gt 0) {
    Write-Error ("app/ must not depend on legacy/ or archive/:`n" + ($violations -join "`n"))
}

$builderConfig = Get-Content -LiteralPath 'electron-builder.yml' -Raw
if ($builderConfig -match '(?m)^\s*-\s+(legacy|archive)(/|\\|\*\*)') {
    throw 'electron-builder files must not package legacy/ or archive/'
}

Write-Host '[boundaries] PASS: app/ is isolated; desktop package excludes legacy/ and archive/'
exit 0

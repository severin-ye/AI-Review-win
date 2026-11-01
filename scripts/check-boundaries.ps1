$ErrorActionPreference = 'Stop'

$patterns = @(
    '(?i)(from|import)\s+legacy',
    '(?i)(require|import)\s*\([^)]*(legacy|archive)',
    '(?i)(legacy|archive)[\\/].*\.(py|ts|tsx|js|jsx)$'
)

$violations = @()
# Git is already required for checkout; do not assume CI also provides ripgrep.
# Include untracked source files while respecting .gitignore (venv/data/build).
$sourceFiles = & git -c core.quotePath=false ls-files --cached --others --exclude-standard -- app
if ($LASTEXITCODE -ne 0) {
    throw "git boundary file listing failed with exit code $LASTEXITCODE"
}
$sourceFiles = @($sourceFiles | Where-Object { $_ -match '\.(py|ts|tsx|js|jsx)$' })
if ($sourceFiles.Count -gt 0) {
    $violations = @(Select-String -LiteralPath $sourceFiles -Pattern $patterns)
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

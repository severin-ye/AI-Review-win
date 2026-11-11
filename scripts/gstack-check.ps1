# Windows boundary only: gstack owns execution, freshness and reuse policy.
function Invoke-GstackCheck {
  param([Parameter(Mandatory=$true)][string]$Label, [Parameter(Mandatory=$true)][string]$Command, [switch]$CheckOnly)
  $evidence=Join-Path $env:USERPROFILE '.codex/skills/gstack/bin/gstack-evidence'
  if($env:GSTACK_EVIDENCE) { $evidence=$env:GSTACK_EVIDENCE }
  if(!(Test-Path -LiteralPath $evidence -PathType Leaf)) { throw "gstack-evidence is missing: $evidence. Restore the installed gstack tool; no local check bypass is available." }
  if(!(Get-Command bun -ErrorAction SilentlyContinue)) { throw 'Bun is required by the installed gstack-evidence tool.' }
  # gstack executes shell strings through Git Bash. Encode the PowerShell child
  # to preserve Windows/Unicode paths and quotes without shell interpolation.
  $scriptText='$ErrorActionPreference="Stop"; $global:LASTEXITCODE=0; ' + $Command + "`n" + 'if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }'
  $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($scriptText))
  $exactCommand="powershell.exe -NoProfile -NonInteractive -EncodedCommand $encoded"
  if(!$CheckOnly) {
    & bun --no-env-file --config=NUL $evidence run --reuse --max-age 24 --label $Label -- $exactCommand
    if($LASTEXITCODE -ne 0) { throw "gstack check failed: $Label ($LASTEXITCODE)" }
  }
  # run is transparent on bookkeeping failures, so the explicit freshness check
  # is necessary before the caller may package or publish.
  & bun --no-env-file --config=NUL $evidence check --max-age 24 --label $Label --expect-cmd $exactCommand
  if($LASTEXITCODE -ne 0) { throw "gstack evidence is missing or stale: $Label" }
}

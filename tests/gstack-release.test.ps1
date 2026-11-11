param([switch]$Integration)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$helper=Join-Path $project 'scripts/gstack-check.ps1'
. $helper
foreach($file in @($helper,(Join-Path $project 'scripts/finalize-delivery.ps1'))){
  $errors=$null; $tokens=$null
  [void][Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
  if($errors.Count){throw ($errors | Out-String)}
}
$priorEvidence=$env:GSTACK_EVIDENCE
try {
  $env:GSTACK_EVIDENCE=Join-Path $project 'missing-gstack-evidence'
  $blocked=$false
  try { Invoke-GstackCheck -Label missing -Command "throw 'must never execute'" } catch { $blocked=$_.Exception.Message -match 'gstack-evidence is missing' }
  if(!$blocked){throw 'Missing gstack did not fail closed'}
} finally { $env:GSTACK_EVIDENCE=$priorEvidence }
$source=Get-Content (Join-Path $project 'scripts/finalize-delivery.ps1') -Raw
foreach($label in @('caret-typecheck','caret-license-tests','caret-license-server-tests','caret-boundaries')){if(!$source.Contains("-Label '$label'")){throw "Missing $label"}}
if($source -notmatch '-CheckOnly:\$SkipValidation' -or $source -match 'if \(-not \$SkipValidation\)'){throw 'SkipValidation bypass remains'}
foreach($guard in @('package-smoke.ps1','.data','Compare-Object','ComputeHash')){if(!$source.Contains($guard)){throw "Missing native guard $guard"}}
$boundary=Get-Content $helper -Raw
if($boundary -notmatch 'run --reuse --max-age 24' -or $boundary -notmatch 'check --max-age 24 --label \$Label --expect-cmd \$exactCommand'){throw 'Evidence age/command contract missing'}
if($Integration){
  # Owned, bounded fixture only; no app data, credentials, native build or release.
  $root=Join-Path $project '.agent-status/gstack-adapter-fixture'
  if(Test-Path -LiteralPath $root){throw "Fixture already exists: $root"}
  New-Item -ItemType Directory -Path $root -Force | Out-Null
  $priorState=$env:GSTACK_STATE_ROOT
  try {
    $env:GSTACK_STATE_ROOT=Join-Path $root 'ledger'
    [IO.File]::WriteAllText((Join-Path $root '.gitignore'),"ledger/`n")
    [IO.File]::WriteAllText((Join-Path $root 'sample.test.js'),"import {test,expect} from 'bun:test'; test('controlled evidence fixture',()=>expect(2+2).toBe(4));")
    Push-Location $root
    try {
      & git init --quiet; if($LASTEXITCODE){throw 'fixture git init'}
      & git add .gitignore sample.test.js
      & git -c user.name=AdapterFixture -c user.email=fixture@example.invalid commit --quiet -m fixture
      if($LASTEXITCODE){throw 'fixture commit'}
      $blocked=$false
      try { Invoke-GstackCheck -Label missing-evidence -Command "throw 'must not execute'" -CheckOnly } catch { $blocked=$_.Exception.Message -match 'evidence is missing or stale' }
      if(!$blocked){throw 'Check-only missing evidence was accepted'}
      Invoke-GstackCheck -Label adapter-fixture -Command 'bun test sample.test.js'
      Invoke-GstackCheck -Label adapter-fixture -Command 'bun test sample.test.js'
      $blocked=$false
      try { Invoke-GstackCheck -Label adapter-failure -Command 'exit 7' } catch { $blocked=$_.Exception.Message -match 'gstack check failed' }
      if(!$blocked){throw 'Nonzero child was accepted'}
    } finally { Pop-Location }
  } finally { $env:GSTACK_STATE_ROOT=$priorState }
  Write-Output "PASS real evidence fixture (retained for coordinator review): $root"
}
Write-Output 'PASS gstack release adapter parsing, missing-tool refusal and release wiring'

$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$entry=Join-Path $project 'scripts/finalize-delivery.ps1'
$owned=Join-Path $project '.agent-status/finalize-contract-fixture'
if(Test-Path -LiteralPath $owned){throw 'Owned fixture already exists'}
foreach($scenario in @('skip','generic-failure','private-data')) {
  $root=Join-Path $owned $scenario
  $scripts=Join-Path $root 'scripts'
  $package=Join-Path $root 'release/Caret-交付包-v1.0.0'
  New-Item -ItemType Directory -Path $scripts,(Join-Path $package '1-授权端'),(Join-Path $package '2-客户端'),(Join-Path $root 'docs/releases') -Force | Out-Null
  Copy-Item -LiteralPath $entry -Destination (Join-Path $scripts 'finalize-delivery.ps1')
  [IO.File]::WriteAllText((Join-Path $root 'package.json'),'{"version":"1.0.0"}')
  [IO.File]::WriteAllText((Join-Path $root 'docs/releases/Caret-v1.0.0-更新日志.md'),"第一部分：业务改进（通俗版）`n第二部分：技术修改详情")
  foreach($name in @('README-请先读我.txt','1-授权端/Caret License Center.exe','1-授权端/授权管理指南.pdf','2-客户端/Caret Setup 1.0.0.exe','2-客户端/使用指南.pdf')){[IO.File]::WriteAllText((Join-Path $package $name),'fixture')}
  $mock=@'
function Invoke-GstackCheck {
  param([string]$Label,[string]$Command,[switch]$CheckOnly)
  Add-Content -LiteralPath './calls' -Value "$Label|$CheckOnly"
  if((Split-Path (Get-Location) -Leaf) -eq 'generic-failure'){throw 'generic blocked'}
}
'@
  [IO.File]::WriteAllText((Join-Path $scripts 'gstack-check.ps1'),$mock)
  [IO.File]::WriteAllText((Join-Path $scripts 'package-smoke.ps1'),"param(`$DataDir,`$ExpectedVersion)`nSet-Content -LiteralPath './smoke-called' -Value called`nexit 9")
  if($scenario -eq 'private-data'){New-Item -ItemType Directory -Path (Join-Path $package '.data') | Out-Null}
  Push-Location $root
  try {
    $caught=''
    try { & (Join-Path $scripts 'finalize-delivery.ps1') -SkipValidation:($scenario -eq 'skip') } catch {$caught=$_.Exception.Message}
    if($scenario -eq 'skip') {
      if($caught -notmatch '烟测失败' -or !(Test-Path './smoke-called')){throw 'SkipValidation bypassed native smoke'}
      $calls=@(Get-Content './calls');if($calls.Count -ne 4 -or @($calls | Where-Object {$_ -notmatch '\|True$'}).Count){throw 'SkipValidation did not require all check-only lanes'}
    } elseif($scenario -eq 'generic-failure') {
      if($caught -ne 'generic blocked' -or (Test-Path './smoke-called')){throw 'Generic failure did not stop before native/ZIP work'}
    } else {
      if($caught -notmatch '\.data' -or (Test-Path './calls') -or (Test-Path './smoke-called')){throw 'Private data guard missing'}
    }
    if(Get-ChildItem -LiteralPath './release' -Filter '*.zip'){throw 'Failure path produced final ZIP'}
  } finally { Pop-Location }
}
Write-Output 'PASS actual finalize script: check-only cannot skip smoke, generic failure stops, .data rejected, no final ZIP side effects'

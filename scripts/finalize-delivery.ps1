param(
    [string]$Version = "",
    [string]$PackageDir = "",
    [string]$ReleaseNote = "",
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath ".").Path
$packageJson = Get-Content -LiteralPath (Join-Path $repo "package.json") -Raw | ConvertFrom-Json
if (-not $Version) { $Version = [string]$packageJson.version }
if ([string]$packageJson.version -ne $Version) {
    throw "版本不一致：package.json=$($packageJson.version)，请求导出=$Version"
}

$releaseRoot = Join-Path $repo "release"
if (-not $PackageDir) { $PackageDir = Join-Path $releaseRoot "Caret-交付包-v$Version" }
if (-not $ReleaseNote) { $ReleaseNote = Join-Path $repo "docs\releases\Caret-v$Version-更新日志.md" }
$PackageDir = [System.IO.Path]::GetFullPath($PackageDir)
$ReleaseNote = [System.IO.Path]::GetFullPath($ReleaseNote)

if (-not $PackageDir.StartsWith($releaseRoot + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "交付包目录必须位于 release 下：$PackageDir"
}
if (-not (Test-Path -LiteralPath $PackageDir -PathType Container)) { throw "交付包目录不存在：$PackageDir" }
if (-not (Test-Path -LiteralPath $ReleaseNote -PathType Leaf)) { throw "缺少版本更新日志：$ReleaseNote" }

$noteText = Get-Content -LiteralPath $ReleaseNote -Raw
foreach ($heading in @("第一部分：业务改进（通俗版）", "第二部分：技术修改详情")) {
    if (-not $noteText.Contains($heading)) { throw "更新日志缺少必需章节：$heading" }
}

$requiredFiles = @(
    "README-请先读我.txt",
    "1-授权端\Caret License Center.exe",
    "1-授权端\授权管理指南.pdf",
    "2-客户端\Caret Setup $Version.exe",
    "2-客户端\使用指南.pdf"
)
foreach ($relative in $requiredFiles) {
    $path = Join-Path $PackageDir $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "交付包缺少文件：$relative" }
}

$forbiddenData = @(Get-ChildItem -LiteralPath $PackageDir -Recurse -Force | Where-Object { $_.Name -eq ".data" })
if ($forbiddenData.Count -gt 0) { throw "干净交付包不得包含运行时 .data：$($forbiddenData.FullName -join ', ')" }

if (-not $SkipValidation) {
    & npm.cmd run typecheck
    if ($LASTEXITCODE -ne 0) { throw "TypeScript 类型检查失败" }
    & npm.cmd run test:license
    if ($LASTEXITCODE -ne 0) { throw "客户端许可证测试失败" }
    & (Join-Path $repo "app\server\.venv\Scripts\python.exe") -m pytest `
        (Join-Path $repo "app\license-server\tests") -q
    if ($LASTEXITCODE -ne 0) { throw "授权端测试失败" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "scripts\check-boundaries.ps1")
    if ($LASTEXITCODE -ne 0) { throw "新旧代码边界检查失败" }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $smokeDir = Join-Path $releaseRoot "构建中间文件\v$Version\发布前烟测-$stamp"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "scripts\package-smoke.ps1") `
        -DataDir $smokeDir -ExpectedVersion $Version
    if ($LASTEXITCODE -ne 0) { throw "打包产物烟测失败" }
}

Copy-Item -LiteralPath $ReleaseNote -Destination (Join-Path $PackageDir "更新日志.md") -Force

$zipPath = Join-Path $releaseRoot "Caret-交付包-v$Version.zip"
if (Test-Path -LiteralPath $zipPath) {
    $archiveDir = Join-Path $releaseRoot "构建中间文件\v$Version\历次定稿ZIP"
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Move-Item -LiteralPath $zipPath -Destination (Join-Path $archiveDir "Caret-交付包-v$Version-$stamp.zip")
}

Compress-Archive -LiteralPath $PackageDir -DestinationPath $zipPath -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf)) { throw "ZIP 未生成：$zipPath" }

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $rootName = Split-Path -Leaf $PackageDir
    $expected = @(Get-ChildItem -LiteralPath $PackageDir -Recurse -File | ForEach-Object {
        $relative = $_.FullName.Substring($PackageDir.Length).TrimStart("\").Replace("\", "/")
        "$rootName/$relative"
    })
    $entries = @($zip.Entries | Where-Object { $_.Name } | ForEach-Object { $_.FullName })
    $difference = @(Compare-Object $expected $entries)
    if ($difference.Count -gt 0) { throw "ZIP 文件清单与目录不一致：$($difference | Out-String)" }
    foreach ($entry in $zip.Entries | Where-Object { $_.Name }) {
        $stream = $entry.Open()
        try { $stream.CopyTo([System.IO.Stream]::Null) } finally { $stream.Dispose() }
    }
} finally {
    $zip.Dispose()
}

$sha256 = [System.Security.Cryptography.SHA256]::Create()
$zipStream = [System.IO.File]::OpenRead($zipPath)
try {
    $hash = [System.BitConverter]::ToString($sha256.ComputeHash($zipStream)).Replace("-", "")
} finally {
    $zipStream.Dispose()
    $sha256.Dispose()
}
"DELIVERY_FINALIZED=PASS"
"VERSION=$Version"
"PACKAGE_DIR=$PackageDir"
"ZIP=$zipPath"
"ZIP_SHA256=$hash"

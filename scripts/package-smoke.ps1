param(
    [string]$BackendExe = "app/server/dist/ai-review-backend.exe",
    [string]$LicenseExe = "app/license-server/dist/Caret License Center.exe",
    [string]$DataDir = "release/package-smoke-data",
    [string]$ExpectedVersion = ""
)

$ErrorActionPreference = "Stop"
$backend = (Resolve-Path -LiteralPath $BackendExe).Path
$license = (Resolve-Path -LiteralPath $LicenseExe).Path
$ExpectedVersion = if ($ExpectedVersion) {
    $ExpectedVersion
} else {
    (Get-Content -LiteralPath "package.json" -Raw | ConvertFrom-Json).version
}
$data = if ([System.IO.Path]::IsPathRooted($DataDir)) {
    [System.IO.Path]::GetFullPath($DataDir)
} else {
    [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $DataDir))
}
if (Test-Path -LiteralPath $data) { throw "测试目录已存在: $data" }
New-Item -ItemType Directory -Path $data | Out-Null

$backendProcess = $null
$licenseProcess = $null
$startedAt = Get-Date
try {
    $backendProcess = Start-Process -FilePath $backend -ArgumentList @("--port", "18765") -PassThru -WindowStyle Hidden
    $backendHealth = $null
    for ($i = 0; $i -lt 90; $i++) {
        try {
            $backendHealth = Invoke-RestMethod "http://127.0.0.1:18765/api/health" -TimeoutSec 2
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $backendHealth) { throw "打包后端未通过健康检查" }
    if ($backendHealth.version -ne $ExpectedVersion) { throw "打包后端版本错误: $($backendHealth.version)" }

    $env:AI_REVIEW_LICENSE_DATA_DIR = $data
    $env:AI_REVIEW_LICENSE_ADMIN_PORT = "18767"
    $env:AI_REVIEW_LICENSE_EMPLOYEE_PORT = "18768"
    $env:AI_REVIEW_LICENSE_SKIP_FIREWALL = "1"
    $env:AI_REVIEW_LICENSE_DEV_KEYS = "0"
    $licenseProcess = Start-Process -FilePath $license -PassThru -WindowStyle Hidden

    $ping = $null
    for ($i = 0; $i -lt 90; $i++) {
        try {
            $ping = Invoke-RestMethod "http://127.0.0.1:18768/api/v1/ping" -TimeoutSec 2
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ping) { throw "打包授权端员工 API 未启动" }
    if (-not $ping.public_key_pem) { throw "ping 未返回服务器公钥" }

    $createBody = @{
        name = "v$ExpectedVersion smoke"
        validity_mode = "duration"
        duration_days = 7
        max_devices = 1
        features = @("main")
        minimum_client_version = "0.0.0"
    } | ConvertTo-Json
    $created = Invoke-RestMethod "http://127.0.0.1:18767/api/v1/admin/licenses" `
        -Method Post -ContentType "application/json" -Body $createBody
    $copied = Invoke-RestMethod "http://127.0.0.1:18767/api/v1/admin/licenses/$($created.license.id)/key"
    if ($copied.license_key -ne $created.license_key) { throw "再次复制的许可证与创建值不一致" }

    $activateBody = @{
        license_key = $created.license_key
        device_id = "a" * 64
        device_name = "smoke"
        platform = "win32"
        os_version = "Windows"
        client_version = $ExpectedVersion
        session_id = "smoke"
        nonce = [guid]::NewGuid().ToString("N")
    } | ConvertTo-Json
    $activated = Invoke-RestMethod "http://127.0.0.1:18768/api/v1/licenses/activate" `
        -Method Post -ContentType "application/json" -Body $activateBody
    if (-not $activated.public_key_pem -or -not $activated.signature) {
        throw "激活响应缺少公钥或签名"
    }
    $ui = (Invoke-WebRequest "http://127.0.0.1:18767/" -UseBasicParsing).Content
    if ($ui -notmatch "复制许可") { throw "打包管理页缺少复制许可按钮" }

    "BACKEND_SMOKE=PASS version=$($backendHealth.version)"
    "LICENSE_SMOKE=PASS fingerprint=$($ping.key_fingerprint)"
    "COPY_LICENSE_SMOKE=PASS masked=$($created.license.masked_key)"
    "ACTIVATION_PAYLOAD_SMOKE=PASS public_key=$([bool]$activated.public_key_pem)"
    "SMOKE_DATA=$data"
} finally {
    if ($licenseProcess -and -not $licenseProcess.HasExited) {
        Stop-Process -Id $licenseProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    # PyInstaller onefile 启动器会派生同路径的实际服务子进程；按本轮开始时间和精确
    # EXE 路径收尾，避免烟测端口或数据目录继续被占用。
    Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and
        ($_.ExecutablePath -eq $backend -or $_.ExecutablePath -eq $license) -and
        $_.CreationDate -ge $startedAt.AddSeconds(-1)
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

# 许可证系统运行说明（Runbook）

> 命令以 Windows PowerShell 为准（Git Bash 亦可，差异处另行注明）。路径均相对仓库根。

## 一、老板端（许可证服务器）

### 1. 安装依赖

服务器复用员工后端的 venv（`app/server/.venv`）。首次使用在共享 venv 中补装依赖：

```powershell
cd app\license-server
..\server\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Windows 下私钥 DPAPI 保护需要 pywin32：
..\server\.venv\Scripts\python.exe -m pip install cryptography pywin32
```

### 2. 开发密钥生成

**无需手动生成**：首次启动时 `KeyManager.load_or_create()` 自动在数据目录生成 Ed25519 密钥对：

- Windows 且有 win32crypt → 私钥经 DPAPI(CryptProtectData) 加密存 `.data\keys\private.key.bin`；
- 否则明文 `.data\keys\private_key.pem` + 醒目警告日志（仅开发可用）；
- 公钥始终存 `.data\keys\public_key.pem`。
- 默认 DEV 模式（`AI_REVIEW_LICENSE_DEV_KEYS=1`）。生产部署显式设 `$env:AI_REVIEW_LICENSE_DEV_KEYS="0"`。

### 3. 启动服务器

```powershell
cd app\license-server
..\server\.venv\Scripts\python.exe run.py
```

- 管理 UI：<http://127.0.0.1:8767/>（仅本机；启动后自动打开浏览器）
- 员工 API：`http://0.0.0.0:8768/api/v1`
- 停止：`Ctrl+C`（管理页"停止员工端监听"只停 8768，管理进程仍在）。

端口/目录覆盖（环境变量，前缀 `AI_REVIEW_LICENSE_`）：

```powershell
$env:AI_REVIEW_LICENSE_ADMIN_PORT="8777"         # 管理端口（默认 8767，仅本机）
$env:AI_REVIEW_LICENSE_EMPLOYEE_PORT="8788"      # 员工端口（默认 8768）
$env:AI_REVIEW_LICENSE_EMPLOYEE_HOST="0.0.0.0"   # 员工监听地址
$env:AI_REVIEW_LICENSE_DATA_DIR="D:\airev-license-data"  # 数据目录
```

### 4. 查看员工连接地址

管理页顶部仪表盘显示「员工连接地址」（`http://<局域网IP>:8768`），一键复制发给员工。
也可命令行查看本机 IP：`ipconfig` 中的 IPv4 地址。员工端连通性自测：

```powershell
Invoke-RestMethod http://<服务器IP>:8768/api/v1/ping
# 返回 success / server_time / key_fingerprint / dev / server_version
```

### 5. 创建第一个许可证

**方式 A：管理 UI** —— 打开 <http://127.0.0.1:8767/> →「新建许可证」→ 填有效期/设备数 →
创建后**立即复制完整密钥**（`AIREV-XXXX-XXXX-XXXX`，只显示这一次）。

**方式 B：curl（PowerShell 用 Invoke-RestMethod）**：

```powershell
$resp = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8767/api/v1/admin/licenses `
  -ContentType 'application/json' `
  -Body '{"name":"测试许可证","validity_mode":"duration","duration_days":365,"max_devices":3}'
$resp.license_key   # 明文密钥仅此一次返回
```

其它常用管理操作（均有对应 UI 按钮）：

```powershell
$licId = $resp.license.id
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8767/api/v1/admin/licenses/$licId/suspend -ContentType 'application/json' -Body '{}'            # 暂停
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8767/api/v1/admin/licenses/$licId/resume  -ContentType 'application/json' -Body '{}'            # 恢复
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8767/api/v1/admin/licenses/$licId/revoke  -ContentType 'application/json' -Body '{"reason":"离职"}' # 撤销
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8767/api/v1/admin/licenses/$licId/renew   -ContentType 'application/json' -Body '{"extend_days":365}' # 续期
```

撤销/暂停**下一次心跳生效**（员工端默认 300 秒一跳，最大延迟约 5 分钟）。

### 6. 生产部署注意

1. **备份即备份整个 `.data\` 目录**（`license.db` + `keys\`）。私钥丢失 = 所有凭证无法验签，
   只能重新生成密钥对并全员重新激活。
2. 生产设 `$env:AI_REVIEW_LICENSE_DEV_KEYS="0"` 关闭 DEV 标记。
3. Windows 防火墙放行员工端口（管理员 PowerShell，一次即可）：

   ```powershell
   netsh advfirewall firewall add rule name="AI-Review License Server" dir=in action=allow protocol=TCP localport=8768
   ```

4. 管理页「设置 → 危险操作 → 重新生成密钥对」会使**所有已签发凭证立即失效**，慎用。
5. 打包成 exe（可选）：`..\server\.venv\Scripts\python.exe -m PyInstaller ai-review-license-server.spec --noconfirm` → `dist\ai-review-license-server.exe`。

## 二、员工端

### 1. 开发模式

前置：**license-server 必须在跑**（见上），且员工端公钥已与服务器密钥匹配：

```powershell
# 在 app\license-server 下执行（服务器运行过一次、密钥已生成后）：
..\server\.venv\Scripts\python.exe scripts\export_public_key.py
# → 写 app\desktop\resources\license-public.pem（+ DEV 模式写 license-public.dev.json）
```

启动员工端（仓库根）：

```powershell
npm.cmd run dev    # electron-vite dev：主进程 + preload + 渲染层热更新
```

### 2. 激活

1. 首次启动进入「激活许可证」页。
2. 填**服务器地址**（管理员给的 `http://<局域网IP>:8768`，会记忆保存）；
   可先点「连接测试」（调 `/api/v1/ping`，成功显示服务器时间绿色提示，失败红色）。
3. 填**许可证密钥**（`AIREV-XXXX-XXXX-XXXX`）、设备名（默认本机名）。
4. 点「激活」。成功进入主界面；失败按 reason_code 显示中文错误（与服务端文案一致）。
5. 之后每次启动自动校验本地凭证并后台心跳；「设置 → 许可证」可查看状态、
   立即验证、退出许可证。

### 3. 打包后安装程序

```powershell
npm.cmd run dist:backend   # 先出 app\server\dist\ai-review-backend.exe
npm.cmd run dist           # electron-vite build + electron-builder（NSIS 到 release\）
```

- `electron-builder.yml` 的 extraResources 已包含
  `app\desktop\resources\license-public.pem → license-public.pem`，
  主进程打包后从 `process.resourcesPath\license-public.pem` 读取，无需额外配置。
- **生产构建前必须替换正式公钥**：
  1. 老板端生产环境设 `AI_REVIEW_LICENSE_DEV_KEYS=0` 并生成正式密钥对（备份 `.data\keys\`）；
  2. 运行 `scripts\export_public_key.py` 重新导出公钥；
  3. 确认 `app\desktop\resources\license-public.dev.json` 不再生成（DEV 标注消失）后再打包；
  4. 换公钥后所有员工端需用新包重新激活。

## 三、测试环境加速（心跳改 5 秒等）

员工端配置环境变量（在启动 `npm.cmd run dev` 前设置）：

| 变量 | 默认 | 说明 |
|---|---|---|
| `AI_REVIEW_LICENSE_HEARTBEAT_INTERVAL_SECONDS` | 300 | 心跳周期（测试改 `5`） |
| `AI_REVIEW_LICENSE_REQUEST_TIMEOUT_SECONDS` | 10 | 单次请求超时 |
| `AI_REVIEW_LICENSE_RETRY_DELAYS` | `5,15` | 心跳失败快速重试延迟（逗号分隔秒） |
| `AI_REVIEW_LICENSE_CLOCK_SKEW_TOLERANCE_SECONDS` | 300 | 时间回拨容差 |
| `AI_REVIEW_LICENSE_EXPIRY_WARNINGS` | `259200,86400,3600` | 到期提醒阈值（秒，逗号分隔） |

```powershell
$env:AI_REVIEW_LICENSE_HEARTBEAT_INTERVAL_SECONDS="5"
npm.cmd run dev
```

服务器侧（`AI_REVIEW_LICENSE_` 前缀）：`HEARTBEAT_INTERVAL_SECONDS`（心跳响应建议值）、
`TIMESTAMP_TOLERANCE_SECONDS`（客户端时间戳容差）、`RATE_LIMIT_PER_MINUTE`（activate 限流）、
`LOG_LEVEL` 等，见 `license_server/core/config.py`。

## 四、集成冒烟脚本（scripts/license-smoke.ts）

对真实 license-server 跑 40 项端到端断言（激活/心跳/撤销/验签/断连全链路）。
依赖真实服务器，**不进 vitest 默认套件**，可重复运行（每次运行使用唯一设备 ID）。

```powershell
# 1. 另开终端启动 license-server（见上），确认：
Invoke-RestMethod http://127.0.0.1:8768/api/v1/ping

# 2. 仓库根打包并运行：
node_modules\.bin\esbuild scripts\license-smoke.ts --bundle --platform=node --format=esm `
  --outfile=scripts\.license-smoke.bundle.mjs `
  "--banner:js=import { createRequire } from 'module'; const require = createRequire(import.meta.url);"
node scripts\.license-smoke.bundle.mjs

# 3. 结束后：停掉 license-server；临时 bundle 已被 .gitignore 覆盖，可删可不删
```

注意：冒烟会在开发 `.data` 中留下已撤销的测试许可证（无害，管理页可见可删）。

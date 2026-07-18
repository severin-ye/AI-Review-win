# 句读授权中心（授权端）

许可证核心库 + 许可证服务器（员工 API + 管理 API）+ 内置 Web 管理界面。
技术栈与 app/server 对齐：Python 3.12 + FastAPI + SQLModel(SQLite) + pydantic-settings。

## 运行（老板端）

```bash
cd app/license-server
# 首次：在共享 venv 中补装依赖
../server/.venv/Scripts/python.exe -m pip install cryptography pywin32
# 启动（同进程起两个监听，并自动打开管理页）
../server/.venv/Scripts/python.exe run.py
```

- 管理页：<http://127.0.0.1:8767/>（仅本机，可用 `AI_REVIEW_LICENSE_ADMIN_HOST/PORT` 改）
- 员工 API：`http://0.0.0.0:8768`（可用 `AI_REVIEW_LICENSE_EMPLOYEE_HOST/PORT` 改）
- 首次启动自动生成 Ed25519 密钥对到 `.data/keys/`（Windows 下私钥经 DPAPI 加密存
  `private.key.bin`；无 win32crypt 时明文 `private_key.pem` + 醒目警告，仅开发用）。
- 数据目录默认 `app/license-server/.data`（SQLite + 密钥 + 运行时配置），可用
  `AI_REVIEW_LICENSE_DATA_DIR` 覆盖。**`.data/` 已加入 .gitignore，私钥不会入库。**

## 员工连接地址

管理页顶部仪表盘显示「员工连接地址」（`http://<局域网IP>:8768`），一键复制发给员工；
也可在员工端调用 `GET /api/v1/ping` 做连通测试（返回 server_time 与公钥指纹）。

## Windows 防火墙放行

- **打包 exe**：首次启动自动检查放行规则（规则名 `Caret License Server`），缺失时
  弹一次「用户账户控制」(UAC) 提权窗口自动添加，点「是」即可；取消或失败只记警告，
  **不阻断服务器启动**。之后每次启动复查，规则已存在则静默跳过。
- 设 `AI_REVIEW_LICENSE_SKIP_FIREWALL=1` 可完全跳过自动放行（自动化测试/特殊部署用）。
- **源码运行不触发自动放行**；提权失败时的兜底做法：管理员 PowerShell 手动执行一次——

```powershell
netsh advfirewall firewall add rule name="Caret License Server" dir=in action=allow protocol=TCP localport=8768
```

## 公钥导出（员工端验签内嵌）

```bash
../server/.venv/Scripts/python.exe scripts/export_public_key.py
# → app/desktop/resources/license-public.pem
# DEV 模式下额外写 license-public.dev.json 标注（仅开发联调，生产构建前必须重新导出）
```

## 生产密钥与备份

- 生产部署：设 `AI_REVIEW_LICENSE_DEV_KEYS=0`；首次启动前备份 `.data/keys/`。
- **备份即备份整个 `.data/` 目录**（license.db + keys/）。私钥丢失 = 所有凭证无法验签，
  只能重新生成密钥对并全员重新激活。
- 管理页「设置 → 危险操作 → 重新生成密钥对」会使所有已签发凭证立即失效，慎用。

## 测试

```bash
cd app/license-server
../server/.venv/Scripts/python.exe -m pytest tests/ -q
```

测试使用独立临时数据目录与注入时钟，不依赖网络与真实时间。
`tests/vectors/license_vectors.json` 为员工端 TS 对拍向量（canonical 字符串、签名、公钥、篡改用例）。

## 打包（后续统一打，当前只提供 spec）

```bash
../server/.venv/Scripts/python.exe -m pip install pyinstaller
../server/.venv/Scripts/python.exe -m PyInstaller ai-review-license-server.spec --noconfirm
# → dist/句读授权中心.exe
```

## 员工端协议速览

- 激活 `POST /api/v1/licenses/activate`；心跳 `POST /api/v1/licenses/heartbeat`；
  刷新 `POST /api/v1/licenses/refresh`；连通 `GET /api/v1/ping`。
- 凭证 = `{"license": {...}, "signature": base64}`；签名对象 = token 的 canonical JSON：
  `JSON.stringify` 键递归排序、无空白、UTF-8 原样非 ASCII（详见 vectors）。
- 心跳响应同样带 signature（对响应体除 signature 外 canonical 签名）。
- 心跳返回 `refresh_required: true` 时调用 refresh 取新凭证。

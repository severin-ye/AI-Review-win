# 许可证任务修改文件清单（阶段 2–6）

> 只列本许可证任务（老板端许可证服务器 + 员工端许可证接入）相关改动；
> 方案 D 重构等许可证系统之外的早期改动不在此列。
> 状态标记：🆕 新建 / ✏️ 修改。

## 1. 老板端许可证服务器 `app/license-server/`（🆕 全部新建，阶段 2–4）

| 路径 | 内容 | 原因 |
|---|---|---|
| `run.py` | 薄入口（`license_server.run:main`） | 启动脚本 |
| `requirements.txt` | fastapi / uvicorn / sqlmodel / pydantic-settings / cryptography 等 | 服务器依赖 |
| `README.md` | 服务器运行/测试/打包/协议速览 | 使用文档 |
| `ai-review-license-server.spec` | PyInstaller 打包规格 | 后续打 exe |
| `license_server/main.py` | 组装 admin / employee 两个 FastAPI app，lifespan 内 `init_db()` | 应用入口 |
| `license_server/run.py` | 单进程双监听（admin 127.0.0.1:8767 / employee 0.0.0.0:8768），管理 API 可启停员工监听 | 运行方式 |
| `license_server/version.py` | 版本号 | ping 响应用 |
| `license_server/schemas.py` | 请求/响应模型、ErrorCode 错误码全集、ERROR_MESSAGES 中文文案、EventType、管理 API 模型与序列化辅助 | 协议契约（员工端文案以此为准） |
| `license_server/crypto.py` | canonical JSON、Ed25519 签名/验签、License Key 生成/SHA256 哈希/规整、版本比较 | 密码学原语 |
| `license_server/core/config.py` | pydantic-settings（`AI_REVIEW_LICENSE_` 前缀），数据目录/端口/DEV 标记/限流/心跳间隔/时间容差 | 运行配置 |
| `license_server/core/db.py` | SQLModel engine 缓存 + `init_db()` 自动建表 | 存储 |
| `license_server/core/keys.py` | Ed25519 密钥对管理：首启自动生成；Windows DPAPI 存 `private.key.bin`，否则明文 PEM+警告；公钥指纹；危险 regenerate | 密钥生命周期 |
| `license_server/core/timeutil.py` | UTC 时间工具、ISO Z 序列化、回拨/偏差检测 | 时间一致性 |
| `license_server/models/tables.py` | License / Device / LicenseEvent 三表 | 数据模型 |
| `license_server/api/employee.py` | 员工 API：activate / heartbeat / refresh / ping，统一事务包裹，activate 固定窗口限流 | 员工协议端点 |
| `license_server/api/admin.py` | 管理 API：许可证 CRUD、renew/suspend/resume/revoke、设备解绑、事件查询、服务器状态/启停/配置/公钥/重生成密钥 | 管理端点 |
| `license_server/api/ratelimit.py` | 固定窗口限流器（每 IP 10 次/分，activate 用） | 防爆破 |
| `license_server/services/activation.py` | 激活服务：幂等、设备上限、模式 A/B 有效期、最低版本 | 业务逻辑 |
| `license_server/services/heartbeat.py` | 心跳/刷新服务：时间戳窗口、设备链校验、nonce 防重放、状态优先级、签名响应 | 业务逻辑 |
| `license_server/services/license_ops.py` | 许可证 CRUD、懒过期（lazy expiry）、事件记录 | 业务逻辑 |
| `license_server/services/token.py` | token 构建、凭证签发（签 token）、心跳响应签名（签整响应体）、客户端镜像体检 | 签名凭证 |
| `license_server/api/__init__.py` 等包标识 | — | 包结构 |
| `scripts/export_public_key.py` | 导出公钥到 `app/desktop/resources/license-public.pem`；DEV 模式额外写 `license-public.dev.json` 标注 | 公钥分发 |
| `tests/conftest.py`、`test_crypto.py`（11）、`test_core.py`（9）、`test_api.py`（28）、`test_scenarios.py`（6） | 54 个 pytest 用例 | 服务端测试 |
| `tests/vectors/license_vectors.json` + `tests/vectors/_generate.py` | 4 组 canonical/签名对拍向量（含篡改用例） | 员工端验签对拍基准 |

### 增补：Windows 防火墙自动放行（打包 exe 首启提权）

| 路径 | 状态 | 内容 / 原因 |
|---|---|---|
| `license_server/core/firewall.py` | 🆕 | 防火墙规则"先查后建"：netsh show rule 查询（mbcs/utf-8 解码，按输出含端口号判断），缺失时 `ShellExecuteW("runas")` UAC 提权添加，2 秒后复查；取消/失败/异常均只记警告、不阻断启动；仅 win32 + frozen 且 `AI_REVIEW_LICENSE_SKIP_FIREWALL!=1` 时生效 | 老板 exe 首启免手动配防火墙 |
| `license_server/run.py` | ✏️ | `main()` 在启动监听前调用 `ensure_firewall_rule()`；新增 `_effective_employee_port()` 读取 `.data/server_config.json` 运行时端口覆盖，保证放行端口与实际监听端口一致 | 接入防火墙自检 |
| `tests/test_firewall.py` | 🆕 | 12 个 pytest 用例（启用条件 3 / rule_exists 4 / ensure 5），全 mock subprocess/ctypes/sys | 服务端测试（总数 54→66） |

## 2. 员工端主进程 `app/desktop/`（阶段 5 新建 license 模块）

| 路径 | 状态 | 内容 / 原因 |
|---|---|---|
| `main/license/types.ts` | 🆕 | 13 状态、LicenseToken/StoredCredential/LicenseSnapshot 等类型、错误码中文文案（与 schemas.py 同步） |
| `main/license/config.ts` | 🆕 | 心跳 300s/超时 10s/重试 [5,15]/回拨容差 300s/提醒阈值 [3天,1天,1小时]；`AI_REVIEW_LICENSE_*` env 覆盖（测试可改心跳为 5 秒） |
| `main/license/canonical.ts` | 🆕 | 与服务端逐字节一致的 canonical JSON + node:crypto Ed25519 验签（纯函数，vitest 对拍） |
| `main/license/timeGuard.ts` | 🆕 | 时间回拨检测、可信时间推进、到期/剩余时间、提醒档位（纯函数） |
| `main/license/deviceId.ts` | 🆕 | installation secret + 注册表 MachineGuid + "ai-review" → SHA256 device_id（原始 MachineGuid 不出本机） |
| `main/license/storage.ts` | 🆕 | safeStorage(DPAPI) 加密存 `userData/license.dat`；明文降级策略写明；服务器地址记忆小文件 |
| `main/license/publicKey.ts` | 🆕 | 公钥多候选路径加载（开发仓库路径 / 打包 resourcesPath） |
| `main/license/serverClient.ts` | 🆕 | 可注入 fetch 的协议客户端，NetworkError 与 ServerError 分类（连接失败≠撤销的前提） |
| `main/license/licenseService.ts` | 🆕 | 许可证状态机单例：启动决策、心跳并发去重、license_version 单调、激活幂等、refresh_required 自动刷新、离线规则表 |
| `main/license/ipc.ts` | 🆕 | license:* IPC handler + license:stateChanged 推送；Electron 依赖在此装配注入 |
| `main/license/__tests__/`（fakeServer.ts + 5 个 test 文件，阶段 6） | 🆕 | 60 个 vitest 用例（见 [test-report.md](test-report.md)） |
| `main/index.ts` | ✏️ | bootstrap 先 `service.init()` 再注册 IPC；before-quit dispose |
| `preload/index.ts` | ✏️ | 新增 `window.licenseApi`（getState/activate/testConnection/refresh/getStatus/logout/onStateChanged） |
| `resources/license-public.pem` | 🆕 | 验签公钥（export_public_key.py 导出；当前为 DEV 密钥） |
| `resources/license-public.dev.json` | 🆕 | DEV 密钥标注（生产构建前必须重新导出正式公钥） |

## 3. 渲染层 `app/web/`（阶段 5）

| 路径 | 状态 | 内容 / 原因 |
|---|---|---|
| `src/license/types.ts` | 🆕 | 渲染层镜像类型 + 错误文案兜底 + `getLicenseApi()`（globalThis 结构类型） |
| `src/license/format.ts` | 🆕 | 本地时区完整时间/剩余时间/提醒档位文案 |
| `src/license/LicenseGate.tsx` | 🆕 | 状态→界面路由（激活页/锁定页/加载页/放行）；浏览器预览模式直通 |
| `src/license/LicenseActivatePage.tsx` | 🆕 | 服务器地址（记忆）+ 密钥 + 设备名 + 连接测试（绿/红）+ 激活 + reason_code 中文错误 |
| `src/license/LicenseLockedPage.tsx` | 🆕 | 撤销/暂停/时间异常文案；重新验证/返回激活页/安全退出（无绕回主界面按钮） |
| `src/license/LicenseBanner.tsx` | 🆕 | 非阻断横幅：SERVER_UNREACHABLE（可用至何时）+ 到期提醒（3天/1天/1小时） |
| `src/license/LicenseStatusSection.tsx` | 🆕 | 设置页许可证状态卡（编号/设备/激活与截止时刻+时区/剩余/心跳/服务器状态；立即验证/退出许可证） |
| `src/App.tsx` | ✏️ | 最外层包 `LicenseGate`，主界面顶部挂 `LicenseBanner` |
| `src/api/client.ts` | ✏️ | 新增 `requireActiveLicense()` 前置检查，拦在 upload/run/retrieve/review/decide/batchDecide/export 7 个核心请求前 |
| `src/api/electron.d.ts` | ✏️ | `window.licenseApi` 类型声明 |
| `src/pages/SettingsPage.tsx` | ✏️ | 嵌入 `LicenseStatusSection` |

## 4. 根目录与其它（阶段 5–6）

| 路径 | 状态 | 内容 / 原因 |
|---|---|---|
| `electron-builder.yml` | ✏️ | extraResources 增加 `app/desktop/resources/license-public.pem → license-public.pem`（打包后公钥随资源分发） |
| `package.json` | ✏️ | 新增 `"typecheck"` script（阶段 5）；新增 vitest devDependency + `"test:license": "vitest run"`（阶段 6） |
| `package-lock.json` | ✏️ | vitest 安装连带更新 |
| `vitest.config.ts` | 🆕 | vitest 配置（node 环境，include 限定 license __tests__） |
| `.gitignore` | ✏️ | `app/license-server/.data/`（SQLite+私钥不入库）、`scripts/.license-smoke.bundle.mjs` |
| `scripts/license-smoke.ts` | 🆕 | 端到端集成冒烟（41 项检查；依赖真实 license-server，不进 vitest；头部注释含运行手册） |
| `docs/license/*.md` | 🆕 | 本文档六件套（阶段 7） |

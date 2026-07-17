# 许可证系统架构说明

> 适用范围：AI 审校助手「老板端许可证服务器 + 员工端许可证接入」（阶段 2–6 实现）。
> 本文所有路径、端口、字段名均以仓库当前代码为准。

## 1. 系统总览

```
┌────────────────────────────────────────────────────────────────────┐
│ 老板端（局域网内一台机器）                                            │
│  app/license-server（FastAPI + SQLModel/SQLite，单进程双监听）        │
│  ├─ 管理 API + 管理 UI   http://127.0.0.1:8767/   （仅本机）          │
│  └─ 员工 API             http://0.0.0.0:8768/api/v1（对局域网开放）    │
│  数据目录 app/license-server/.data/（SQLite + 密钥，已 gitignore）    │
└──────────────▲─────────────────────────────────────────────────────┘
               │ HTTP/JSON + Ed25519 签名
┌──────────────┴─────────────────────────────────────────────────────┐
│ 员工端（每位员工一台机器，Electron 桌面应用）                          │
│  app/desktop/main/license/   许可证状态机（主进程，验签/心跳/存储）    │
│  app/desktop/preload/        window.licenseApi（contextBridge）      │
│  app/web/src/license/        LicenseGate/激活页/锁定页/横幅/状态卡    │
│  app/server（FastAPI 员工后端，不感知许可证）                         │
└────────────────────────────────────────────────────────────────────┘
```

关键边界：

- **许可证门在 desktop/renderer 层**。`app/server`（审校业务后端）完全不感知许可证；
  渲染层在发审校等核心请求前调用 `requireActiveLicense()` 实时查询主进程状态机
  （`app/web/src/api/client.ts`）。
- **客户端只含公钥**（`app/desktop/resources/license-public.pem`），私钥只在老板端数据目录。
- 管理 API 只监听 `127.0.0.1`，员工无法访问管理功能。

## 2. 数据库存储（老板端）

- SQLite，文件：`app/license-server/.data/license.db`（`.data/` 已加入 `.gitignore`）。
- 首次启动时由 FastAPI lifespan 调用 `init_db()` 自动建表
  （`license_server/main.py` → `license_server/core/db.py`，`SQLModel.metadata.create_all`），
  无独立迁移脚本（详见 [database.md](database.md)）。
- 三张表（`license_server/models/tables.py`）：

| 表 | 关键字段 | 说明 |
|---|---|---|
| `licenses` | `id`（`lic_<hex>`）、`license_key_hash`（**SHA256(key) hex，唯一索引**）、`license_key_prefix`（第一组 4 字符，脱敏展示）、`status`（pending/active/suspended/revoked/expired）、`validity_mode`（duration 模式 A / fixed 模式 B）、`duration_seconds`、`activated_at`、`expires_at`、`max_devices`、`features`（JSON）、`minimum_client_version`、`license_version`（影响凭证内容的变更 +1）、`suspended_at`/`revoked_at`/`revoked_reason` | **明文 License Key 不落库**，只在创建时经 API 返回一次 |
| `devices` | `id`（`dev_<uuid>`）、`license_id`（外键）、`device_id`（客户端算好的 SHA256 hex）、`device_name`、`platform`、`os_version`、`first_activated_at`、`last_seen_at`、`last_ip`、`last_client_version`、`last_nonce`（心跳防重放）、`revoked` | 激活时绑定；心跳按 `device_id` **全局**校验归属 |
| `license_events` | `id`（`evt_<uuid>`）、`license_id`、`device_id`、`event_type`（见 `schemas.EventType`）、`event_time`、`ip_address`、`client_version`、`result`（success/failure）、`reason_code`、`event_metadata`（JSON 列，物理列名 `metadata`） | 审计流水；**metadata 严禁包含完整 key、私钥、完整签名**（代码注释约束） |

## 3. 数字签名流程

算法：**Ed25519**（服务端 `cryptography` 库；客户端 Node `node:crypto`，不手写密码学）。

**canonical JSON（签名对象序列化，两端必须逐字节一致）**：

```
Python: json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
TS 等价: app/desktop/main/license/canonical.ts 的 canonicalize()
        —— 键递归按 Unicode 码位排序、无空白、非 ASCII 原样 UTF-8、不转义 "/"
```

一致性由对拍向量保证：`app/license-server/tests/vectors/license_vectors.json`（4 组，含篡改用例），
客户端 vitest 逐字节对拍（`app/desktop/main/license/__tests__/canonical.test.ts`）。

**两种签名对象（以服务端代码为准，已在阶段 5 核对）**：

| 场景 | 响应结构 | 签名对象 |
|---|---|---|
| 激活 `/licenses/activate`、刷新 `/licenses/refresh` | `{"success": true, "license": {token}, "signature": base64}` | **只签 token 对象本身**（`services/token.py: sign_token`） |
| 心跳 `/licenses/heartbeat`（active/revoked/suspended/expired 业务状态） | `{status, ..., "signature": base64}`（HTTP 200） | **签去掉 signature 字段后的整个响应体**（`services/token.py: sign_response`） |
| 请求级失败（key 错、设备未注册、限流等） | HTTP 4xx + `{"success": false, "reason_code": ..., "message": ...}` | **不签名** |

签名策略推论（客户端实现于 `licenseService.ts`）：

- **只有验签通过的响应才会驱动状态迁移**（revoked/suspended/expired/active）。
- 未签名的错误体只用于展示（reasonCode/message），**绝不据此删除或隔离本地凭证**，
  防止伪造服务器响应误锁。
- 心跳响应验签失败 → 忽略该响应并记日志，不改变当前状态。

凭证 token 结构（`LicenseToken`，schema_version=1）：

```json
{"schema_version":1,"license_id":"lic_<hex>","device_id":"<sha256 hex>",
 "issued_at":"<ISO Z>","expires_at":"<ISO Z 或 null>","features":["main"],"license_version":1}
```

`expires_at` 为 `null` 表示永久授权（客户端按"永不过期"处理）。

## 4. 核心流程

### 4.1 激活流程

1. 员工在激活页输入服务器地址、许可证密钥、设备名（默认本机名，主进程 `os.hostname()` 兜底）。
2. 主进程 `LicenseService.activate()`（**幂等**：并发重复调用复用同一 Promise，只发一次请求）：
   - 计算 `device_id = SHA256("ai-review:<MachineGuid>:<installation-secret>")`（64 hex 字符）；
   - `POST /api/v1/licenses/activate`（带 device_id、client_version、随机 nonce）。
3. 服务端校验链（`services/activation.py`）：key 哈希存在 → 状态（挂起/撤销/过期拒绝）→
   最低客户端版本 → 设备：同 device_id 已绑定且未解绑 → **幂等成功**（不占新额度）；
   新设备且绑定数 ≥ max_devices → `LICENSE_DEVICE_LIMIT_REACHED`。
   模式 A（duration）在**首次激活时刻**起算有效期并置 active。
4. 客户端收到凭证后：**先验签**（失败→INVALID_SIGNATURE）、**比对 device_id**（不符→DEVICE_MISMATCH），
   然后用 safeStorage（Windows DPAPI）加密落盘 `userData/license.dat`，进入 SERVER_ACTIVE 并启动心跳。

### 4.2 心跳流程

- 周期默认 **300 秒**（`config.ts`，服务器可在 active 响应中用 `next_heartbeat_seconds` 调整）；
  **应用启动后立即先做一次服务器检查**，再进入周期。
- 请求体：`{license_id, device_id, session_id, client_version, license_version, timestamp, nonce}`。
  - `timestamp` 与服务器时间偏差 > 300s → `SERVER_TIME_INVALID`；
  - `nonce` 与该 (license, device) 上次相同 → `REPLAY_DETECTED`（防重放）。
- **并发去重**：上一次心跳未结束不叠加（`heartbeatInFlight`）。
- **网络失败（超时 10s / 不可达）**：不锁定；按 **[5s, 15s] 快速重试 2 次**后等下个周期，
  状态置 SERVER_UNREACHABLE，界面仅非阻断横幅提示（`LicenseBanner`）。
- 响应处理（先验签）：active → 更新可信服务器时间；revoked → 立即锁定（见 4.4）；
  suspended → 锁定但保留凭证；expired → 尝试 refresh，失败停留许可证页。

### 4.3 离线规则表（任务书 §五，照录并标注实现位置）

| 本地凭证 | 服务器状态 | 客户端行为 | 实现位置 |
|---|---|---|---|
| 未过期 + 签名有效 | active | 正常使用，更新本地状态 | `licenseService.ts: handleHeartbeatPayload case 'active'` |
| 未过期 + 签名有效 | revoked（验签通过） | **立即锁定**，凭证标记 `revoked=true` 持久化 | 同上 `case 'revoked'` |
| 未过期 + 签名有效 | suspended（验签通过） | 锁定，**保留凭证**（恢复后 refresh 即可用） | 同上 `case 'suspended'` |
| 未过期 + 签名有效 | 不可达 | **继续使用**（SERVER_UNREACHABLE 不锁定） | `heartbeatWithRetry` + `computeUsable()` |
| 已过期 | 续期成功 | 保存新凭证继续使用 | `refresh()` |
| 已过期 | 不可达 | **禁止使用**（LOCAL_EXPIRED，停留许可证页） | `init()` 过期分支 |
| 签名无效 | — | **禁止使用**（INVALID_SIGNATURE，隔离凭证文件） | `init()` 验签分支 |
| 设备不匹配 | — | **禁止使用**（DEVICE_MISMATCH） | `init()` 设备比对分支 |

以上每行均有对应 vitest 用例（`__tests__/licenseService.test.ts`「离线规则表」分组）。

### 4.4 撤销流程

1. 管理员在管理 UI（或 `POST /api/v1/admin/licenses/{id}/revoke`）撤销。
2. **下一次心跳生效**：服务端返回验签通过的 `{status:"revoked", ...}`，客户端立即锁定、
   持久化撤销标记、通知渲染层显示锁定页（不可绕过，无跳回主界面按钮）。
3. **最大延迟约一个心跳周期（默认 ≈5 分钟）**；撤销期间本地凭证仍在有效期内时可离线使用，
   这是离线放行设计的固有窗口。
4. 已标记撤销的凭证在**冷启动时直接进入 REVOKED**，不再联网验证。

### 4.5 续期 / 变更流程

- 管理员续期（renew）或任何影响凭证内容的变更 → 服务端 `license_version + 1`。
- 心跳 active 响应携带最新 `license_version`；当大于客户端上报值时附带 `refresh_required: true`。
- 客户端自动调 `/licenses/refresh` 取新凭证，**验签通过后覆盖旧凭证**；
  `license_version` **单调递增**：心跳/refresh 响应版本回退直接忽略，防止旧响应覆盖新状态。
- 客户端发送的 `license_version` 追平后，服务端不再置 `refresh_required`（无循环）。

## 5. 员工端状态机（13 状态）

```
UNINITIALIZED ──init()──▶ VALIDATING_LOCAL ──┬─ 无凭证 ──────────────▶ NO_LICENSE
                                             ├─ 验签失败 ────────────▶ INVALID_SIGNATURE
                                             ├─ device_id 不符 ──────▶ DEVICE_MISMATCH
                                             ├─ 本地撤销标记 ────────▶ REVOKED（锁定）
                                             ├─ 时间回拨超容差 ──────▶ TIME_TAMPER_DETECTED（锁定）
                                             ├─ 已过期 ──────────────▶ LOCAL_EXPIRED ──refresh 成功─▶ SERVER_ACTIVE
                                             │                          （refresh 失败停留，许可证页）
                                             └─ 未过期 ──────────────▶ LOCAL_VALID（放行）
                                                                        │ 启动后立即一次服务器检查
                                                                        ▼
                                                ┌── active（验签通过）── SERVER_ACTIVE ◀──┐
                                                ├── 不可达 ──────────▶ SERVER_UNREACHABLE │
                                                │     （不锁定，本地凭证有效即可用）        │ 周期心跳 300s
                                                ├── suspended ───────▶ SUSPENDED（锁定，  │
                                                │                       保留凭证）         │
                                                ├── revoked ─────────▶ REVOKED（锁定，     │
                                                │                       标记撤销）         │
                                                └── refresh_required ─▶ refresh ─────────┘
CONNECTING_SERVER：无本地凭证时 activate/refresh 进行中（加载页）
```

渲染层映射（`app/web/src/license/LicenseGate.tsx`）：

| 状态 | 界面 |
|---|---|
| UNINITIALIZED / VALIDATING_LOCAL / CONNECTING_SERVER | 全屏加载页 |
| NO_LICENSE / INVALID_SIGNATURE / DEVICE_MISMATCH / LOCAL_EXPIRED | 许可证激活页 |
| SUSPENDED / REVOKED / TIME_TAMPER_DETECTED | 锁定页（不可绕过） |
| LOCAL_VALID / SERVER_ACTIVE / SERVER_UNREACHABLE | 主界面（+ 非阻断横幅） |

### 启动决策树

```
读取 userData/license.dat
  ├─ 不存在/损坏/解密失败 → NO_LICENSE（激活页）
  ├─ 验签失败            → INVALID_SIGNATURE（隔离凭证 → 激活页）
  ├─ device_id 不匹配    → DEVICE_MISMATCH（激活页）
  ├─ revoked 标记        → REVOKED（锁定页）
  ├─ 时间回拨 > 300s     → TIME_TAMPER_DETECTED（锁定页）
  ├─ 已过期              → 尝试 refresh：成功→SERVER_ACTIVE；失败→LOCAL_EXPIRED（激活页）
  └─ 未过期              → LOCAL_VALID 放行 + 立即一次服务器检查 + 进入 300s 心跳周期
```

## 6. 时间安全

- 每条**验签通过**的心跳/激活/刷新响应都会推进 `last_trusted_server_time`（只增不减）。
- 本机观测到的最大时间记入 `max_observed_time`（先检测、后推进）。
- 参考时间 = max(last_trusted_server_time, max_observed_time)；当前系统时间早于参考时间
  超过 **300 秒容差**（与服务端 `timestamp_tolerance_seconds` 对齐）→ `TIME_TAMPER_DETECTED` 锁定。
- 检测时机：每次启动（init）+ 每次心跳响应处理中。
- 实现：`app/desktop/main/license/timeGuard.ts`（纯函数），持久化在 `license.dat` 内。

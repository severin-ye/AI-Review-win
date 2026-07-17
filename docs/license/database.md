# 数据库迁移说明（老板端 license-server）

## 1. 初始化方式（以代码实际为准）

- **无独立迁移脚本、无 alembic**。首次启动时由 FastAPI lifespan 自动建表：
  - 调用链：`license_server/run.py` / `license_server/main.py` 的 `_lifespan()` →
    `license_server/core/db.py: init_db()` → `SQLModel.metadata.create_all(engine)`。
  - `create_all` 是幂等的（`CREATE TABLE IF NOT EXISTS` 语义）：已存在的表不会重建，**也不会修改已有表结构**。
- 数据库文件：`app/license-server/.data/license.db`（数据目录可用环境变量
  `AI_REVIEW_LICENSE_DATA_DIR` 覆盖）。
- engine 按数据目录惰性创建并缓存（`get_engine()`）；测试通过切换
  `AI_REVIEW_LICENSE_DATA_DIR` + `reset_engine()` 实现隔离。

## 2. 三表 DDL 要点

由 SQLModel 表模型生成（`license_server/models/tables.py`），要点如下：

### licenses

| 列 | 类型/约束 | 备注 |
|---|---|---|
| `id` | TEXT PRIMARY KEY | `lic_<32hex>` |
| `license_key_hash` | TEXT UNIQUE, INDEX | **SHA256(明文 key) hex**；明文不落库 |
| `license_key_prefix` | TEXT, INDEX | 第一组 4 字符，用于脱敏展示 `AIREV-XXXX-****-****` |
| `status` | TEXT, INDEX, 默认 `pending` | pending/active/suspended/revoked/expired |
| `validity_mode` | TEXT，默认 `duration` | duration=模式 A（首激活起算）/ fixed=模式 B（固定截止） |
| `duration_seconds` | INTEGER NULL | 模式 A 有效秒数 |
| `activated_at` / `expires_at` | DATETIME NULL（UTC） | 首次激活时刻 / 到期时刻 |
| `max_devices` | INTEGER，默认 1 | 设备上限 |
| `features` | JSON 列 | 默认 `["main"]` |
| `minimum_client_version` | TEXT，默认 `0.0.0` | 激活时校验 |
| `license_version` | INTEGER，默认 1 | 影响凭证内容的变更 +1（驱动 refresh_required） |
| `suspended_at` / `revoked_at` / `revoked_reason` | DATETIME/TEXT NULL | 状态时间戳 |
| `created_at` / `updated_at` | DATETIME（UTC） | |

### devices

| 列 | 类型/约束 | 备注 |
|---|---|---|
| `id` | TEXT PRIMARY KEY | `dev_<uuid hex>` |
| `license_id` | TEXT FK → licenses.id, INDEX | |
| `device_id` | TEXT, INDEX | 客户端计算的 SHA256 hex；**心跳按此全局校验归属** |
| `device_name` / `platform` / `os_version` | TEXT | 设备展示信息 |
| `first_activated_at` / `last_seen_at` | DATETIME（UTC） | |
| `last_ip` / `last_client_version` | TEXT | 最近一次心跳 |
| `last_nonce` | TEXT NULL | 心跳防重放（同 nonce 直接拒） |
| `revoked` / `revoked_at` | BOOLEAN / DATETIME | 设备解绑标记 |
| `created_at` / `updated_at` | DATETIME（UTC） | |

### license_events

| 列 | 类型/约束 | 备注 |
|---|---|---|
| `id` | TEXT PRIMARY KEY | `evt_<uuid hex>` |
| `license_id` | TEXT NULL, INDEX | 失败事件可能无归属 |
| `device_id` | TEXT NULL | |
| `event_type` | TEXT, INDEX | 见 `schemas.EventType`（LICENSE_CREATED / ACTIVATION_SUCCEEDED / HEARTBEAT_SUCCEEDED / LICENSE_RENEWED / LICENSE_SUSPENDED / LICENSE_REVOKED / DEVICE_UNBOUND / LICENSE_EXPIRED 等） |
| `event_time` | DATETIME, INDEX（UTC） | |
| `ip_address` / `client_version` | TEXT | |
| `result` / `reason_code` | TEXT | success / failure + 错误码 |
| `metadata` | JSON 列（Python 属性名 `event_metadata`） | **严禁包含完整 license key、私钥、完整签名**（表模型注释约束） |

## 3. 后续升级注意事项

**当前无版本化迁移机制（无 alembic / 无 schema 版本号）。** `create_all` 只能新增表，
不能给已有表加列或改列。升级建议：

1. **加列/改列前**，先备份整个 `.data/` 目录（`license.db` + `keys/`）：

   ```powershell
   Copy-Item -Recurse app\license-server\.data app\license-server\.data.bak-$(Get-Date -Format yyyyMMdd-HHmmss)
   ```

2. 变更表模型后，二选一：
   - **数据可重建**（开发期）：停服 → 删除 `.data/license.db` → 重启自动建新表
     （注意：所有许可证与设备绑定丢失，需重新创建并全员重新激活；密钥在 `keys/` 不受影响）。
   - **数据需保留**（生产）：停服 → 备份 → 用 SQLite 客户端手动 `ALTER TABLE`
     （SQLite 支持 `ADD COLUMN`，不支持直接改列类型/删列，复杂变更需要
     "建新表 → 拷数据 → 改名" 流程）→ 重启验证。
3. 若未来变更频繁，建议引入 alembic 并以 `SQLModel.metadata` 为目标生成迁移脚本；
   届时需要为现有库补一个初始基线（`alembic stamp`）。
4. **密钥与库分离**：重建 `license.db` 不影响 `keys/` 下的密钥对，已删除数据后新签发的
   凭证仍用原密钥，员工端公钥无需替换；反之**重新生成密钥对（regenerate）会使所有已签发
   凭证立即失效**，且需要重新导出公钥到员工端（见 [runbook.md](runbook.md)）。

# 许可证系统安全说明

> 本文描述安全机制的实际实现（以代码为准）与其边界。不夸大防护能力。

## 1. 私钥保存（老板端）

- 位置：`app/license-server/.data/keys/`（整个 `.data/` 已 gitignore，私钥不会入库）。
- 保护机制（`license_server/core/keys.py`）：
  - **Windows 且有 win32crypt** → 私钥（PKCS8 PEM 字节）经 **DPAPI `CryptProtectData`**
    加密存 `private.key.bin`；读取时 `CryptUnprotectData` 解密。DPAPI 绑定当前机器/用户，
    拷贝到其它机器无法解密。
  - **无 win32crypt**（非 Windows 开发环境）→ 明文 `private_key.pem` + 醒目警告日志
    （代码注释与日志均标注"仅开发用"）。
  - 公钥始终明文存 `public_key.pem`（公钥无需保密）。
- **备份要求**：备份整个 `.data/`（`license.db` + `keys/`）。私钥丢失 = 所有已签发凭证
  无法验签，只能重新生成密钥对并全员重新激活。
- 「重新生成密钥对」（管理页危险操作）会删除旧密钥文件并新建——**所有已签发凭证立即
  验签失败**，且员工端需重新导出公钥、重新打包或替换资源。

## 2. 公钥分发

- 流程：老板端 `scripts/export_public_key.py` →
  `app/desktop/resources/license-public.pem` → electron-builder `extraResources`
  复制到安装包 `resources/license-public.pem` → 主进程多候选路径加载
  （`app/desktop/main/license/publicKey.ts`）。
- **客户端只含公钥**，验签使用 Node `node:crypto`（不手写密码学）。
- **当前仓库内的公钥是 DEV 密钥**：DEV 模式导出时额外写
  `app/desktop/resources/license-public.dev.json` 标注文件（含指纹与醒目警告）。
  含义：该密钥对仅用于开发联调。**生产构建前必须**：生产密钥对（`AI_REVIEW_LICENSE_DEV_KEYS=0`）
  → 重新导出公钥 → 确认 dev 标注不再生成 → 再打包。
- 公钥指纹（`SHA256:<sha256(DER)>`）在管理页与 `/api/v1/ping` 可见，可用于核对
  员工连接的是不是目标服务器。

## 3. License Key 保存

- 明文 License Key（`AIREV-XXXX-XXXX-XXXX`，32 字符集排除 0/O/1/I/L）**只存在创建瞬间**：
  管理 API 仅在 `POST /admin/licenses` 响应中返回一次明文。
- 数据库只存：`license_key_hash = SHA256(key) hex`（唯一索引）+
  `license_key_prefix`（第一组 4 字符，用于脱敏展示 `AIREV-XXXX-****-****`）。
- 激活查询按哈希匹配，比对用 `hmac.compare_digest`（防时序侧信道）。
- 用户输入经规整（去空白、转大写），不改变哈希语义。

## 4. 本地许可证保护（员工端）

- 存储：`userData/license.dat`，经 Electron **safeStorage（Windows 即 DPAPI）加密**后落盘
  （`app/desktop/main/license/storage.ts`）。
- **降级策略（写明）**：safeStorage 不可用（如 Linux 无桌面密钥环的开发环境）→
  `PLAIN:` 前缀明文存储 + 醒目警告日志；仅开发环境可接受，Windows 生产环境命中该降级
  应视为部署异常。
- **防止修改截止时间**：截止时间 `expires_at` 在签名 token 内。任何本地篡改
  （改截止时间、改 device_id、改 features）都会导致**启动时验签失败** →
  INVALID_SIGNATURE → 凭证文件被隔离（重命名 quarantine）→ 停留激活页。
  验签对拍向量含 tampered_expires_at / tampered_device_id 两个篡改用例，客户端 vitest 全过。
- **防止替换凭证**：token 内 `device_id` 与本机设备指纹（见下）不符 → DEVICE_MISMATCH → 禁止。
- **防止时钟回拨续命**：可信服务器时间 + max_observed_time 回拨检测（300s 容差）→
  TIME_TAMPER_DETECTED 锁定（详见 [architecture.md](architecture.md) 第 6 节）。

## 5. 设备 ID 隐私设计

- `device_id = SHA256("ai-review" + ":" + MachineGuid + ":" + installation_secret)`（64 hex）。
  - MachineGuid 读自注册表 `HKLM\SOFTWARE\Microsoft\Cryptography`，**原始值不出本机**，
    只参与本地哈希；
  - installation_secret 为首次运行生成的 32 字节随机数，safeStorage 加密存 userData。
- 服务器与日志中出现的只有哈希值；重装系统/换机后 device_id 变化，需重新激活
  （占用新设备额度或管理员先解绑）。

## 6. 服务端防护

- **速率限制**：activate 固定窗口限流，每 IP 10 次/分钟（`api/ratelimit.py`，内存实现；
  阈值可用 `AI_REVIEW_LICENSE_RATE_LIMIT_PER_MINUTE` 调整），超限返回 429 `RATE_LIMITED`。
  防 License Key 在线爆破（key 空间 32^12 ≈ 2^60，配合限流实际不可行）。
- **nonce 防重放**：心跳 nonce 与该 (license, device) 上次相同 → 400 `REPLAY_DETECTED`。
- **时间戳窗口**：心跳 `timestamp` 与服务器时间偏差 > 300s → `SERVER_TIME_INVALID`，
  防止旧请求重放与严重走时的客户端。
- **管理接口隔离**：管理 API/UI 只监听 `127.0.0.1:8767`，局域网内员工无法访问管理功能；
  员工 API 与管理 API 是两个独立 FastAPI app。
- **日志脱敏**：事件 metadata 严禁包含完整 license key、私钥、完整签名（表模型注释约束；
  激活事件只记 `key_prefix`）；员工端 IPC 注释与实现同样不打印完整 key/signature；
  内部异常不回堆栈，统一 500。
- **签名保证响应可信**：revoked/suspended/expired/active 业务状态响应均为 Ed25519 签名，
  中间人无法伪造"已撤销"或"仍有效"；伪造的未签名错误体不会被客户端用于删除凭证。

## 7. 员工端校验位置

- 启动决策树（验签 → 设备 → 撤销标记 → 时间 → 到期）+ 周期心跳（`licenseService.ts`）。
- `canUseFeature()` 每次**实时查询状态机**（不是启动时检查一次）；渲染层核心请求前
  `requireActiveLicense()` 前置拦截；锁定页无绕回主界面按钮；不留绕过开关。

## 8. 诚实声明：防不住什么

本系统是**防君子不防职业破解者**的商用授权方案。明确防不住的：

1. **本地调试/补丁绕过客户端校验**：员工对本机 Electron 主进程 JS（asar 内）、
   渲染层代码有完全控制权，可通过调试器、改包、hook `licenseApi` 等方式绕过
   `canUseFeature` / `LicenseGate`。Ed25519 只能保证"凭证与服务器响应不可伪造"，
   不能保证"客户端一定执行校验"。
2. **专业逆向**：反编译、内存补丁、协议重放中间人等，成本只是时间问题。
3. **整包克隆到无网环境**：若攻击者同时补丁掉激活页与状态机，离线规则无法发现。

**缓解思路（按性价比排序）**：

- **核心能力服务端化**：把审校的关键计算（如 LLM 调用编排、知识库检索）放到需要
  许可证令牌才能访问的服务端，而非纯客户端判定——这是唯一本质有效的加固方向；
- 保持心跳审计（`license_events`），异常使用模式（多 IP、版本异常）事后追责；
- 提高逆向成本：asar 完整性校验、主进程代码混淆（增加工作量但非根本解决）；
- 法律与合同约束（商用授权的真正兜底）。

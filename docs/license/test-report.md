# 许可证系统测试报告

> 报告时点：阶段 6 结束。所有命令均为实际执行并记录真实输出。
> （防火墙模块增补后，命令 1 与服务端 pytest 分布已按最新重跑结果更新为 66 passed。）

## 1. 已执行命令与结果

| # | 命令 | 结果 |
|---|---|---|
| 1 | `cd app\license-server; ..\server\.venv\Scripts\python.exe -m pytest tests/ -q` | **66 passed**, 1 warning, 9.74s（防火墙模块新增后重跑实测） |
| 2 | `cd app\server; .\.venv\Scripts\python.exe -m pytest tests/ -q` | **30 passed**, 240 warnings（存量 `datetime.utcnow` 弃用告警）, 17.81s |
| 3 | `npm.cmd run test:license`（vitest run） | **5 files / 60 tests 全 passed**, ≈0.8s |
| 4 | `npm.cmd run typecheck`（两套 tsconfig） | 通过，0 错误 |
| 5 | `npm.cmd run build`（electron-vite build） | 通过（main 41.01 kB / preload 1.17 kB / renderer ≈951 kB） |
| 6 | `node scripts\.license-smoke.bundle.mjs`（对真实 license-server） | **40 项断言全通过 ✅**（37 项打印检查 + 3 项异步等待门） |

服务端 pytest 分布（`--collect-only` 实测）：

| 文件 | 用例数 | 内容 |
|---|---|---|
| `tests/test_api.py` | 28 | 员工 API + 管理 API 端点行为 |
| `tests/test_crypto.py` | 11 | canonical JSON、Ed25519、License Key 哈希 |
| `tests/test_core.py` | 9 | 时间工具、密钥管理、配置 |
| `tests/test_scenarios.py` | 6 | 端到端业务场景（激活→心跳→撤销等） |
| `tests/test_firewall.py` | 12 | 防火墙自动放行：启用条件（win32+frozen+SKIP 开关）、netsh 输出解析与端口判定、UAC 提权添加/取消/复查/异常兜底 |
| 合计 | **66** | |

客户端 vitest 分布（`app/desktop/main/license/__tests__/`）：

| 文件 | 用例数 | 内容 |
|---|---|---|
| `canonical.test.ts` | 17 | vectors 4 组逐字节对拍 + canonical 规则专项 |
| `timeGuard.test.ts` | 18 | 回拨/可信时间/到期/剩余/提醒档位 |
| `licenseService.test.ts` | 18 | 状态机 + 离线规则表 + 单调性 + 并发控制 + 登出 |
| `serverClient.test.ts` | 4 | URL 规整 + 错误分类 |
| `errorMessages.test.ts` | 3 | 中文文案与 schemas.py 逐项一致 |
| 合计 | **60** | |

端到端冒烟断言分布：对拍向量 8、ping 1、建证 1、错误 key 2、激活链路 7、冷启动 2（+1 等待门）、
心跳验签+篡改负例 4、协议负例 2、撤销链路 6（+1 等待门）、断连行为 4（+1 等待门），
合计 37 项打印检查 + 3 项异步等待门 = 40 项断言（明细见 `scripts/license-smoke.ts` 输出）。

## 2. 覆盖矩阵（任务书 §十九 单元测试 → 测试文件）

| §十九 条目 | 覆盖位置 | 状态 |
|---|---|---|
| canonical/验签：vectors 4 组对拍（valid 通过、tampered_expires_at / tampered_device_id / bad_signature 失败）；JS canonical 与 Python 字节一致 | `__tests__/canonical.test.ts` | ✅ 17 用例 |
| timeGuard：回拨（超容差异常/容差内放行）、可信时间更新、到期判定、剩余时间、提醒档位（3天/1天/1小时各一次） | `__tests__/timeGuard.test.ts` | ✅ 18 用例 |
| 状态机 + 离线规则表（§五 表格逐行）：未过期+active 正常；revoked(签名通过) 立即锁定+凭证标记；suspended 锁定保留凭证；不可达继续使用；已过期+续期成功继续；已过期+不可达禁止；签名无效禁止；设备不匹配禁止 | `__tests__/licenseService.test.ts`「离线规则表」分组 | ✅ 逐行对应用例 |
| license_version 单调性：旧版本响应不覆盖新状态 | 同上「license_version 单调性」分组（心跳忽略 / refresh 回退拒绝 / refresh_required 自动换新） | ✅ |
| 激活幂等：并发两次 activate 只发一次请求 | 同上「并发控制」分组（同一 Promise 复用，activateCalls===1） | ✅ |
| 心跳并发去重：上一次未结束不叠加 | 同上（gate 挂起验证 heartbeatCalls 不增加） | ✅ |
| 错误码映射：renderer reason_code → 中文文案与 schemas.py 一致（正则提取对比，来源已注明） | `__tests__/errorMessages.test.ts`（主进程 + 渲染层两份映射都与 schemas.py `toEqual`） | ✅ |
| 假 fetch / 假 storage / 假时钟注入，不依赖 electron 与真实服务器 | `__tests__/fakeServer.ts`（真实 Ed25519 密钥对按协议签名响应） | ✅ |

服务端 §十九 条目由 66 个 pytest 覆盖（test_crypto / test_core / test_api / test_scenarios / test_firewall）。

## 3. 验收标准（任务书 §二十）逐项核对

| 验收项 | 状态 | 验证方式 |
|---|---|---|
| 员工端未激活不可进入主界面 | ✅ | vitest（NO_LICENSE → 激活页路由逻辑）+ 冒烟（错误 key 激活被拒） |
| 激活需服务器在线，凭证验签通过才落盘 | ✅ | 冒烟第 4 组（激活成功、落盘凭证验签通过、幂等重复激活） |
| 心跳周期 300s + 启动立即一次 + [5,15] 重试 | ✅ | config.ts 默认值 + vitest 状态机用例 |
| 连接失败 ≠ 撤销（不可达不锁定，本地凭证有效即可用） | ✅ | vitest（SERVER_UNREACHABLE usable=true）+ 冒烟第 9 组（断连后仍可用、canUseFeature=true） |
| 撤销下一次心跳生效（最大延迟约 5 分钟），锁定页不可绕过 | ✅ | 冒烟第 8 组（撤销→心跳 REVOKED→冷启动直接 REVOKED 且不可用）+ vitest 对应用例 |
| suspended 锁定但保留凭证 | ✅ | vitest（SUSPENDED 且 storage 未清除未隔离） |
| 已过期不可达禁止；已过期续期成功继续 | ✅ | vitest 两条对应用例 |
| 签名无效/设备不匹配禁止 | ✅ | vitest + vectors 篡改用例 |
| license_version 单调递增、refresh_required 自动刷新 | ✅ | vitest 三条对应用例 |
| 时间回拨检测（300s 容差） | ✅ | vitest timeGuard 全套 + 状态机 TIME_TAMPER_DETECTED 用例 |
| 客户端只含公钥、不手写密码学、日志不打印完整 key/签名 | ✅ | 代码审查（node:crypto 验签；ipc 注释与实现） |
| 员工后端（app/server）不感知许可证 | ✅ | 未改 app/server；30 个 pytest 回归通过 |
| typecheck / build 通过 | ✅ | 命令 4、5 |

## 4. 未覆盖项与风险（如实）

1. **渲染层无 UI 单测**：LicenseGate / 激活页 / 锁定页 / 横幅仅经 typecheck + build 验证，
   未在有显示环境做 Electron GUI 走查。建议后续安排一次 `npm run dev` 人工验收
   （激活 → 心跳 → 撤销锁定全链路截图检查点）。
2. **safeStorage（DPAPI）真机路径未测**：单测与冒烟均走明文降级路径（`PLAIN:` 前缀）。
   Windows 上 DPAPI 加解密需在真机验证。
3. **注册表 MachineGuid 读取未单测**（平台依赖）；`computeDeviceId` 纯函数已间接验证。
4. **TIME_TAMPER 心跳运行期分支、到期提醒主进程 emit 分支**：timeGuard 纯函数层全测，
   服务层这两条分支仅有逻辑实现与部分间接覆盖。
5. **到期提醒横幅 UI 未实测**（档位判定纯函数已测，横幅渲染未测）。
6. **专业逆向无法完全防御**：客户端校验可被本地调试/补丁绕过（详见
   [security.md](security.md) 第 8 节的诚实声明与缓解思路）。
7. vitest 未纳入根目录统一 `npm test`（当前脚本为 `test:license`，避免与未来其它套件冲突）。
8. **防火墙 UAC 提权真机路径未实测**：`test_firewall.py` 全部 mock subprocess/ctypes/sys；
   exe 冒烟走 `AI_REVIEW_LICENSE_SKIP_FIREWALL=1` 跳过路径验证。真实 UAC 弹窗点「是」后的
   规则添加链路未在真机走查，首次在老板机器上运行时需人工确认（失败也只记警告、不阻断启动，
   兜底为手动 netsh 命令，见 [runbook.md](runbook.md) §一.6）。

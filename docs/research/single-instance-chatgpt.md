# 单实例方案调研（ChatGPT 对话导出，2026-07-18）

> 来源：https://chatgpt.com/c/6a5ae04d-d6d8-83ee-abf4-48529115ea43
> 背景：2026-07-18 曾发生两个 license-server exe 并发启动互相覆盖密钥的事故。
> 本文是业主调研的原始存档，实现时以此为准。

## 一、服务端重复启动：业界普遍做法

典型「重复启动未受控」问题。业界不允许同一台机器上无意运行两个相同服务实例。

### 1. 单实例锁（Named Mutex，Windows 最标准）

第一个服务启动时创建 `Global\MyLicenseServer`；第二个发现 Mutex 已存在则退出/提示/转连已有实例。Mutex 创建是原子操作，可解决「先检查再启动」的竞争条件。

### 2. 监听端口作为第二层保护

绑定固定端口失败 → 记录日志 → 立即退出。不得自动换随机端口、不得静默继续。端口检测只是兜底（占用也可能是别的程序）。

### 3. 启动器不应盲目启动 server.exe

正确顺序：请求 `/health`（或本地 IPC/进程检查）→ 已有服务则直接连接 → 没有才启动。

### 完整三层防护

```
GUI 启动
 ├─ ① 请求 /health → 成功：用已有服务
 ├─ ② 启动 Server.exe
 └─ Server.exe 内部创建 Named Mutex → 已存在：退出
```

### 进程管理

- GUI 与服务生命周期绑定：保存 PID / Job Object / IPC shutdown；不得按进程名全杀（可能误杀其他会话/其他安装目录/写入中的实例）。
- 服务独立运行：Windows Service / 托盘后台 / 守护进程，GUI 只是管理面板。

### 本项目（老板机许可证服务器）建议

| 防护层 | 作用 |
|---|---|
| Named Mutex | 从根本上保证只有一个 Server 实例 |
| 固定端口绑定 | 防止意外监听不同端口 |
| /health 接口 | 判断服务是否已运行 |
| PID / instanceId | 精确管理实例 |
| 日志 | 记录谁何时为何启动或退出 |
| 优雅关闭 | 避免 Kill 导致数据损坏 |

重复启动日志示例：`Startup rejected: another server instance is already running.`

## 二、客户端单实例

客户端与服务端逻辑不同：

- 服务端重复启动：第二实例直接退出；
- 客户端重复启动：第二实例通知第一实例「显示窗口并获得焦点」，然后退出。

锁名必须不同：`Global\Product_Server` / `Local\Product_Client`。

### 更标准的方案：激活已有窗口

Named Mutex + Named Pipe（Mutex 保单实例，Pipe 通知已有实例恢复窗口）。托盘隐藏场景：第二实例启动应触发 Show/Restore/Activate，不能因为窗口不可见就误判未运行。

### 不能只检查进程名

`Process.GetProcessesByName` 的问题：误判同名程序、多用户会话、竞争条件、正在退出的进程、无法激活原窗口。

### Global\ 还是 Local\

- `Global\`：整台电脑所有会话只允许一个；
- `Local\`：每个登录用户一个（普通桌面软件惯例）。

### 需要避免

1. Mutex 对象被 GC（必须静态字段持有）；
2. 主窗口启动后才创建锁（锁要尽可能早）；
3. 第二实例静默退出不通知第一实例；
4. 只靠客户端检查，服务端自身不加锁（服务可能被手动双击/更新器/开机启动项拉起）。

## 三、Electron 项目怎么做（官方方式）

Electron **不自己实现 Named Mutex**，用内置 API：

```ts
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();           // 第二实例：已通知主实例，立即退出
} else {
  app.on('second-instance', (e, argv, cwd, additionalData) => {
    activateMainWindow(); // 恢复/聚焦主窗口；可处理启动参数
  });
  app.whenReady().then(() => { createWindow(); ensureServerRunning(); });
}
```

关键：**锁必须在创建窗口、启动服务之前申请**（官方示例同）。`second-instance` 保证在主实例 ready 之后触发。传参用 `additionalData`（argv 顺序不稳）。

窗口激活逻辑：

```ts
function activateMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) { mainWindow = createMainWindow(); return; }
  if (mainWindow.isMinimized()) mainWindow.restore();
  if (!mainWindow.isVisible()) mainWindow.show();  // 托盘隐藏场景
  mainWindow.focus();
}
```

### 注意：单实例 ≠ 任务管理器里只有一个 exe

Electron 是 Chromium 多进程：`--type=renderer/gpu-process/utility` 都是正常子进程，不算重复启动。要禁的是「两个 Electron 主实例」。

### 本项目架构结论

```
Client.exe（Electron）
├── app.requestSingleInstanceLock()
├── BrowserWindow + 托盘
└── 检查并启动后端

Server.exe（license-server）
├── 自身单实例锁
├── 固定端口（绑定失败即退出）
├── /api/v1/ping（健康检查）
└── 授权服务
```

来源：[Electron app API](https://electronjs.org/docs/latest/api/app)

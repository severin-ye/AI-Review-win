# Electron 启动画面（Splash）与系统托盘最小化 — 联网调研

调研日期：2026-07-18
调研目的：为「双击启动后长时间无反馈」（启动画面）与「关闭按钮最小化到托盘」（托盘驻留）两个需求确定 Electron 官方推荐做法与社区惯例，作为实现依据。

## 关键结论

### 1. 启动画面：官方推荐 `show: false` + `ready-to-show`，并补 `backgroundColor`

Electron 官方 BrowserWindow 文档「Showing the window gracefully」一节明确推荐：

- 创建窗口时设 `show: false`，监听 `once('ready-to-show')` 后再 `win.show()`，避免白屏/闪烁；
- 同时建议给窗口设 `backgroundColor`，让窗口在页面加载完成前也有确定的底色，而不是默认白色。

来源：<https://www.electronjs.org/docs/latest/api/browser-window#showing-window-gracefully>

本项目主窗口已是 `show: false` + `ready-to-show` 模式（`app/desktop/main/index.ts`），因此启动画面方案为：

- `app.whenReady()` 后**立刻**创建一个小尺寸 splash 窗口（`frame: false`、`resizable: false`、`center: true`、`skipTaskbar: true`、`alwaysOnTop: true`、`show: true`），用户双击图标后立即可见；
- splash 内容用 **data: URL**（内联 SVG 图标 + 「正在启动…」文案），不引远程资源、不依赖磁盘文件路径，打包后最稳；
- 主窗口 `ready-to-show` 触发时：关闭 splash → 显示主窗口；
- splash 创建失败必须 try/catch，绝不能阻断正常启动流程；
- 主窗口补 `backgroundColor: '#f8fafc'`（与前端 slate-50 底色一致），消除加载期白闪。

### 2. 托盘：Windows 推荐 ICO 图标；单击恢复窗口

Electron 官方 Tray 文档确认：

- Windows 平台推荐使用 **ICO** 格式图标（本项目 `build/icon.ico` 已存在）；
- 支持事件 `click` / `double-click` / `right-click`；
- `setContextMenu()` 设置右键菜单、`setToolTip()` 设置悬停提示、`destroy()` 销毁。

来源：<https://www.electronjs.org/docs/latest/api/tray>

社区惯例上「单击恢复」与「双击恢复」两种都有。本实现选**单击恢复**：

- 窗口被隐藏（最小化到托盘）时，单击是最直接的恢复方式；
- KeePassXC issue #2956 指出：双击在窗口已可见时会先让窗口失焦（第一次点击被已有窗口"吃掉"），语义不稳定；单击没有这个问题。

来源：<https://github.com/keepassxreboot/keepassxc/issues/2956>（社区案例，仅作交互语义参考）

### 3. 关闭即最小化到托盘的实现要点

- 主窗口 `close` 事件：非退出意图时 `event.preventDefault()` + `win.hide()`，进程与侧车（sidecar）保持运行，许可证心跳不中断；
- 用 `isQuitting` 标志区分「用户点关闭」与「托盘菜单退出」：托盘「退出」置 `isQuitting = true` 后 `app.quit()`；
- `window-all-closed` 不再直接 `app.quit()`（窗口被 hide 后没有窗口，但进程要活着）；
- `before-quit` 里补 `tray?.destroy()`，并复用现有清理（许可证服务 dispose、停止 sidecar），保证「退出」后进程与 sidecar 真正退出。

## 采用方案汇总

| 需求 | 做法 | 依据 |
| --- | --- | --- |
| 启动白屏/无反馈 | whenReady 立即建 splash 小窗（data: URL），主窗口 ready-to-show 时关 splash 再 show | Electron 官方「Showing the window gracefully」 |
| 加载期底色 | 主窗口 `backgroundColor: '#f8fafc'` | Electron 官方建议 |
| 关闭到托盘 | close → preventDefault + hide；isQuitting 区分真退出 | Electron 标准模式 |
| 托盘图标 | `build/icon.ico`（Windows 推荐 ICO） | Electron Tray 官方文档 |
| 托盘恢复 | 单击恢复 + 右键菜单「显示主窗口 / 退出」 | 官方事件 + 社区惯例（单击语义更稳） |

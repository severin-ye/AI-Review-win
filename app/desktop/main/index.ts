import fs from 'node:fs'
import path from 'node:path'
import { BrowserWindow, Menu, Tray, app, dialog, ipcMain, nativeImage, shell } from 'electron'
import { startSidecar, stopSidecar, waitForHealthy, type SidecarHandle } from './sidecar'
import { createLicenseService, registerLicenseIpc, type LicenseIpcContext } from './license/ipc'

// ---- 单实例（任务 1a，依据 docs/research/single-instance-chatgpt.md）----
// 锁必须在 splash/窗口/sidecar/许可证服务等一切启动动作之前申请。
// 第二实例抢锁失败：Electron 已代为通知第一实例（second-instance 事件），本实例直接退出。
const hasSingleInstanceLock = app.requestSingleInstanceLock()
if (!hasSingleInstanceLock) {
  app.quit()
}

const isDev = !app.isPackaged

let mainWindow: BrowserWindow | null = null
let splash: BrowserWindow | null = null
let tray: Tray | null = null
let isQuitting = false
let sidecar: SidecarHandle | null = null
let backendUrl = ''
let licenseCtx: LicenseIpcContext | null = null
// 单实例时序：启动阶段（splash 在/主窗口未 ready）收到 second-instance 时挂起，ready-to-show 后补聚焦
let pendingSecondInstanceActivate = false
let mainWindowShownOnce = false

// ---- 启动画面（任务 2）----
// 依据 docs/research/electron-splash-tray.md：whenReady 后立即展示 splash，
// 主窗口 ready-to-show 时关闭 splash 再显示主窗口，消除"双击后长时间无反馈"。
// 内容用 data: URL（内联 SVG + 文案），不依赖磁盘文件路径，打包后同样可用。
const SPLASH_HTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  html,body{margin:0;height:100%;background:#0f172a;display:flex;align-items:center;justify-content:center;
    font-family:"Microsoft YaHei","Segoe UI",system-ui,sans-serif;color:#e2e8f0;user-select:none;-webkit-user-select:none}
  .box{display:flex;flex-direction:column;align-items:center;gap:14px}
  .title{font-size:18px;font-weight:600;letter-spacing:2px}
  .sub{font-size:12px;color:#94a3b8;letter-spacing:1px}
  .spinner{width:22px;height:22px;border:2px solid #334155;border-top-color:#38bdf8;border-radius:50%;
    animation:spin .8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
  <div class="box">
    <svg width="52" height="52" viewBox="0 0 64 64" fill="none">
      <rect x="4" y="4" width="56" height="56" rx="14" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
      <path d="M20 34l8 8 16-18" stroke="#38bdf8" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <div class="title">句读</div>
    <div class="spinner"></div>
    <div class="sub">正在启动，请稍候…</div>
  </div>
</body>
</html>`

function createSplash(): void {
  try {
    splash = new BrowserWindow({
      width: 360,
      height: 220,
      frame: false,
      resizable: false,
      center: true,
      skipTaskbar: true,
      alwaysOnTop: true,
      show: true,
      backgroundColor: '#0f172a',
    })
    splash.on('closed', () => {
      splash = null
    })
    const dataUrl = 'data:text/html;charset=utf-8;base64,' + Buffer.from(SPLASH_HTML, 'utf8').toString('base64')
    void splash.loadURL(dataUrl)
  } catch (err) {
    // splash 只是体验优化，失败绝不能阻断正常启动
    console.error('[splash] 创建失败（不阻断启动）', err)
    splash = null
  }
}

function closeSplash(): void {
  if (splash && !splash.isDestroyed()) splash.close()
  splash = null
}

async function bootstrap(): Promise<void> {
  // 0. 初始化许可证服务（先完成本地凭证校验，再创建窗口；心跳后台进行）
  const service = createLicenseService()
  await service.init()
  licenseCtx = registerLicenseIpc(service, () => mainWindow)

  // 1. 启动 Python FastAPI sidecar
  sidecar = await startSidecar({
    isDev,
    appPath: app.getAppPath(),
    resourcesPath: process.resourcesPath,
    onLog: (line) => console.log(line),
  })
  backendUrl = sidecar.url

  // 2. 轮询健康检查，后端就绪后再创建窗口
  await waitForHealthy(backendUrl)

  createWindow()
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    title: '句读 Caret',
    show: false,
    // 官方建议：与 ready-to-show 配合设置背景色，避免页面加载完成前白闪
    backgroundColor: '#f8fafc',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
    },
  })

  mainWindow.once('ready-to-show', () => {
    mainWindowShownOnce = true
    closeSplash()
    mainWindow?.show()
    // 启动期间有第二实例到来：就绪后补聚焦
    if (pendingSecondInstanceActivate) {
      pendingSecondInstanceActivate = false
      mainWindow?.focus()
    }
  })

  // 渲染层加载失败时也不能让 splash 永久悬挂：关掉 splash 并显示主窗口，让用户看到失败页面
  mainWindow.webContents.on('did-fail-load', () => {
    closeSplash()
    mainWindow?.show()
  })

  if (isDev && process.env['ELECTRON_RENDERER_URL']) {
    void mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    void mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }

  // 任务 3：托盘可用时，点关闭 = 最小化到托盘（进程与 sidecar 驻留，许可证心跳不中断）；
  // 仅当托盘菜单「退出」置 isQuitting 后才真正关闭窗口退出进程。
  mainWindow.on('close', (event) => {
    if (!isQuitting && tray) {
      event.preventDefault()
      mainWindow?.hide()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    mainWindowShownOnce = false
  })
}

// ---- 系统托盘（任务 3）----
function showMainWindow(): void {
  if (!mainWindow) return
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.show()
  mainWindow.focus()
}

/** 第二实例到来（任务 1a）：
 * 主窗口已就绪 → restore/show/focus（覆盖最小化与托盘隐藏两种场景）；
 * 仍在启动（splash 阶段或主窗口等待 ready-to-show）→ 挂起，ready-to-show 后补聚焦；
 * 主窗口已销毁（极端场景）→ 重建。 */
function activateForSecondInstance(): void {
  const win = mainWindow
  if (win && !win.isDestroyed() && mainWindowShownOnce) {
    showMainWindow()
    return
  }
  if ((win && !win.isDestroyed()) || (splash && !splash.isDestroyed())) {
    pendingSecondInstanceActivate = true
    return
  }
  createWindow()
}

if (hasSingleInstanceLock) {
  app.on('second-instance', activateForSecondInstance)
}

async function resolveTrayIcon(): Promise<Electron.NativeImage | null> {
  const candidates = [
    path.join(app.getAppPath(), 'build', 'icon.ico'), // dev：项目根 build/icon.ico
    path.join(process.resourcesPath ?? '', 'icon.ico'), // 打包后若经 extraResources 分发
  ]
  for (const candidate of candidates) {
    try {
      if (candidate && fs.existsSync(candidate)) {
        const image = nativeImage.createFromPath(candidate)
        if (!image.isEmpty()) return image
      }
    } catch {
      // 尝试下一个候选路径
    }
  }
  try {
    // 兜底：exe 自身图标（electron-builder 打包时已把 build/icon.ico 嵌入 exe）
    const image = await app.getFileIcon(process.execPath)
    return image.isEmpty() ? null : image
  } catch {
    return null
  }
}

let trayMenu: Menu | null = null

async function createTray(): Promise<void> {
  try {
    const icon = await resolveTrayIcon()
    if (!icon) {
      console.warn('[tray] 无可用图标，跳过托盘创建（关闭窗口将直接退出）')
      return
    }
    tray = new Tray(icon)
    tray.setToolTip('句读 Caret')
    const menu = Menu.buildFromTemplate([
      { label: '显示主窗口', click: showMainWindow },
      { type: 'separator' },
      {
        label: '退出 句读 Caret',
        click: () => {
          isQuitting = true
          app.quit()
        },
      },
    ])
    tray.setContextMenu(menu)
    trayMenu = menu
    // 单击托盘图标恢复主窗口（调研结论：单击语义比双击稳定，见 docs/research/electron-splash-tray.md）
    tray.on('click', showMainWindow)
  } catch (err) {
    // 托盘失败时退化为"关闭即退出"，避免窗口被隐藏后无处可寻
    console.error('[tray] 创建失败（关闭窗口将直接退出）', err)
    tray = null
    trayMenu = null
  }
}

// ---- IPC ----
ipcMain.handle('backend:url', () => backendUrl)
ipcMain.handle('app:version', () => app.getVersion())
// M5：在系统文件管理器中定位导出产物（仅接受字符串路径，由渲染层传入后端返回的绝对路径）
ipcMain.handle('shell:showItemInFolder', (_event, targetPath: unknown) => {
  if (typeof targetPath !== 'string' || targetPath.length === 0) return
  shell.showItemInFolder(targetPath)
})

// ---- 生命周期 ----
if (hasSingleInstanceLock) {
  void app.whenReady().then(async () => {
    // splash 最先展示，覆盖许可证校验 + sidecar 启动 + 健康检查这段耗时
    createSplash()
    try {
      await bootstrap()
      await createTray()
    } catch (err) {
      console.error('[bootstrap] 启动失败', err)
      closeSplash()
      dialog.showErrorBox('启动失败', err instanceof Error ? err.message : String(err))
      app.quit()
    }
  })
}

app.on('window-all-closed', () => {
  // 托盘可用时进程驻留（窗口只是被隐藏，不会走到这里）；
  // 托盘不可用时退化为传统行为：窗口全关即退出，避免"关不掉也找不到"的驻留进程。
  if (!tray) app.quit()
})

app.on('before-quit', () => {
  isQuitting = true
  tray?.destroy()
  tray = null
  trayMenu = null
  closeSplash()
  licenseCtx?.unsubscribe()
  licenseCtx?.service.dispose()
  licenseCtx = null
  stopSidecar(sidecar)
  sidecar = null
})

// ---- e2e/调试自省钩子（渲染层勿用）----
export interface ShellHooks {
  getMainWindow: () => BrowserWindow | null
  getSplash: () => BrowserWindow | null
  getTray: () => Tray | null
  getTrayMenu: () => Menu | null
}

/** 仅供 e2e/调试自省：暴露 shell 内部实例，便于合成事件验证托盘接线（scripts/e2e-shell-entry.ts 使用）。 */
export function getShellHooksForTest(): ShellHooks {
  return {
    getMainWindow: () => mainWindow,
    getSplash: () => splash,
    getTray: () => tray,
    getTrayMenu: () => trayMenu,
  }
}

import path from 'node:path'
import { BrowserWindow, app, ipcMain, shell } from 'electron'
import { startSidecar, stopSidecar, waitForHealthy, type SidecarHandle } from './sidecar'
import { createLicenseService, registerLicenseIpc, type LicenseIpcContext } from './license/ipc'

const isDev = !app.isPackaged

let mainWindow: BrowserWindow | null = null
let sidecar: SidecarHandle | null = null
let backendUrl = ''
let licenseCtx: LicenseIpcContext | null = null

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
    title: 'AI 审校助手',
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
    },
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  if (isDev && process.env['ELECTRON_RENDERER_URL']) {
    void mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    void mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
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
void app.whenReady().then(bootstrap)

app.on('window-all-closed', () => {
  app.quit()
})

app.on('before-quit', () => {
  licenseCtx?.unsubscribe()
  licenseCtx?.service.dispose()
  licenseCtx = null
  stopSidecar(sidecar)
  sidecar = null
})

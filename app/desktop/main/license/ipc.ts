/**
 * 许可证 IPC：注册 license:* handler，并向渲染层 push license:stateChanged。
 */
import path from 'node:path'
import { app, ipcMain, safeStorage, type BrowserWindow } from 'electron'
import { getDeviceId } from './deviceId'
import { LicenseService } from './licenseService'
import { loadPublicKeyPem } from './publicKey'
import { ClientConfigStore, CredentialStorage } from './storage'
import type { ActivateParams, LicenseOpResult } from './types'

export interface LicenseIpcContext {
  service: LicenseService
  unsubscribe: () => void
}

/** 装配许可证服务（Electron 依赖在这里注入；核心逻辑保持无 electron 可测）。 */
export function createLicenseService(): LicenseService {
  const userData = app.getPath('userData')
  const storage = new CredentialStorage(
    path.join(userData, 'license.dat'),
    safeStorage,
    (msg) => console.warn(msg),
  )
  const clientConfig = new ClientConfigStore(path.join(userData, 'license-client-config.json'))

  return new LicenseService({
    storage,
    getDeviceId: () => getDeviceId(userData, safeStorage, (msg) => console.warn(msg)),
    getPublicKeyPem: () =>
      loadPublicKeyPem({
        resourcesPath: process.resourcesPath,
        appPath: app.getAppPath(),
        mainOutDir: __dirname,
      }),
    getClientVersion: () => app.getVersion(),
    saveServerUrl: (url) => clientConfig.saveServerUrl(url),
    loadServerUrl: () => clientConfig.loadServerUrl(),
    platform: process.platform,
    osVersion: process.getSystemVersion(),
    log: (msg) => console.log(msg),
  })
}

/** 注册 IPC handler + 状态推送。返回 context 供生命周期管理。 */
export function registerLicenseIpc(
  service: LicenseService,
  getWindow: () => BrowserWindow | null,
): LicenseIpcContext {
  ipcMain.handle('license:getState', () => service.getState())

  ipcMain.handle('license:activate', (_event, params: ActivateParams) => {
    // 不向日志打印完整 license key / signature
    const safe: ActivateParams = {
      serverUrl: typeof params?.serverUrl === 'string' ? params.serverUrl : '',
      licenseKey: typeof params?.licenseKey === 'string' ? params.licenseKey : '',
      deviceName: typeof params?.deviceName === 'string' ? params.deviceName : '',
    }
    return service.activate(safe)
  })

  ipcMain.handle('license:testConnection', (_event, serverUrl: unknown) => {
    return service.testConnection(typeof serverUrl === 'string' ? serverUrl : '')
  })

  ipcMain.handle('license:refresh', async (): Promise<LicenseOpResult> => {
    const ok = await service.refresh()
    return ok
      ? { success: true }
      : { success: false, reasonCode: service.getState().reasonCode, message: service.getState().message ?? '刷新失败' }
  })

  ipcMain.handle('license:getStatus', () => service.getState())

  ipcMain.handle('license:logout', () => {
    service.logout()
    return { success: true }
  })

  const unsubscribe = service.subscribe((snapshot) => {
    getWindow()?.webContents.send('license:stateChanged', snapshot)
  })

  return { service, unsubscribe }
}

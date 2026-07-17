import { contextBridge, ipcRenderer } from 'electron'

export interface RendererApi {
  /** FastAPI sidecar 的 baseUrl，例如 http://127.0.0.1:54321 */
  getBackendUrl: () => Promise<string>
  /** 应用版本号（来自 package.json） */
  getAppVersion: () => Promise<string>
  /** 在系统文件管理器中定位文件（主进程 shell.showItemInFolder） */
  showItemInFolder: (path: string) => Promise<void>
}

/* ---------- 许可证 ---------- */

export interface LicenseSnapshotDto {
  state: string
  usable: boolean
  reasonCode: string | null
  message: string | null
  licenseId: string | null
  deviceId: string | null
  features: string[]
  licenseVersion: number | null
  issuedAt: string | null
  expiresAt: string | null
  remainingSeconds: number | null
  lastHeartbeatAt: string | null
  lastServerTime: string | null
  serverReachable: boolean | null
  serverUrl: string | null
  expiryWarning: { thresholdSeconds: number; remainingSeconds: number } | null
}

export interface LicenseApi {
  /** 当前状态快照 */
  getState: () => Promise<LicenseSnapshotDto>
  /** 激活（幂等：重复点击不重复请求） */
  activate: (params: { serverUrl: string; licenseKey: string; deviceName?: string }) => Promise<{
    success: boolean
    reasonCode?: string | null
    message?: string | null
  }>
  /** 连接测试（GET /api/v1/ping） */
  testConnection: (serverUrl: string) => Promise<{
    ok: boolean
    serverTime?: string | null
    keyFingerprint?: string | null
    message?: string | null
  }>
  /** 主动刷新凭证 / 重新验证 */
  refresh: () => Promise<{ success: boolean; reasonCode?: string | null; message?: string | null }>
  /** 完整状态信息（同 getState，含截止时间/剩余时间/最近心跳/服务器状态） */
  getStatus: () => Promise<LicenseSnapshotDto>
  /** 清除本地凭证，回到未激活状态 */
  logout: () => Promise<{ success: boolean }>
  /** 订阅状态变更推送；返回退订函数 */
  onStateChanged: (callback: (snapshot: LicenseSnapshotDto) => void) => () => void
}

const licenseApi: LicenseApi = {
  getState: () => ipcRenderer.invoke('license:getState') as Promise<LicenseSnapshotDto>,
  activate: (params) =>
    ipcRenderer.invoke('license:activate', params) as Promise<{
      success: boolean
      reasonCode?: string | null
      message?: string | null
    }>,
  testConnection: (serverUrl) =>
    ipcRenderer.invoke('license:testConnection', serverUrl) as Promise<{
      ok: boolean
      serverTime?: string | null
      keyFingerprint?: string | null
      message?: string | null
    }>,
  refresh: () =>
    ipcRenderer.invoke('license:refresh') as Promise<{
      success: boolean
      reasonCode?: string | null
      message?: string | null
    }>,
  getStatus: () => ipcRenderer.invoke('license:getStatus') as Promise<LicenseSnapshotDto>,
  logout: () => ipcRenderer.invoke('license:logout') as Promise<{ success: boolean }>,
  onStateChanged: (callback) => {
    const listener = (_event: Electron.IpcRendererEvent, snapshot: LicenseSnapshotDto): void => {
      callback(snapshot)
    }
    ipcRenderer.on('license:stateChanged', listener)
    return () => {
      ipcRenderer.removeListener('license:stateChanged', listener)
    }
  },
}

const api: RendererApi = {
  getBackendUrl: () => ipcRenderer.invoke('backend:url') as Promise<string>,
  getAppVersion: () => ipcRenderer.invoke('app:version') as Promise<string>,
  showItemInFolder: (path: string) => ipcRenderer.invoke('shell:showItemInFolder', path) as Promise<void>,
}

contextBridge.exposeInMainWorld('api', api)
contextBridge.exposeInMainWorld('licenseApi', licenseApi)

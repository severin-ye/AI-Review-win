import { contextBridge, ipcRenderer } from 'electron'

export interface RendererApi {
  /** FastAPI sidecar 的 baseUrl，例如 http://127.0.0.1:54321 */
  getBackendUrl: () => Promise<string>
  /** 应用版本号（来自 package.json） */
  getAppVersion: () => Promise<string>
  /** 在系统文件管理器中定位文件（主进程 shell.showItemInFolder） */
  showItemInFolder: (path: string) => Promise<void>
}

const api: RendererApi = {
  getBackendUrl: () => ipcRenderer.invoke('backend:url') as Promise<string>,
  getAppVersion: () => ipcRenderer.invoke('app:version') as Promise<string>,
  showItemInFolder: (path: string) => ipcRenderer.invoke('shell:showItemInFolder', path) as Promise<void>,
}

contextBridge.exposeInMainWorld('api', api)

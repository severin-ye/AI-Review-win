/** 预加载脚本通过 contextBridge 暴露的 window.api 类型声明 */
export interface RendererApi {
  getBackendUrl: () => Promise<string>
  getAppVersion: () => Promise<string>
  /** 在系统文件管理器中定位文件（Electron shell.showItemInFolder） */
  showItemInFolder: (path: string) => Promise<void>
}

declare global {
  interface Window {
    api: RendererApi
  }
}

export {}

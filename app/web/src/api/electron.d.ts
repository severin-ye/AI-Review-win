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
    /** 预加载脚本暴露的许可证 API（浏览器预览模式下不存在） */
    licenseApi?: import('@/license/types').LicenseApi
  }
}

export {}

/**
 * 渲染层许可证类型（与主进程 app/desktop/main/license/types.ts 等价拷贝，
 * 两端 tsconfig 独立，不互相 import）。
 */

export type LicenseState =
  | 'UNINITIALIZED'
  | 'NO_LICENSE'
  | 'VALIDATING_LOCAL'
  | 'LOCAL_VALID'
  | 'LOCAL_EXPIRED'
  | 'CONNECTING_SERVER'
  | 'SERVER_ACTIVE'
  | 'SERVER_UNREACHABLE'
  | 'SUSPENDED'
  | 'REVOKED'
  | 'INVALID_SIGNATURE'
  | 'DEVICE_MISMATCH'
  | 'TIME_TAMPER_DETECTED'

export interface LicenseSnapshot {
  state: LicenseState
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

export interface LicenseOpResult {
  success: boolean
  reasonCode?: string | null
  message?: string | null
}

export interface TestConnectionResult {
  ok: boolean
  serverTime?: string | null
  keyFingerprint?: string | null
  message?: string | null
}

export interface LicenseApi {
  getState: () => Promise<LicenseSnapshot>
  activate: (params: {
    serverUrl: string
    licenseKey: string
    deviceName?: string
  }) => Promise<LicenseOpResult>
  testConnection: (serverUrl: string) => Promise<TestConnectionResult>
  refresh: () => Promise<LicenseOpResult>
  getStatus: () => Promise<LicenseSnapshot>
  logout: () => Promise<{ success: boolean }>
  onStateChanged: (callback: (snapshot: LicenseSnapshot) => void) => () => void
}

/** 错误码 -> 中文文案（与服务端 schemas.py ERROR_MESSAGES 一致，前端内置兜底） */
export const LICENSE_ERROR_MESSAGES: Record<string, string> = {
  LICENSE_NOT_FOUND: '许可证密钥无效，请核对后重试',
  LICENSE_PENDING: '许可证尚未激活，请先完成激活',
  LICENSE_SUSPENDED: '许可证已被管理员暂停，请联系管理员',
  LICENSE_REVOKED: '许可证已被管理员撤销',
  LICENSE_EXPIRED: '许可证已到期，请联系管理员续期',
  LICENSE_DEVICE_LIMIT_REACHED: '已达设备数量上限，请先在管理端解绑其他设备',
  DEVICE_NOT_REGISTERED: '设备未注册，请先激活',
  DEVICE_REVOKED: '设备已被解绑，请重新激活',
  DEVICE_MISMATCH: '设备与许可证不匹配',
  CLIENT_VERSION_TOO_OLD: '客户端版本过旧，请升级后重试',
  INVALID_LICENSE_SIGNATURE: '许可证凭证签名校验失败',
  INVALID_REQUEST_SIGNATURE: '请求签名校验失败',
  SERVER_TIME_INVALID: '本机时间与服务器偏差过大，请校准系统时间',
  LICENSE_REFRESH_REQUIRED: '许可证信息已更新，请刷新凭证',
  SERVER_UNREACHABLE: '无法连接许可证服务器',
  REQUEST_TIMEOUT: '请求超时，请稍后重试',
  INTERNAL_SERVER_ERROR: '服务器内部错误，请稍后重试',
  REPLAY_DETECTED: '检测到重放请求，已拒绝',
  RATE_LIMITED: '请求过于频繁，请稍后再试',
}

export function licenseErrorMessage(reasonCode: string | null | undefined, fallback?: string | null): string {
  if (reasonCode && LICENSE_ERROR_MESSAGES[reasonCode]) return LICENSE_ERROR_MESSAGES[reasonCode]
  return fallback ?? '未知错误'
}

/** 取预加载注入的许可证 API；浏览器预览模式返回 null。用 globalThis 结构类型以便两端 tsconfig 都能编译。 */
export function getLicenseApi(): LicenseApi | null {
  const w = globalThis as { licenseApi?: LicenseApi }
  return w.licenseApi ?? null
}

/** 状态 -> 中文展示文案 */
export const LICENSE_STATE_LABELS: Record<LicenseState, string> = {
  UNINITIALIZED: '初始化中',
  NO_LICENSE: '未激活',
  VALIDATING_LOCAL: '校验本地许可证中',
  LOCAL_VALID: '已激活（本地校验）',
  LOCAL_EXPIRED: '许可证已过期',
  CONNECTING_SERVER: '正在连接许可证服务器',
  SERVER_ACTIVE: '已激活（服务器已确认）',
  SERVER_UNREACHABLE: '服务器暂不可达（许可证仍可用）',
  SUSPENDED: '许可证已暂停',
  REVOKED: '许可证已撤销',
  INVALID_SIGNATURE: '许可证凭证校验失败',
  DEVICE_MISMATCH: '设备与许可证不匹配',
  TIME_TAMPER_DETECTED: '系统时间异常',
}

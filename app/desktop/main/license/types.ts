/**
 * 许可证模块共享类型与常量（主进程侧）。
 * 渲染层在 app/web/src/license/types.ts 有一份等价拷贝（两端 tsconfig 独立，不互相 import）。
 */

/** 许可证状态机状态 */
export type LicenseState =
  | 'UNINITIALIZED' // 服务尚未初始化
  | 'NO_LICENSE' // 无本地凭证
  | 'VALIDATING_LOCAL' // 启动校验本地凭证中
  | 'LOCAL_VALID' // 本地凭证验签通过且未过期（离线放行，后台继续服务器检查）
  | 'LOCAL_EXPIRED' // 本地凭证已过期（且刷新失败）
  | 'CONNECTING_SERVER' // 无可用本地凭证，正在连接服务器（激活/刷新进行中）
  | 'SERVER_ACTIVE' // 服务器确认 active
  | 'SERVER_UNREACHABLE' // 服务器不可达（本地凭证仍有效，不锁定）
  | 'SUSPENDED' // 已暂停（验签可信），锁定但保留凭证
  | 'REVOKED' // 已撤销（验签可信），锁定且凭证已隔离
  | 'INVALID_SIGNATURE' // 本地凭证验签失败
  | 'DEVICE_MISMATCH' // 凭证与本机设备绑定不符
  | 'TIME_TAMPER_DETECTED' // 检测到系统时间回拨

/** 服务器签发的许可证凭证 token（canonical JSON + Ed25519 签名对象） */
export interface LicenseToken {
  schema_version: number
  license_id: string
  device_id: string
  issued_at: string
  expires_at: string | null
  features: string[]
  license_version: number
}

/** 本地持久化凭证（safeStorage 加密后写入 userData/license.dat） */
export interface StoredCredential {
  token: LicenseToken
  signature: string
  server_url: string
  /** 最近一次验签通过的服务器 server_time（ISO Z） */
  last_trusted_server_time: string | null
  /** 本机观测到的最大时间（ISO），用于时间回拨检测 */
  max_observed_time: string | null
  /** 已发送过的到期提醒阈值（秒），每档只提醒一次 */
  last_warning_threshold_sent: number | null
  /** 本地撤销标记（收到验签通过的 revoked 心跳后置位） */
  revoked: boolean
}

/** 推送给渲染层的完整状态快照 */
export interface LicenseSnapshot {
  state: LicenseState
  /** 当前是否放行核心功能（连接失败 ≠ 撤销；本地凭证有效即可用） */
  usable: boolean
  /** 最近一次服务器 reason_code（若有） */
  reasonCode: string | null
  /** 中文提示文案 */
  message: string | null
  licenseId: string | null
  deviceId: string | null
  features: string[]
  licenseVersion: number | null
  issuedAt: string | null
  expiresAt: string | null
  /** 剩余秒数（<0 表示已过期；null 表示未知/永久） */
  remainingSeconds: number | null
  /** 最近一次成功心跳的本机接收时间（ISO） */
  lastHeartbeatAt: string | null
  /** 最近一次验签通过的服务器时间（ISO Z） */
  lastServerTime: string | null
  /** 服务器连通状态：true 可达 / false 不可达 / null 未知 */
  serverReachable: boolean | null
  serverUrl: string | null
  /** 到期提醒：剩余时间首次低于 3天/1天/1小时 时给出 */
  expiryWarning: { thresholdSeconds: number; remainingSeconds: number } | null
}

/** 激活参数 */
export interface ActivateParams {
  serverUrl: string
  licenseKey: string
  deviceName?: string
}

/** IPC 层统一操作结果 */
export interface LicenseOpResult {
  success: boolean
  reasonCode?: string | null
  message?: string | null
}

/** 连接测试（ping）结果 */
export interface TestConnectionResult {
  ok: boolean
  serverTime?: string | null
  keyFingerprint?: string | null
  message?: string | null
}

/** 错误码 -> 中文文案（与服务端 schemas.py ERROR_MESSAGES 保持一致） */
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

export function errorMessageOf(reasonCode: string | null | undefined): string {
  if (!reasonCode) return '未知错误'
  return LICENSE_ERROR_MESSAGES[reasonCode] ?? '未知错误'
}

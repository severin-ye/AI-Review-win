/**
 * 许可证客户端运行配置：集中管理，支持 env 变量覆盖（供测试把心跳改成 5 秒等）。
 * 不要在其它模块散落硬编码这些数值。
 */

export interface LicenseClientConfig {
  /** 心跳周期（秒），默认 300；服务器响应 next_heartbeat_seconds 时优先用服务器值 */
  heartbeatIntervalSeconds: number
  /** 单次请求超时（秒），默认 10 */
  requestTimeoutSeconds: number
  /** 心跳网络失败后的快速重试延迟（秒），默认 [5, 15]，之后等下个周期 */
  retryDelaysSeconds: number[]
  /** 时间回拨检测容差（秒），默认 300（与服务端 timestamp_tolerance_seconds 对齐） */
  clockSkewToleranceSeconds: number
  /** 到期提醒阈值（秒）：剩余 3 天 / 1 天 / 1 小时 各提醒一次 */
  expiryWarningThresholdsSeconds: number[]
}

export const DEFAULT_LICENSE_CONFIG: LicenseClientConfig = {
  heartbeatIntervalSeconds: 300,
  requestTimeoutSeconds: 10,
  retryDelaysSeconds: [5, 15],
  clockSkewToleranceSeconds: 300,
  expiryWarningThresholdsSeconds: [3 * 86400, 86400, 3600],
}

type EnvLike = Record<string, string | undefined>

function envInt(env: EnvLike, name: string, fallback: number): number {
  const raw = env[name]
  if (raw === undefined || raw.trim() === '') return fallback
  const n = Number.parseInt(raw, 10)
  return Number.isFinite(n) && n > 0 ? n : fallback
}

function envIntList(env: EnvLike, name: string, fallback: number[]): number[] {
  const raw = env[name]
  if (raw === undefined || raw.trim() === '') return fallback
  const parts = raw
    .split(',')
    .map((s) => Number.parseInt(s.trim(), 10))
    .filter((n) => Number.isFinite(n) && n >= 0)
  return parts.length > 0 ? parts : fallback
}

/** 读取配置（env 可注入，便于测试）。 */
export function loadLicenseConfig(env: EnvLike = process.env): LicenseClientConfig {
  return {
    heartbeatIntervalSeconds: envInt(
      env,
      'AI_REVIEW_LICENSE_HEARTBEAT_INTERVAL_SECONDS',
      DEFAULT_LICENSE_CONFIG.heartbeatIntervalSeconds,
    ),
    requestTimeoutSeconds: envInt(
      env,
      'AI_REVIEW_LICENSE_REQUEST_TIMEOUT_SECONDS',
      DEFAULT_LICENSE_CONFIG.requestTimeoutSeconds,
    ),
    retryDelaysSeconds: envIntList(
      env,
      'AI_REVIEW_LICENSE_RETRY_DELAYS',
      DEFAULT_LICENSE_CONFIG.retryDelaysSeconds,
    ),
    clockSkewToleranceSeconds: envInt(
      env,
      'AI_REVIEW_LICENSE_CLOCK_SKEW_TOLERANCE_SECONDS',
      DEFAULT_LICENSE_CONFIG.clockSkewToleranceSeconds,
    ),
    expiryWarningThresholdsSeconds: envIntList(
      env,
      'AI_REVIEW_LICENSE_EXPIRY_WARNINGS',
      DEFAULT_LICENSE_CONFIG.expiryWarningThresholdsSeconds,
    ),
  }
}

/**
 * 时间回拨检测与到期判定（纯函数，不依赖 electron，可注入时钟，vitest 可测）。
 *
 * 语义与服务端 license_server/core/timeutil.py 对齐：
 *   - detectTimeRollback：观测时间比最近可信时间早超过容差（默认 300s）即回拨
 *   - 每次验签通过的心跳更新可信时间（last_trusted_server_time）
 *   - max_observed_time 记录本机观测到的最大时间，先检测后更新
 */

export interface TimeGuardState {
  last_trusted_server_time: string | null
  max_observed_time: string | null
}

/** 解析 ISO 时间为 epoch 毫秒；非法/空返回 null。 */
export function parseIsoMs(value: string | null | undefined): number | null {
  if (!value) return null
  const ms = Date.parse(value)
  return Number.isFinite(ms) ? ms : null
}

/**
 * 检测时间回拨：observed 比参考时间（lastTrusted / maxObserved 的较大者）早超过容差。
 * 无任何可信记录时无法判定，返回 false。
 */
export function detectTimeRollback(
  state: TimeGuardState,
  observedMs: number,
  toleranceSeconds: number,
): boolean {
  const trustedMs = parseIsoMs(state.last_trusted_server_time)
  const observedMaxMs = parseIsoMs(state.max_observed_time)
  const reference = Math.max(trustedMs ?? Number.NEGATIVE_INFINITY, observedMaxMs ?? Number.NEGATIVE_INFINITY)
  if (!Number.isFinite(reference)) return false
  return reference - observedMs > toleranceSeconds * 1000
}

/** 先检测后调用：把本机当前时间并入 max_observed_time，返回新的记录值（ISO）。 */
export function advanceMaxObserved(state: TimeGuardState, observedMs: number): string {
  const prev = parseIsoMs(state.max_observed_time)
  const next = prev === null ? observedMs : Math.max(prev, observedMs)
  return new Date(next).toISOString()
}

/** 验签通过的服务器时间 → 更新可信时间（只增不减）。 */
export function advanceTrustedTime(state: TimeGuardState, serverTimeIso: string): string {
  const incoming = parseIsoMs(serverTimeIso)
  const prev = parseIsoMs(state.last_trusted_server_time)
  if (incoming === null) return state.last_trusted_server_time ?? serverTimeIso
  const next = prev === null ? incoming : Math.max(prev, incoming)
  return new Date(next).toISOString()
}

/** 凭证是否已过期（expires_at 为 null 视为永久）。 */
export function isExpired(expiresAt: string | null | undefined, nowMs: number): boolean {
  const ms = parseIsoMs(expiresAt)
  if (ms === null) return false
  return nowMs > ms
}

/** 剩余秒数（expires_at 为 null 返回 null；可为负）。 */
export function remainingSeconds(expiresAt: string | null | undefined, nowMs: number): number | null {
  const ms = parseIsoMs(expiresAt)
  if (ms === null) return null
  return Math.floor((ms - nowMs) / 1000)
}

/**
 * 到期提醒判定：阈值降序排列（如 [3d, 1d, 1h]）。
 * 返回当前应处于的提醒档位（首个 remaining <= 阈值的档），且该档尚未提醒过；
 * 已提醒过同档或更小档时返回 null（每档只提醒一次）。
 */
export function dueExpiryWarning(
  expiresAt: string | null | undefined,
  nowMs: number,
  thresholdsSeconds: number[],
  lastWarningThresholdSent: number | null,
): { thresholdSeconds: number; remainingSeconds: number } | null {
  const remaining = remainingSeconds(expiresAt, nowMs)
  if (remaining === null || remaining < 0) return null
  const sorted = [...thresholdsSeconds].sort((a, b) => b - a)
  // 找到命中的最小档位（最紧急的一档）
  let hit: number | null = null
  for (const t of sorted) {
    if (remaining <= t) hit = t
  }
  if (hit === null) return null
  // 已提醒过同档或更小档（lastWarningThresholdSent <= hit）则不重复
  if (lastWarningThresholdSent !== null && lastWarningThresholdSent <= hit) return null
  return { thresholdSeconds: hit, remainingSeconds: remaining }
}

/**
 * timeGuard 纯函数测试（任务书 §十九：时间回拨、可信时间、到期、剩余时间、提醒档位）。
 */
import { describe, expect, it } from 'vitest'
import {
  advanceMaxObserved,
  advanceTrustedTime,
  detectTimeRollback,
  dueExpiryWarning,
  isExpired,
  parseIsoMs,
  remainingSeconds,
  type TimeGuardState,
} from '../timeGuard'

const T0 = Date.parse('2026-07-17T12:00:00Z')
const TOL = 300 // 秒

function state(lastTrusted: string | null, maxObserved: string | null): TimeGuardState {
  return { last_trusted_server_time: lastTrusted, max_observed_time: maxObserved }
}

describe('时间回拨检测', () => {
  it('系统时间早于 max_observed 超过容差 → 判定回拨', () => {
    const s = state(null, new Date(T0 + 10_000 * 1000).toISOString())
    // 当前时间比记录早 10000 秒，远超 300 秒容差
    expect(detectTimeRollback(s, T0, TOL)).toBe(true)
  })

  it('偏差在容差内 → 放行', () => {
    const s = state(null, new Date(T0 + 200 * 1000).toISOString())
    expect(detectTimeRollback(s, T0, TOL)).toBe(false)
  })

  it('系统时间早于可信服务器时间超容差 → 判定回拨', () => {
    const s = state(new Date(T0 + 1000 * 1000).toISOString(), null)
    expect(detectTimeRollback(s, T0, TOL)).toBe(true)
  })

  it('无任何记录 → 无法判定（放行）', () => {
    expect(detectTimeRollback(state(null, null), T0, TOL)).toBe(false)
  })

  it('参考时间取 lastTrusted 与 maxObserved 的较大者', () => {
    // lastTrusted 较旧、maxObserved 较新：按 maxObserved 判定
    const s = state(new Date(T0).toISOString(), new Date(T0 + 1000 * 1000).toISOString())
    expect(detectTimeRollback(s, T0, TOL)).toBe(true)
    expect(detectTimeRollback(s, T0 + 900 * 1000, TOL)).toBe(false)
  })
})

describe('可信时间 / 观测时间推进', () => {
  it('max_observed_time 只增不减', () => {
    const s = state(null, new Date(T0 + 5000).toISOString())
    expect(parseIsoMs(advanceMaxObserved(s, T0))).toBe(T0 + 5000)
    expect(parseIsoMs(advanceMaxObserved(s, T0 + 9000))).toBe(T0 + 9000)
  })

  it('可信服务器时间只增不减', () => {
    const s = state(new Date(T0 + 5000).toISOString(), null)
    expect(parseIsoMs(advanceTrustedTime(s, new Date(T0).toISOString()))).toBe(T0 + 5000)
    expect(parseIsoMs(advanceTrustedTime(s, new Date(T0 + 8000).toISOString()))).toBe(T0 + 8000)
  })

  it('空记录时直接采用新值', () => {
    expect(parseIsoMs(advanceMaxObserved(state(null, null), T0))).toBe(T0)
    expect(parseIsoMs(advanceTrustedTime(state(null, null), new Date(T0).toISOString()))).toBe(T0)
  })
})

describe('到期判定与剩余时间', () => {
  const expires = new Date(T0 + 3600 * 1000).toISOString()

  it('未过期 / 已过期', () => {
    expect(isExpired(expires, T0)).toBe(false)
    expect(isExpired(expires, T0 + 3601 * 1000)).toBe(true)
  })

  it('expires_at 为 null 视为永久', () => {
    expect(isExpired(null, T0)).toBe(false)
    expect(remainingSeconds(null, T0)).toBeNull()
  })

  it('剩余秒数（可为负）', () => {
    expect(remainingSeconds(expires, T0)).toBe(3600)
    expect(remainingSeconds(expires, T0 + 3700 * 1000)).toBe(-100)
  })
})

describe('到期提醒档位（3 天 / 1 天 / 1 小时各触发一次）', () => {
  const THRESHOLDS = [3 * 86400, 86400, 3600]
  const expires = new Date(T0 + 4 * 86400 * 1000).toISOString() // 4 天后到期

  it('剩余 > 3 天不提醒', () => {
    expect(dueExpiryWarning(expires, T0, THRESHOLDS, null)).toBeNull()
  })

  it('跌破 3 天 → 提醒 3 天档', () => {
    const now = T0 + 1 * 86400 * 1000 + 1000 // 剩余约 2 天 23.x 小时
    const due = dueExpiryWarning(expires, now, THRESHOLDS, null)
    expect(due?.thresholdSeconds).toBe(3 * 86400)
  })

  it('同档不重复提醒', () => {
    const now = T0 + 2 * 86400 * 1000 // 剩余 2 天
    expect(dueExpiryWarning(expires, now, THRESHOLDS, 3 * 86400)).toBeNull()
  })

  it('跌破 1 天 → 提醒 1 天档（已提醒过 3 天档）', () => {
    const now = T0 + 3 * 86400 * 1000 + 1000 // 剩余约 23 小时
    const due = dueExpiryWarning(expires, now, THRESHOLDS, 3 * 86400)
    expect(due?.thresholdSeconds).toBe(86400)
  })

  it('跌破 1 小时 → 提醒 1 小时档（已提醒过 1 天档）', () => {
    const now = T0 + 4 * 86400 * 1000 - 1800 * 1000 // 剩余 30 分钟
    const due = dueExpiryWarning(expires, now, THRESHOLDS, 86400)
    expect(due?.thresholdSeconds).toBe(3600)
  })

  it('1 小时档提醒过后不再提醒', () => {
    const now = T0 + 4 * 86400 * 1000 - 600 * 1000
    expect(dueExpiryWarning(expires, now, THRESHOLDS, 3600)).toBeNull()
  })

  it('已过期不再提醒', () => {
    const now = T0 + 5 * 86400 * 1000
    expect(dueExpiryWarning(expires, now, THRESHOLDS, null)).toBeNull()
  })
})

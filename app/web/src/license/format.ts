/** 时间显示工具：统一用本地时区完整时间 + 时区名。 */

/** 完整日期时间 + 时区名，例如 "2026/7/20 15:04:05（中国标准时间）"。 */
export function formatLocalDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
  const text = d.toLocaleString('zh-CN', { hour12: false })
  return `${text}（${timeZone}）`
}

/** 剩余时间人性化展示，如 "3 天 4 小时"。 */
export function formatRemaining(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 0) return '已过期'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${String(days)} 天 ${String(hours)} 小时`
  if (hours > 0) return `${String(hours)} 小时 ${String(minutes)} 分钟`
  if (minutes > 0) return `${String(minutes)} 分钟`
  return `${String(seconds)} 秒`
}

/** 到期提醒阈值 -> 中文档位名。 */
export function warningThresholdLabel(thresholdSeconds: number): string {
  if (thresholdSeconds >= 3 * 86400) return '3 天'
  if (thresholdSeconds >= 86400) return '1 天'
  if (thresholdSeconds >= 3600) return '1 小时'
  return `${String(Math.floor(thresholdSeconds / 60))} 分钟`
}

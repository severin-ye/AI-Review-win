import { useEffect, useState, type ReactNode } from 'react'
import { getLicenseApi, type LicenseSnapshot } from './types'
import { formatLocalDateTime, formatRemaining, warningThresholdLabel } from './format'

/**
 * 非阻断横幅（挂主界面顶部）：
 *   - 服务器暂不可达：提示当前许可证可用至何时（本地时区完整时间）
 *   - 即将到期：剩余 3 天 / 1 天 / 1 小时 档位提醒（每档主进程只推送一次）
 */
export default function LicenseBanner(): ReactNode {
  const isBrowser = getLicenseApi() === null
  const [snapshot, setSnapshot] = useState<LicenseSnapshot | null>(null)
  const [dismissedUnreachable, setDismissedUnreachable] = useState(false)

  useEffect(() => {
    const api = getLicenseApi()
    if (!api) return
    let cancelled = false
    void api.getState().then((s) => {
      if (!cancelled) setSnapshot(s)
    })
    const unsubscribe = api.onStateChanged((s) => {
      if (!cancelled) setSnapshot(s)
    })
    // 剩余时间本地每分钟刷新一次展示（不触发主进程）
    const timer = setInterval(() => {
      setSnapshot((prev) => {
        if (!prev || prev.remainingSeconds === null) return prev
        return { ...prev, remainingSeconds: prev.remainingSeconds - 60 }
      })
    }, 60_000)
    return () => {
      cancelled = true
      unsubscribe()
      clearInterval(timer)
    }
  }, [isBrowser])

  if (isBrowser || !snapshot) return null

  // 1. 服务器不可达（会话内可关闭）
  if (snapshot.state === 'SERVER_UNREACHABLE' && !dismissedUnreachable) {
    return (
      <div className="mb-4 flex items-start justify-between rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
        <span>
          暂时无法连接许可证服务器。当前许可证仍可使用至 {formatLocalDateTime(snapshot.expiresAt)}
          ，恢复连接后将自动重新验证。
        </span>
        <button
          type="button"
          onClick={() => setDismissedUnreachable(true)}
          className="ml-3 shrink-0 text-amber-500 hover:text-amber-700"
          aria-label="关闭提示"
        >
          ✕
        </button>
      </div>
    )
  }

  // 2. 即将到期提醒
  if (snapshot.expiryWarning && snapshot.usable) {
    const { thresholdSeconds, remainingSeconds } = snapshot.expiryWarning
    return (
      <div className="mb-4 rounded-md border border-orange-200 bg-orange-50 px-3 py-2 text-sm text-orange-800">
        许可证即将到期：剩余 {formatRemaining(remainingSeconds)}（{warningThresholdLabel(thresholdSeconds)}
        提醒）。到期时间 {formatLocalDateTime(snapshot.expiresAt)}，请及时联系管理员续期。
      </div>
    )
  }

  return null
}

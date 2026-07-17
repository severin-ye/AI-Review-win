import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { getLicenseApi, LICENSE_STATE_LABELS, type LicenseSnapshot } from './types'
import { formatLocalDateTime, formatRemaining } from './format'

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }): ReactNode {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="shrink-0 text-sm text-slate-500">{label}</span>
      <span className={`break-all text-right text-sm text-slate-800 ${mono ? 'font-mono text-xs' : ''}`}>{value}</span>
    </div>
  )
}

function serverStatusText(s: LicenseSnapshot): string {
  if (s.serverReachable === true) return '已连接'
  if (s.serverReachable === false) return '暂不可达'
  return '未检测'
}

/** 许可证状态卡片（嵌入设置页）。浏览器预览模式不渲染。 */
export default function LicenseStatusSection(): ReactNode {
  const isBrowser = getLicenseApi() === null
  const [snapshot, setSnapshot] = useState<LicenseSnapshot | null>(null)
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState<string | null>(null)

  const reload = useCallback(async (): Promise<void> => {
    const api = getLicenseApi()
    if (!api) return
    const s = await api.getStatus()
    setSnapshot(s)
  }, [])

  useEffect(() => {
    if (isBrowser) return
    void reload()
    const api = getLicenseApi()
    if (!api) return
    const unsubscribe = api.onStateChanged((s) => setSnapshot(s))
    return unsubscribe
  }, [isBrowser, reload])

  if (isBrowser) return null

  const handleRevalidate = async (): Promise<void> => {
    if (busy) return
    setBusy(true)
    setNote(null)
    const api = getLicenseApi()
    if (!api) return
    try {
      const result = await api.refresh()
      setNote(result.success ? '已重新验证，许可证状态正常。' : (result.message ?? '验证失败，请稍后重试。'))
    } catch {
      setNote('无法连接许可证服务器。')
    } finally {
      setBusy(false)
      await reload()
    }
  }

  const handleLogout = async (): Promise<void> => {
    if (busy) return
    if (!window.confirm('确定要退出当前许可证吗？退出后需要重新激活才能使用。')) return
    setBusy(true)
    const api = getLicenseApi()
    if (!api) return
    try {
      await api.logout()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">许可证</h2>
      {snapshot ? (
        <>
          <div className="divide-y divide-slate-100">
            <Row label="状态" value={LICENSE_STATE_LABELS[snapshot.state] ?? snapshot.state} />
            <Row label="许可证编号" value={snapshot.licenseId ?? '—'} mono />
            <Row label="绑定设备" value={snapshot.deviceId ?? '—'} mono />
            <Row label="激活时间" value={formatLocalDateTime(snapshot.issuedAt)} />
            <Row label="截止时间" value={formatLocalDateTime(snapshot.expiresAt)} />
            <Row label="剩余时间" value={formatRemaining(snapshot.remainingSeconds)} />
            <Row label="最近成功心跳" value={formatLocalDateTime(snapshot.lastHeartbeatAt)} />
            <Row label="服务器状态" value={serverStatusText(snapshot)} />
            <Row label="服务器地址" value={snapshot.serverUrl ?? '—'} />
          </div>
          {note && (
            <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {note}
            </div>
          )}
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => void handleRevalidate()}
              disabled={busy || !snapshot.licenseId}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? '处理中…' : '立即验证'}
            </button>
            <button
              type="button"
              onClick={() => void handleLogout()}
              disabled={busy || !snapshot.licenseId}
              className="rounded-md border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              退出许可证
            </button>
          </div>
        </>
      ) : (
        <p className="text-sm text-slate-400">正在读取许可证状态…</p>
      )}
    </div>
  )
}

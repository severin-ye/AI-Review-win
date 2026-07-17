import { useState, type ReactNode } from 'react'
import { getLicenseApi, type LicenseSnapshot } from './types'

function lockedText(snapshot: LicenseSnapshot): { title: string; body: string } {
  switch (snapshot.state) {
    case 'REVOKED':
      return {
        title: '许可证已被撤销',
        body: snapshot.message ?? '许可证已被管理员撤销，软件无法继续使用。请联系管理员重新获取授权。',
      }
    case 'SUSPENDED':
      return {
        title: '许可证已被暂停',
        body: snapshot.message ?? '许可证已被管理员暂停，软件暂时无法使用。请联系管理员恢复或稍后重试。',
      }
    case 'TIME_TAMPER_DETECTED':
      return {
        title: '系统时间异常',
        body: snapshot.message ?? '检测到系统时间异常回拨。请校准本机系统时间后重新启动应用。',
      }
    default:
      return { title: '许可证不可用', body: snapshot.message ?? '当前许可证不可用，请联系管理员。' }
  }
}

/** 锁定页：不可绕过（无关闭按钮可跳回主界面），仅提供 重新验证 / 返回激活页 / 安全退出。 */
export default function LicenseLockedPage({ snapshot }: { snapshot: LicenseSnapshot }): ReactNode {
  const [busy, setBusy] = useState<'refresh' | 'logout' | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const { title, body } = lockedText(snapshot)

  const handleRevalidate = async (): Promise<void> => {
    if (busy) return
    setBusy('refresh')
    setNote(null)
    const api = getLicenseApi()
    if (!api) return
    try {
      const result = await api.refresh()
      if (!result.success) {
        setNote(result.message ?? '重新验证失败，许可证状态未变化。')
      }
      // 成功时状态机推送新状态，LicenseGate 自动切换
    } catch {
      setNote('无法连接许可证服务器，请检查网络后重试。')
    } finally {
      setBusy(null)
    }
  }

  const handleBackToActivate = async (): Promise<void> => {
    if (busy) return
    setBusy('logout')
    const api = getLicenseApi()
    if (!api) return
    try {
      await api.logout()
      // 状态机推送 NO_LICENSE，LicenseGate 自动切到激活页
    } finally {
      setBusy(null)
    }
  }

  const handleQuit = (): void => {
    window.close()
  }

  return (
    <div className="flex h-screen items-center justify-center bg-slate-100 p-6">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-50 text-2xl text-red-500">
          ⛔
        </div>
        <h1 className="mb-2 text-xl font-semibold text-slate-800">{title}</h1>
        <p className="mb-6 text-sm leading-6 text-slate-500">{body}</p>
        {snapshot.licenseId && (
          <p className="mb-4 text-xs text-slate-400">许可证编号：{snapshot.licenseId}</p>
        )}
        {note && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
            {note}
          </div>
        )}
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => void handleRevalidate()}
            disabled={busy !== null}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy === 'refresh' ? '验证中…' : '重新验证'}
          </button>
          <button
            type="button"
            onClick={() => void handleBackToActivate()}
            disabled={busy !== null}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy === 'logout' ? '处理中…' : '返回激活页'}
          </button>
          <button
            type="button"
            onClick={handleQuit}
            className="rounded-md px-4 py-2 text-sm text-slate-400 hover:text-slate-600"
          >
            安全退出
          </button>
        </div>
      </div>
    </div>
  )
}

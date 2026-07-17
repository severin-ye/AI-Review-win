import { useEffect, useState, type ReactNode } from 'react'
import { getLicenseApi, type LicenseSnapshot } from './types'
import LicenseActivatePage from './LicenseActivatePage'
import LicenseLockedPage from './LicenseLockedPage'

function FullScreenLoading({ text }: { text: string }): ReactNode {
  return (
    <div className="flex h-screen items-center justify-center bg-slate-50">
      <div className="text-center">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
        <p className="text-sm text-slate-500">{text}</p>
      </div>
    </div>
  )
}

/**
 * 许可证总门：订阅主进程状态机，决定渲染 激活页 / 锁定页 / 加载页 / 主界面。
 * 浏览器预览模式（无 window.licenseApi）直接放行，便于纯前端调试。
 */
export default function LicenseGate({ children }: { children: ReactNode }): ReactNode {
  const licenseApi = getLicenseApi()
  const [snapshot, setSnapshot] = useState<LicenseSnapshot | null>(null)

  useEffect(() => {
    if (!licenseApi) return
    let cancelled = false
    void licenseApi.getState().then((s) => {
      if (!cancelled) setSnapshot(s)
    })
    const unsubscribe = licenseApi.onStateChanged((s) => {
      if (!cancelled) setSnapshot(s)
    })
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [licenseApi])

  if (!licenseApi) return children
  if (!snapshot) return <FullScreenLoading text="正在加载许可证状态…" />

  switch (snapshot.state) {
    case 'UNINITIALIZED':
    case 'VALIDATING_LOCAL':
      return <FullScreenLoading text="正在校验本地许可证…" />
    case 'CONNECTING_SERVER':
      return <FullScreenLoading text="正在连接许可证服务器…" />
    case 'NO_LICENSE':
    case 'INVALID_SIGNATURE':
    case 'DEVICE_MISMATCH':
    case 'LOCAL_EXPIRED':
      return <LicenseActivatePage snapshot={snapshot} />
    case 'SUSPENDED':
    case 'REVOKED':
    case 'TIME_TAMPER_DETECTED':
      return <LicenseLockedPage snapshot={snapshot} />
    default:
      // LOCAL_VALID / SERVER_ACTIVE / SERVER_UNREACHABLE：放行主界面
      return children
  }
}

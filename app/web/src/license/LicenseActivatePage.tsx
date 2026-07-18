import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { getLicenseApi, licenseErrorMessage, type LicenseSnapshot } from './types'
import { formatLocalDateTime } from './format'

type TestState =
  | { kind: 'idle' }
  | { kind: 'testing' }
  | { kind: 'ok'; serverTime: string | null; message: string }
  | { kind: 'fail'; message: string }

/** 许可证激活页：服务器地址（记忆保存）+ 许可证密钥 + 设备名 + 连接测试 + 激活。 */
export default function LicenseActivatePage({ snapshot }: { snapshot?: LicenseSnapshot }): ReactNode {
  const [serverUrl, setServerUrl] = useState('')
  const [licenseKey, setLicenseKey] = useState('')
  const [deviceName, setDeviceName] = useState('')
  const [testState, setTestState] = useState<TestState>({ kind: 'idle' })
  const [activating, setActivating] = useState(false)
  const [errorText, setErrorText] = useState<string | null>(null)

  // 激活失败兜底：doActivate 会先置 CONNECTING_SERVER（本页被全屏「正在连接」卸载），
  // 失败后状态机回退 NO_LICENSE 并携带 reasonCode/message，本页重新挂载时本地 errorText 已丢失，
  // 必须从 snapshot 恢复错误提示，否则用户看到"loading 一闪回到激活页、毫无反馈"。
  const stateErrorText =
    snapshot?.state === 'NO_LICENSE' && snapshot.reasonCode
      ? licenseErrorMessage(snapshot.reasonCode, snapshot.message)
      : null
  const displayError = errorText ?? stateErrorText

  // 进入页面时：带出上次服务器地址与设备名；状态带过来的错误（如凭证校验失败）展示在错误区
  useEffect(() => {
    const api = getLicenseApi()
    if (!api) return
    let cancelled = false
    void api.getStatus().then((s) => {
      if (cancelled) return
      if (s.serverUrl) setServerUrl(s.serverUrl)
      if (!deviceName) {
        // 设备名默认本机名（浏览器环境不可知， Electron 下用 navigator 兜底为空即可）
        setDeviceName('')
      }
      if (s.state === 'INVALID_SIGNATURE') {
        setErrorText('本地许可证凭证校验失败，请重新激活。如反复出现请联系管理员。')
      } else if (s.state === 'DEVICE_MISMATCH') {
        setErrorText('当前许可证凭证与本机设备不匹配，请重新激活。')
      } else if (s.state === 'LOCAL_EXPIRED') {
        setErrorText('许可证已到期且自动续期失败，请联系管理员续期后重新激活。')
      }
    })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleTest = async (): Promise<void> => {
    setTestState({ kind: 'testing' })
    setErrorText(null)
    try {
      const result = await getLicenseApi()!.testConnection(serverUrl)
      if (result.ok) {
        setTestState({ kind: 'ok', serverTime: result.serverTime ?? null, message: result.message ?? '连接成功' })
      } else {
        setTestState({ kind: 'fail', message: result.message ?? '连接失败' })
      }
    } catch {
      setTestState({ kind: 'fail', message: '无法连接许可证服务器' })
    }
  }

  const handleActivate = async (e: FormEvent): Promise<void> => {
    e.preventDefault()
    if (activating) return
    setActivating(true)
    setErrorText(null)
    try {
      const result = await getLicenseApi()!.activate({ serverUrl, licenseKey, deviceName })
      if (!result.success) {
        setErrorText(licenseErrorMessage(result.reasonCode, result.message))
      }
      // 成功时主进程状态机会推送 SERVER_ACTIVE，LicenseGate 自动切换到主界面
    } catch {
      setErrorText('激活请求失败，请稍后重试')
    } finally {
      setActivating(false)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="mb-1 text-xl font-semibold text-slate-800">激活许可证</h1>
        <p className="mb-6 text-sm text-slate-500">
          请输入管理员提供的许可证服务器地址与许可证密钥。激活需要连接局域网内的许可证服务器。
        </p>
        {snapshot?.state === 'LOCAL_EXPIRED' && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
            许可证已到期，请联系管理员续期后重新激活。
          </div>
        )}
        <form onSubmit={(e) => void handleActivate(e)} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">服务器地址</label>
            <input
              type="text"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              placeholder="http://192.168.1.100:8768"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">许可证密钥</label>
            <input
              type="text"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder="AIREV-XXXX-XXXX-XXXX"
              autoComplete="off"
              spellCheck={false}
              className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">设备名（选填）</label>
            <input
              type="text"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              placeholder="便于管理员识别的设备名称"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {testState.kind === 'ok' && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {testState.message}
              {testState.serverTime && (
                <span className="mt-0.5 block text-xs">服务器时间：{formatLocalDateTime(testState.serverTime)}</span>
              )}
            </div>
          )}
          {testState.kind === 'fail' && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              连接失败：{testState.message}
            </div>
          )}
          {displayError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{displayError}</div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => void handleTest()}
              disabled={testState.kind === 'testing' || !serverUrl.trim()}
              className="flex-1 rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {testState.kind === 'testing' ? '测试中…' : '连接测试'}
            </button>
            <button
              type="submit"
              disabled={activating || !serverUrl.trim() || !licenseKey.trim()}
              className="flex-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {activating ? '激活中…' : '激活'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

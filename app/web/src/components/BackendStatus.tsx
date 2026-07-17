import clsx from 'clsx'
import { useBackendHealth } from '@/api/health'

export default function BackendStatus() {
  const { data, isError, isLoading } = useBackendHealth()
  const ok = !isError && !!data

  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span
        className={clsx(
          'inline-block h-2 w-2 rounded-full',
          ok ? 'bg-emerald-500' : isLoading ? 'bg-amber-400' : 'bg-rose-500',
        )}
      />
      {ok ? `后端已连接 v${data.version}` : isLoading ? '后端连接中…' : '后端未连接'}
    </div>
  )
}

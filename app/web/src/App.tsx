import { lazy, Suspense } from 'react'
import clsx from 'clsx'
import BackendStatus from '@/components/BackendStatus'
import LicenseGate from '@/license/LicenseGate'
import LicenseBanner from '@/license/LicenseBanner'
import { Toaster } from '@/components/ui/sonner'
import { isBrowserPreview } from '@/api/client'
import { useHashPath } from '@/router'

const DocumentsPage = lazy(() => import('@/pages/DocumentsPage'))
const WorkbenchPage = lazy(() => import('@/pages/WorkbenchPage'))
const KnowledgeBasePage = lazy(() => import('@/pages/KnowledgeBasePage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))

const navItems = [
  { to: '/documents', label: '文档库' },
  { to: '/workbench', label: '审校工作台' },
  { to: '/kb', label: '医学知识库' },
  { to: '/settings', label: '设置' },
]

export default function App() {
  const path = useHashPath()
  const page = path === '/kb'
    ? <KnowledgeBasePage />
    : path === '/settings'
      ? <SettingsPage />
      : path === '/workbench' || path.startsWith('/workbench/')
        ? <WorkbenchPage />
        : <DocumentsPage />

  return (
    <LicenseGate>
      <div className="flex h-screen bg-slate-50 text-slate-800">
      <aside className="flex w-52 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="px-4 py-4 text-lg font-semibold">Caret</div>
        <nav className="flex-1 space-y-1 px-2">
          {navItems.map((item) => (
            <a
              key={item.to}
              href={`#${item.to}`}
              className={clsx(
                'block rounded-md px-3 py-2 text-sm',
                path === item.to || path.startsWith(`${item.to}/`)
                  ? 'bg-blue-50 font-medium text-blue-700'
                  : 'text-slate-600 hover:bg-slate-100',
              )}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="border-t border-slate-200 px-4 py-3">
          <BackendStatus />
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <LicenseBanner />
        {isBrowserPreview() && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            浏览器预览模式：后端连接 http://127.0.0.1:8765（npm run backend:dev）；
            「打开所在文件夹」等系统集成功能不可用，导出产物以下载链接代替。
          </div>
        )}
        <Suspense
          fallback={
            <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-sm text-slate-400">
              页面加载中…
            </div>
          }
        >
          {page}
        </Suspense>
      </main>
      <Toaster />
    </div>
    </LicenseGate>
  )
}

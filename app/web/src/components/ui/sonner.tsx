import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * sonner 风格 toast 最小手工版：全局 Toaster + 命令式 toast() / toast.success() / toast.error()。
 * 在应用根部挂一次 <Toaster />，任意处 import { toast } 调用。
 */
type ToastKind = 'default' | 'success' | 'error'

interface ToastItem {
  id: number
  kind: ToastKind
  message: string
}

type Listener = (toasts: ToastItem[]) => void

let nextId = 1
let toasts: ToastItem[] = []
const listeners = new Set<Listener>()

function notify() {
  for (const fn of listeners) fn(toasts)
}

function push(kind: ToastKind, message: string) {
  const item: ToastItem = { id: nextId++, kind, message }
  toasts = [...toasts, item]
  notify()
  window.setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== item.id)
    notify()
  }, 3200)
}

export const toast = Object.assign((message: string) => push('default', message), {
  success: (message: string) => push('success', message),
  error: (message: string) => push('error', message),
})

const kindClass: Record<ToastKind, string> = {
  default: 'border-slate-200 bg-white text-slate-700',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  error: 'border-red-200 bg-red-50 text-red-700',
}

export function Toaster() {
  const [items, setItems] = React.useState<ToastItem[]>(toasts)
  React.useEffect(() => {
    const fn: Listener = (t) => setItems([...t])
    listeners.add(fn)
    return () => {
      listeners.delete(fn)
    }
  }, [])
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-80 flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className={cn(
            'pointer-events-auto rounded-md border px-3 py-2 text-sm shadow-md',
            kindClass[t.kind],
          )}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}

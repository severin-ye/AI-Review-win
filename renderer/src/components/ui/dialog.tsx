import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * shadcn/ui dialog 最小手工版（无 radix）：受控 open + 遮罩点击/Escape 关闭。
 * 用法同 shadcn：<Dialog open onOpenChange><DialogContent><DialogHeader><DialogTitle/>…
 */
interface DialogProps {
  open: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
}

function Dialog({ open, onOpenChange, children }: DialogProps) {
  React.useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange?.(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onOpenChange])
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => {
        if (e.target === e.currentTarget) onOpenChange?.(false)
      }}
    >
      {children}
    </div>
  )
}

const DialogContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      role="dialog"
      aria-modal="true"
      className={cn(
        'w-full max-w-md rounded-lg border border-slate-200 bg-white p-5 shadow-lg',
        className,
      )}
      {...props}
    />
  ),
)
DialogContent.displayName = 'DialogContent'

function DialogHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mb-3 flex flex-col gap-1', className)} {...props} />
}

function DialogTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-base font-semibold', className)} {...props} />
}

function DialogDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn('text-sm text-slate-500', className)} {...props} />
}

function DialogFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('mt-4 flex justify-end gap-2', className)} {...props} />
}

export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter }

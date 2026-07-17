import * as React from 'react'
import { cn } from '@/lib/utils'

/** shadcn/ui badge 最小手工版。 */
const variants: Record<string, string> = {
  default: 'border-transparent bg-blue-600 text-white',
  secondary: 'border-transparent bg-slate-100 text-slate-700',
  destructive: 'border-transparent bg-red-600 text-white',
  outline: 'text-slate-700',
}

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof variants
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border border-slate-200 px-2 py-0.5 text-xs font-medium transition-colors',
        variants[variant] ?? variants.default,
        className,
      )}
      {...props}
    />
  )
}

export { Badge }

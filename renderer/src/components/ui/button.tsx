import * as React from 'react'
import { cn } from '@/lib/utils'

/**
 * shadcn/ui button 最小手工版（不用 CLI / radix；variant×size 映射表替代 cva）。
 */
const variants: Record<string, string> = {
  default: 'bg-blue-600 text-white shadow-sm hover:bg-blue-700',
  destructive: 'bg-red-600 text-white shadow-sm hover:bg-red-700',
  outline: 'border border-slate-200 bg-white shadow-sm hover:bg-slate-50 text-slate-700',
  secondary: 'bg-slate-100 text-slate-700 shadow-sm hover:bg-slate-200',
  ghost: 'hover:bg-slate-100 text-slate-700',
  link: 'text-blue-600 underline-offset-4 hover:underline',
}

const sizes: Record<string, string> = {
  default: 'h-9 px-4 py-2',
  sm: 'h-8 rounded-md px-3 text-xs',
  lg: 'h-10 rounded-md px-6',
  icon: 'h-9 w-9',
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants
  size?: keyof typeof sizes
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400',
        'disabled:pointer-events-none disabled:opacity-50',
        variants[variant] ?? variants.default,
        sizes[size] ?? sizes.default,
        className,
      )}
      {...props}
    />
  ),
)
Button.displayName = 'Button'

export { Button }

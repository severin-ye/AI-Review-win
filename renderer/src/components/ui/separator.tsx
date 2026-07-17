import * as React from 'react'
import { cn } from '@/lib/utils'

/** shadcn/ui separator 最小手工版（无 radix）。 */
const Separator = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { orientation?: 'horizontal' | 'vertical' }
>(({ className, orientation = 'horizontal', ...props }, ref) => (
  <div
    ref={ref}
    role="separator"
    className={cn(
      'shrink-0 bg-slate-200',
      orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
      className,
    )}
    {...props}
  />
))
Separator.displayName = 'Separator'

export { Separator }

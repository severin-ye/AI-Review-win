import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** shadcn/ui 约定的 className 合并工具：clsx 条件拼接 + tailwind-merge 冲突去重。 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

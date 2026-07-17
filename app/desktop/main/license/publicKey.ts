/**
 * 许可证验签公钥加载。
 *
 * 路径策略：
 *   - 打包后：electron-builder extraResources 将 app/desktop/resources/license-public.pem
 *     复制到 resources/license-public.pem → process.resourcesPath/license-public.pem
 *   - 开发期：仓库内 app/desktop/resources/license-public.pem
 *     （app.getAppPath() = 仓库根；__dirname = out/main，向上两级回到仓库根）
 * 客户端只含公钥。
 */
import fs from 'node:fs'
import path from 'node:path'

export interface PublicKeyPathHints {
  /** process.resourcesPath（打包后） */
  resourcesPath?: string
  /** app.getAppPath()（开发期 = 仓库根） */
  appPath?: string
  /** 主进程产物目录（out/main），用于向上推导仓库根 */
  mainOutDir?: string
  /** 显式覆盖（测试注入） */
  explicitPath?: string
}

/** 按优先级列出候选路径（纯函数，可测）。 */
export function publicKeyCandidates(hints: PublicKeyPathHints): string[] {
  const candidates: string[] = []
  if (hints.explicitPath) candidates.push(hints.explicitPath)
  if (hints.resourcesPath) candidates.push(path.join(hints.resourcesPath, 'license-public.pem'))
  if (hints.appPath) {
    candidates.push(path.join(hints.appPath, 'resources', 'license-public.pem'))
    candidates.push(path.join(hints.appPath, 'app', 'desktop', 'resources', 'license-public.pem'))
  }
  if (hints.mainOutDir) {
    candidates.push(path.resolve(hints.mainOutDir, '../../app/desktop/resources/license-public.pem'))
  }
  return candidates
}

/** 读取首个存在的候选路径的公钥 PEM；都找不到则抛错。 */
export function loadPublicKeyPem(hints: PublicKeyPathHints): string {
  const candidates = publicKeyCandidates(hints)
  for (const candidate of candidates) {
    try {
      if (fs.existsSync(candidate)) {
        const pem = fs.readFileSync(candidate, 'utf8')
        if (pem.includes('BEGIN PUBLIC KEY')) return pem
      }
    } catch {
      /* 尝试下一个 */
    }
  }
  throw new Error(`未找到许可证验签公钥 license-public.pem（已尝试：${candidates.join(', ')}）`)
}

/**
 * 本地凭证存储：Electron safeStorage（Windows DPAPI）加密保存 userData/license.dat。
 *
 * 降级策略（写明）：safeStorage 不可用时以 `PLAIN:` 前缀明文落盘并打印醒目警告——
 * 仅开发环境（如 Linux 无桌面密钥环）可接受；Windows 生产环境 DPAPI 应当可用，
 * 若生产环境命中该降级应视为部署异常。
 */
import fs from 'node:fs'
import path from 'node:path'
import type { SafeStorageLike } from './deviceId'
import type { StoredCredential } from './types'

const PLAIN_PREFIX = 'PLAIN:'

export class CredentialStorage {
  constructor(
    private readonly filePath: string,
    private readonly safeStorage?: SafeStorageLike,
    private readonly log: (msg: string) => void = console.warn,
  ) {}

  get path(): string {
    return this.filePath
  }

  load(): StoredCredential | null {
    if (!fs.existsSync(this.filePath)) return null
    let text: string
    const raw = fs.readFileSync(this.filePath)
    const asText = raw.toString('utf8')
    if (asText.startsWith(PLAIN_PREFIX)) {
      text = asText.slice(PLAIN_PREFIX.length)
    } else if (this.safeStorage?.isEncryptionAvailable()) {
      try {
        text = this.safeStorage.decryptString(raw)
      } catch {
        this.log('[license] license.dat 解密失败（可能跨机器拷贝），按无凭证处理')
        return null
      }
    } else {
      this.log('[license] safeStorage 不可用且文件无 PLAIN 标记，无法读取凭证')
      return null
    }
    try {
      const parsed = JSON.parse(text) as StoredCredential
      if (!parsed || typeof parsed !== 'object' || !parsed.token || !parsed.signature) return null
      return parsed
    } catch {
      this.log('[license] license.dat 内容损坏，按无凭证处理')
      return null
    }
  }

  save(credential: StoredCredential): void {
    const text = JSON.stringify(credential)
    const dir = path.dirname(this.filePath)
    fs.mkdirSync(dir, { recursive: true })
    const tmp = `${this.filePath}.tmp`
    if (this.safeStorage?.isEncryptionAvailable()) {
      fs.writeFileSync(tmp, this.safeStorage.encryptString(text))
    } else {
      this.log('[license] 警告：safeStorage 不可用，凭证以明文降级存储（仅开发环境可接受）')
      fs.writeFileSync(tmp, `${PLAIN_PREFIX}${text}`, 'utf8')
    }
    fs.renameSync(tmp, this.filePath)
  }

  clear(): void {
    try {
      fs.rmSync(this.filePath, { force: true })
    } catch {
      /* 忽略 */
    }
  }

  /** 隔离损坏/非法凭证（保留排查线索，不参与后续加载）。 */
  quarantine(reason: string): void {
    if (!fs.existsSync(this.filePath)) return
    const stamp = new Date().toISOString().replace(/[:.]/g, '-')
    const target = `${this.filePath}.quarantined-${reason}-${stamp}`
    try {
      fs.renameSync(this.filePath, target)
    } catch {
      this.clear()
    }
  }
}

/** 记住上次输入的服务器地址（非敏感，明文小文件）。 */
export class ClientConfigStore {
  constructor(private readonly filePath: string) {}

  loadServerUrl(): string | null {
    try {
      const parsed = JSON.parse(fs.readFileSync(this.filePath, 'utf8')) as { server_url?: unknown }
      return typeof parsed.server_url === 'string' && parsed.server_url ? parsed.server_url : null
    } catch {
      return null
    }
  }

  saveServerUrl(url: string): void {
    try {
      fs.mkdirSync(path.dirname(this.filePath), { recursive: true })
      fs.writeFileSync(this.filePath, JSON.stringify({ server_url: url }), 'utf8')
    } catch {
      /* 非关键路径，忽略 */
    }
  }
}

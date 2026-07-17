/**
 * 设备指纹：installation secret（首运行生成，存 userData）+ Windows MachineGuid + 固定命名空间
 * → SHA256 hex（64 字符）。原始 MachineGuid 不出本机、不发送。
 *
 * electron 相关能力（文件路径、safeStorage、注册表读取）通过依赖注入传入，核心计算为纯函数。
 */
import { createHash, randomBytes } from 'node:crypto'
import { execFile } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

export const DEVICE_ID_NAMESPACE = 'ai-review'

/** 纯函数：由命名空间 + MachineGuid + installation secret 计算 device_id。 */
export function computeDeviceId(namespace: string, machineGuid: string, installSecret: string): string {
  return createHash('sha256')
    .update(`${namespace}:${machineGuid}:${installSecret}`, 'utf8')
    .digest('hex')
}

export interface SafeStorageLike {
  isEncryptionAvailable: () => boolean
  encryptString: (plain: string) => Buffer
  decryptString: (encrypted: Buffer) => string
}

/** 读取 Windows MachineGuid（注册表 HKLM\SOFTWARE\Microsoft\Cryptography）；失败返回空串。 */
export async function readMachineGuid(
  execImpl: typeof execFileAsync = execFileAsync,
): Promise<string> {
  if (process.platform !== 'win32') return ''
  try {
    const { stdout } = await execImpl('reg', [
      'query',
      'HKLM\\SOFTWARE\\Microsoft\\Cryptography',
      '/v',
      'MachineGuid',
    ])
    const match = /MachineGuid\s+REG_SZ\s+(\S+)/.exec(stdout)
    return match?.[1]?.trim() ?? ''
  } catch {
    return ''
  }
}

/**
 * 读取或创建 installation secret（32 字节随机 hex）。
 * 优先用 safeStorage 加密存储；不可用时明文存储并打印醒目警告（仅开发环境可接受的降级策略，
 * Windows 生产环境 safeStorage 走 DPAPI，应当可用）。
 */
export function getOrCreateInstallSecret(
  userDataDir: string,
  safeStorage?: SafeStorageLike,
  log: (msg: string) => void = console.warn,
): string {
  const file = path.join(userDataDir, 'installation-secret.dat')
  if (fs.existsSync(file)) {
    const raw = fs.readFileSync(file)
    const text = raw.toString('utf8')
    if (text.startsWith('PLAIN:')) return text.slice('PLAIN:'.length).trim()
    if (safeStorage?.isEncryptionAvailable()) {
      try {
        return safeStorage.decryptString(raw)
      } catch {
        log('[license] installation-secret 解密失败，重新生成')
      }
    } else {
      // 无 safeStorage 且文件非 PLAIN 标记：按明文兼容读取
      const trimmed = text.trim()
      if (/^[0-9a-f]{64}$/.test(trimmed)) return trimmed
    }
  }
  const secret = randomBytes(32).toString('hex')
  if (safeStorage?.isEncryptionAvailable()) {
    fs.writeFileSync(file, safeStorage.encryptString(secret))
  } else {
    log('[license] 警告：safeStorage 不可用，installation secret 以明文降级存储（仅开发环境可接受）')
    fs.writeFileSync(file, `PLAIN:${secret}`, 'utf8')
  }
  return secret
}

/** 组合出本机 device_id（SHA256 hex）。 */
export async function getDeviceId(
  userDataDir: string,
  safeStorage?: SafeStorageLike,
  log: (msg: string) => void = console.warn,
): Promise<string> {
  const secret = getOrCreateInstallSecret(userDataDir, safeStorage, log)
  const guid = await readMachineGuid()
  return computeDeviceId(DEVICE_ID_NAMESPACE, guid, secret)
}

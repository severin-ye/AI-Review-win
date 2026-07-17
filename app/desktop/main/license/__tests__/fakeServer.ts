/**
 * 测试桩：内存版假许可证服务器 + 假存储 + 假时钟。
 * 用真实 Ed25519 密钥对按服务端协议签名响应，不依赖 electron / 网络 / 真实服务器。
 */
import { generateKeyPairSync, sign as cryptoSign } from 'node:crypto'
import { canonicalBytes } from '../canonical'
import type { FetchLike } from '../serverClient'
import type { LicenseToken, StoredCredential } from '../types'
import type { CredentialStorageLike } from '../licenseService'

export interface FakeKeyPair {
  publicKeyPem: string
  privateKey: ReturnType<typeof generateKeyPairSync>['privateKey']
}

export function makeKeyPair(): { publicKeyPem: string; privateKey: import('node:crypto').KeyObject } {
  const { publicKey, privateKey } = generateKeyPairSync('ed25519')
  return {
    publicKeyPem: publicKey.export({ format: 'pem', type: 'spki' }).toString(),
    privateKey,
  }
}

export function signObject(privateKey: import('node:crypto').KeyObject, obj: unknown): string {
  return cryptoSign(null, canonicalBytes(obj), privateKey).toString('base64')
}

/** 与服务端 sign_response 一致：对去掉 signature 的整体签名后附加。 */
export function signResponse(privateKey: import('node:crypto').KeyObject, body: Record<string, unknown>): Record<string, unknown> {
  const rest: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(body)) {
    if (k !== 'signature') rest[k] = v
  }
  return { ...rest, signature: signObject(privateKey, rest) }
}

export interface FakeLicense {
  id: string
  key: string
  status: 'active' | 'suspended' | 'revoked' | 'expired'
  expiresAt: string | null
  licenseVersion: number
  features: string[]
}

export class FakeLicenseServer {
  reachable = true
  activateCalls = 0
  heartbeatCalls = 0
  refreshCalls = 0
  boundDevices = new Set<string>()
  /** 心跳挂起控制（并发去重测试用） */
  heartbeatGate: Promise<void> | null = null

  constructor(
    readonly license: FakeLicense,
    readonly privateKey: import('node:crypto').KeyObject,
    readonly nowIso: () => string,
  ) {}

  issueToken(deviceId: string, overrides: Partial<LicenseToken> = {}): { token: LicenseToken; signature: string } {
    const token: LicenseToken = {
      schema_version: 1,
      license_id: this.license.id,
      device_id: deviceId,
      issued_at: this.nowIso(),
      expires_at: this.license.expiresAt,
      features: [...this.license.features],
      license_version: this.license.licenseVersion,
      ...overrides,
    }
    return { token, signature: signObject(this.privateKey, token) }
  }

  private errorBody(reasonCode: string, message: string): Record<string, unknown> {
    return { success: false, reason_code: reasonCode, message }
  }

  private json(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  /** FetchLike 实现；reachable=false 时模拟连接失败。 */
  fetch: FetchLike = async (url: string, init?: RequestInit): Promise<Response> => {
    if (!this.reachable) {
      // 模拟 TCP 层连接失败（与真实 fetch 的 TypeError 类似，serverClient 包装为 NetworkError）
      throw new TypeError('fetch failed')
    }
    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {}

    if (url.endsWith('/api/v1/ping')) {
      return this.json({ success: true, server_time: this.nowIso(), key_fingerprint: 'SHA256:fake', dev: true })
    }

    if (url.endsWith('/api/v1/licenses/activate')) {
      this.activateCalls += 1
      if (body['license_key'] !== this.license.key) {
        return this.json(this.errorBody('LICENSE_NOT_FOUND', '许可证密钥无效，请核对后重试'), 404)
      }
      if (this.license.status === 'revoked') return this.json(this.errorBody('LICENSE_REVOKED', '许可证已被管理员撤销'), 403)
      if (this.license.status === 'suspended') return this.json(this.errorBody('LICENSE_SUSPENDED', '许可证已被管理员暂停，请联系管理员'), 403)
      if (this.license.status === 'expired') return this.json(this.errorBody('LICENSE_EXPIRED', '许可证已到期，请联系管理员续期'), 403)
      const deviceId = String(body['device_id'])
      this.boundDevices.add(deviceId)
      const { token, signature } = this.issueToken(deviceId)
      return this.json({ success: true, license: token, signature })
    }

    if (url.endsWith('/api/v1/licenses/heartbeat')) {
      this.heartbeatCalls += 1
      if (this.heartbeatGate) await this.heartbeatGate
      const lic = this.license
      if (lic.status !== 'active') {
        const mapping = {
          revoked: ['LICENSE_REVOKED', '许可证已被管理员撤销'],
          suspended: ['LICENSE_SUSPENDED', '许可证已被管理员暂停'],
          expired: ['LICENSE_EXPIRED', '许可证已到期，请联系管理员续期'],
        } as const
        const [code, message] = mapping[lic.status]
        return this.json(
          signResponse(this.privateKey, { status: lic.status, reason_code: code, message, server_time: this.nowIso() }),
        )
      }
      const body2: Record<string, unknown> = {
        status: 'active',
        server_time: this.nowIso(),
        expires_at: lic.expiresAt,
        license_version: lic.licenseVersion,
        next_heartbeat_seconds: 300,
      }
      // 与真实服务端一致：license_version 比客户端上报的新 → 要求刷新（刷新后客户端版本追平，不再要求）
      const clientSent = typeof body['license_version'] === 'number' ? body['license_version'] : 0
      if (lic.licenseVersion > clientSent) body2['refresh_required'] = true
      return this.json(signResponse(this.privateKey, body2))
    }

    if (url.endsWith('/api/v1/licenses/refresh')) {
      this.refreshCalls += 1
      if (this.license.status === 'revoked') return this.json(this.errorBody('LICENSE_REVOKED', '许可证已被管理员撤销'), 403)
      if (this.license.status === 'suspended') return this.json(this.errorBody('LICENSE_SUSPENDED', '许可证已被管理员暂停，请联系管理员'), 403)
      if (this.license.status === 'expired') return this.json(this.errorBody('LICENSE_EXPIRED', '许可证已到期，请联系管理员续期'), 403)
      const deviceId = String(body['device_id'])
      const { token, signature } = this.issueToken(deviceId)
      return this.json({ success: true, license: token, signature })
    }

    return this.json({ success: false, reason_code: 'INTERNAL_SERVER_ERROR', message: '未知路径' }, 404)
  }
}

/** 内存凭证存储（记录 save/clear/quarantine 调用）。 */
export class MemoryStorage implements CredentialStorageLike {
  value: StoredCredential | null = null
  saveCount = 0
  cleared = false
  quarantined: string[] = []

  load(): StoredCredential | null {
    return this.value ? (structuredClone(this.value) as StoredCredential) : null
  }
  save(credential: StoredCredential): void {
    this.saveCount += 1
    this.value = structuredClone(credential) as StoredCredential
  }
  clear(): void {
    this.cleared = true
    this.value = null
  }
  quarantine(reason: string): void {
    this.quarantined.push(reason)
    this.value = null
  }
}

/** 假时钟。 */
export class FakeClock {
  constructor(public nowMs: number) {}
  now = (): number => this.nowMs
  iso = (): string => new Date(this.nowMs).toISOString()
  advance(seconds: number): void {
    this.nowMs += seconds * 1000
  }
}

export const SERVER_URL = 'http://fake-license-server:8768'

/** 构造一个已存好的本地凭证（绕过激活流程直接造局）。 */
export function makeStoredCredential(
  server: FakeLicenseServer,
  deviceId: string,
  overrides: Partial<LicenseToken> = {},
  storedOverrides: Partial<StoredCredential> = {},
): StoredCredential {
  const { token, signature } = server.issueToken(deviceId, overrides)
  return {
    token,
    signature,
    server_url: SERVER_URL,
    last_trusted_server_time: null,
    max_observed_time: null,
    last_warning_threshold_sent: null,
    revoked: false,
    ...storedOverrides,
  }
}

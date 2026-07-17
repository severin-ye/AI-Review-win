/**
 * 许可证状态机（单例）。electron / safeStorage / 文件系统全部通过依赖注入，
 * 状态迁移规则、离线规则表判定可在 vitest 中直接测。
 *
 * 启动流程（严格按序）：
 *   加载本地凭证 → 无 → NO_LICENSE
 *   → 验签失败 → INVALID_SIGNATURE（隔离凭证）
 *   → 设备绑定比对不符 → DEVICE_MISMATCH
 *   → 本地撤销标记 → REVOKED
 *   → 时间回拨 → TIME_TAMPER_DETECTED
 *   → 未过期 → LOCAL_VALID 放行 + 立即一次服务器检查，再进入心跳周期
 *   → 已过期 → 尝试 refresh，失败停留 LOCAL_EXPIRED（许可证页）
 *
 * 关键约束：
 *   - 连接失败 ≠ 撤销：网络错误只进 SERVER_UNREACHABLE，本地凭证有效即可用
 *   - 只信任验签通过的响应（revoked/suspended/expired/active 业务状态均为签名响应）
 *   - license_version 单调递增，旧响应不覆盖新状态
 *   - 心跳并发去重；激活接口幂等
 */
import { randomBytes } from 'node:crypto'
import { hostname } from 'node:os'
import {
  canonicalize,
  verifyCredential,
  verifySignedResponse,
} from './canonical'
import { loadLicenseConfig, type LicenseClientConfig } from './config'
import {
  NetworkError,
  ServerError,
  LicenseServerClient,
  normalizeServerUrl,
  type CredentialPayload,
  type FetchLike,
  type HeartbeatPayload,
} from './serverClient'
import {
  advanceMaxObserved,
  advanceTrustedTime,
  detectTimeRollback,
  dueExpiryWarning,
  isExpired,
  remainingSeconds,
} from './timeGuard'
import {
  errorMessageOf,
  type ActivateParams,
  type LicenseOpResult,
  type LicenseSnapshot,
  type LicenseState,
  type LicenseToken,
  type StoredCredential,
  type TestConnectionResult,
} from './types'

export interface CredentialStorageLike {
  load: () => StoredCredential | null
  save: (credential: StoredCredential) => void
  clear: () => void
  quarantine: (reason: string) => void
}

export interface LicenseServiceDeps {
  storage: CredentialStorageLike
  getDeviceId: () => Promise<string>
  getPublicKeyPem: () => string
  getClientVersion?: () => string
  /** 记住服务器地址（非敏感小配置） */
  saveServerUrl?: (url: string) => void
  loadServerUrl?: () => string | null
  fetchFn?: FetchLike
  clock?: () => number
  config?: LicenseClientConfig
  platform?: string
  osVersion?: string
  log?: (msg: string) => void
}

type Listener = (snapshot: LicenseSnapshot) => void

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

export class LicenseService {
  private state: LicenseState = 'UNINITIALIZED'
  private credential: StoredCredential | null = null
  private deviceId: string | null = null
  private reasonCode: string | null = null
  private message: string | null = null
  private lastHeartbeatAt: string | null = null
  private serverReachable: boolean | null = null
  private serverUrl: string | null = null
  private expiryWarning: { thresholdSeconds: number; remainingSeconds: number } | null = null

  private readonly listeners = new Set<Listener>()
  private heartbeatTimer: NodeJS.Timeout | null = null
  private heartbeatInFlight = false
  private activateInFlight: Promise<LicenseOpResult> | null = null
  private stopped = false

  private readonly config: LicenseClientConfig
  private readonly clock: () => number
  private readonly log: (msg: string) => void

  constructor(private readonly deps: LicenseServiceDeps) {
    this.config = deps.config ?? loadLicenseConfig()
    this.clock = deps.clock ?? (() => Date.now())
    this.log = deps.log ?? ((msg) => console.log(msg))
  }

  // ---------- 基础 ----------

  private nowIso(): string {
    return new Date(this.clock()).toISOString()
  }

  private setState(state: LicenseState, reasonCode: string | null = null, message: string | null = null): void {
    const changed = this.state !== state || this.reasonCode !== reasonCode || this.message !== message
    this.state = state
    this.reasonCode = reasonCode
    this.message = message
    if (changed) this.emit()
  }

  private emit(): void {
    const snapshot = this.getState()
    for (const listener of this.listeners) {
      try {
        listener(snapshot)
      } catch {
        /* 监听器异常不影响状态机 */
      }
    }
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  /** 可用状态集合：本地凭证验签通过且未过期（含服务器暂不可达）。 */
  private static readonly USABLE_STATES: ReadonlySet<LicenseState> = new Set([
    'LOCAL_VALID',
    'SERVER_ACTIVE',
    'SERVER_UNREACHABLE',
  ])

  private computeUsable(): boolean {
    if (!LicenseService.USABLE_STATES.has(this.state)) return false
    const cred = this.credential
    if (!cred || cred.revoked) return false
    return !isExpired(cred.token.expires_at, this.clock())
  }

  getState(): LicenseSnapshot {
    const cred = this.credential
    return {
      state: this.state,
      usable: this.computeUsable(),
      reasonCode: this.reasonCode,
      message: this.message,
      licenseId: cred?.token.license_id ?? null,
      deviceId: this.deviceId,
      features: cred?.token.features ?? [],
      licenseVersion: cred?.token.license_version ?? null,
      issuedAt: cred?.token.issued_at ?? null,
      expiresAt: cred?.token.expires_at ?? null,
      remainingSeconds: cred ? remainingSeconds(cred.token.expires_at, this.clock()) : null,
      lastHeartbeatAt: this.lastHeartbeatAt,
      lastServerTime: cred?.last_trusted_server_time ?? null,
      serverReachable: this.serverReachable,
      serverUrl: this.serverUrl ?? this.deps.loadServerUrl?.() ?? null,
      expiryWarning: this.expiryWarning,
    }
  }

  /** 每次实时查状态机（不是启动时检查一次）：核心功能前置门。 */
  canUseFeature(feature: string): boolean {
    if (!this.computeUsable()) return false
    const features = this.credential?.token.features ?? []
    return features.includes(feature)
  }

  // ---------- 启动流程 ----------

  async init(): Promise<LicenseSnapshot> {
    this.deviceId = await this.deps.getDeviceId()
    const cred = this.deps.storage.load()
    if (!cred) {
      this.credential = null
      this.setState('NO_LICENSE')
      return this.getState()
    }
    this.credential = cred
    this.serverUrl = cred.server_url
    this.setState('VALIDATING_LOCAL')

    // 1. 验签（签名对象 = token 本身）
    if (!this.verifyToken(cred.token, cred.signature)) {
      this.deps.storage.quarantine('invalid-signature')
      this.credential = null
      this.setState('INVALID_SIGNATURE', 'INVALID_LICENSE_SIGNATURE')
      return this.getState()
    }
    // 2. 设备绑定比对
    if (cred.token.device_id !== this.deviceId) {
      this.setState('DEVICE_MISMATCH', 'DEVICE_MISMATCH')
      return this.getState()
    }
    // 3. 本地撤销标记
    if (cred.revoked) {
      this.setState('REVOKED', 'LICENSE_REVOKED', errorMessageOf('LICENSE_REVOKED'))
      return this.getState()
    }
    // 4. 时间回拨检测（先检测后推进 max_observed_time）
    if (detectTimeRollback(cred, this.clock(), this.config.clockSkewToleranceSeconds)) {
      this.setState('TIME_TAMPER_DETECTED', null, '检测到系统时间异常回拨，请校准系统时间后重启应用')
      return this.getState()
    }
    this.touchMaxObserved(cred)

    // 5. 到期判定
    if (isExpired(cred.token.expires_at, this.clock())) {
      this.setState('LOCAL_EXPIRED', 'LICENSE_EXPIRED', errorMessageOf('LICENSE_EXPIRED'))
      const ok = await this.refresh()
      if (!ok) {
        // 停留许可证页（保持 LOCAL_EXPIRED）
        this.setState('LOCAL_EXPIRED', this.reasonCode ?? 'LICENSE_EXPIRED', this.message)
      }
      return this.getState()
    }

    // 6. 本地有效 → 放行 + 立即一次服务器检查再进入周期
    this.setState('LOCAL_VALID')
    this.checkExpiryWarning()
    this.startHeartbeat()
    return this.getState()
  }

  private verifyToken(token: LicenseToken, signature: string): boolean {
    try {
      return verifyCredential(this.deps.getPublicKeyPem(), token, signature)
    } catch (err) {
      this.log(`[license] 公钥加载失败: ${err instanceof Error ? err.message : String(err)}`)
      return false
    }
  }

  private touchMaxObserved(cred: StoredCredential): void {
    const next = advanceMaxObserved(cred, this.clock())
    if (next !== cred.max_observed_time) {
      cred.max_observed_time = next
      this.persist()
    }
  }

  private persist(): void {
    if (this.credential) this.deps.storage.save(this.credential)
  }

  private makeClient(): LicenseServerClient | null {
    if (!this.serverUrl) return null
    return new LicenseServerClient(this.serverUrl, this.config.requestTimeoutSeconds, this.deps.fetchFn)
  }

  // ---------- 激活 ----------

  /** 激活（幂等：进行中的重复调用复用同一 Promise）。 */
  activate(params: ActivateParams): Promise<LicenseOpResult> {
    if (this.activateInFlight) return this.activateInFlight
    this.activateInFlight = this.doActivate(params).finally(() => {
      this.activateInFlight = null
    })
    return this.activateInFlight
  }

  private async doActivate(params: ActivateParams): Promise<LicenseOpResult> {
    const serverUrl = normalizeServerUrl(params.serverUrl)
    if (!serverUrl) {
      return { success: false, reasonCode: null, message: '请填写许可证服务器地址' }
    }
    const licenseKey = params.licenseKey.trim().toUpperCase()
    if (!licenseKey) {
      return { success: false, reasonCode: null, message: '请填写许可证密钥' }
    }
    if (!this.deviceId) this.deviceId = await this.deps.getDeviceId()

    const hadLocal = this.credential !== null
    if (!hadLocal) this.setState('CONNECTING_SERVER')

    const client = new LicenseServerClient(serverUrl, this.config.requestTimeoutSeconds, this.deps.fetchFn)
    let payload: CredentialPayload
    try {
      payload = await client.activate({
        license_key: licenseKey,
        device_id: this.deviceId,
        device_name: params.deviceName?.trim() || hostname(),
        platform: this.deps.platform ?? process.platform,
        os_version: this.deps.osVersion ?? '',
        client_version: this.deps.getClientVersion?.() ?? '0.0.0',
        session_id: '',
        nonce: randomBytes(16).toString('hex'),
      })
    } catch (err) {
      return this.activationFailure(err, hadLocal)
    }

    // 验签 + 设备比对（只信任验签通过的凭证）
    const token = payload.license
    if (!token || typeof payload.signature !== 'string' || !this.verifyToken(token, payload.signature)) {
      if (!hadLocal) this.setState('INVALID_SIGNATURE', 'INVALID_LICENSE_SIGNATURE')
      return { success: false, reasonCode: 'INVALID_LICENSE_SIGNATURE', message: errorMessageOf('INVALID_LICENSE_SIGNATURE') }
    }
    if (token.device_id !== this.deviceId) {
      if (!hadLocal) this.setState('DEVICE_MISMATCH', 'DEVICE_MISMATCH')
      return { success: false, reasonCode: 'DEVICE_MISMATCH', message: errorMessageOf('DEVICE_MISMATCH') }
    }

    const now = this.nowIso()
    this.serverUrl = serverUrl
    this.deps.saveServerUrl?.(serverUrl)
    this.credential = {
      token,
      signature: payload.signature,
      server_url: serverUrl,
      last_trusted_server_time: token.issued_at,
      max_observed_time: now,
      last_warning_threshold_sent: null,
      revoked: false,
    }
    this.persist()
    this.serverReachable = true
    this.lastHeartbeatAt = now
    this.setState('SERVER_ACTIVE')
    this.checkExpiryWarning()
    this.startHeartbeat()
    return { success: true }
  }

  private activationFailure(err: unknown, hadLocal: boolean): LicenseOpResult {
    if (err instanceof ServerError) {
      if (!hadLocal) this.setState('NO_LICENSE', err.reasonCode, err.message)
      return { success: false, reasonCode: err.reasonCode, message: err.message }
    }
    if (err instanceof NetworkError) {
      if (!hadLocal) this.setState('NO_LICENSE', 'SERVER_UNREACHABLE', errorMessageOf('SERVER_UNREACHABLE'))
      return {
        success: false,
        reasonCode: err.kind === 'timeout' ? 'REQUEST_TIMEOUT' : 'SERVER_UNREACHABLE',
        message: errorMessageOf(err.kind === 'timeout' ? 'REQUEST_TIMEOUT' : 'SERVER_UNREACHABLE'),
      }
    }
    if (!hadLocal) this.setState('NO_LICENSE', 'INTERNAL_SERVER_ERROR', errorMessageOf('INTERNAL_SERVER_ERROR'))
    return { success: false, reasonCode: 'INTERNAL_SERVER_ERROR', message: errorMessageOf('INTERNAL_SERVER_ERROR') }
  }

  // ---------- 连接测试 ----------

  async testConnection(serverUrl: string): Promise<TestConnectionResult> {
    const url = normalizeServerUrl(serverUrl)
    if (!url) return { ok: false, message: '请填写许可证服务器地址' }
    const client = new LicenseServerClient(url, this.config.requestTimeoutSeconds, this.deps.fetchFn)
    try {
      const pong = await client.ping()
      return {
        ok: true,
        serverTime: pong.server_time ?? null,
        keyFingerprint: pong.key_fingerprint ?? null,
        message: pong.dev ? '连接成功（服务器为 DEV 密钥模式）' : '连接成功',
      }
    } catch (err) {
      if (err instanceof NetworkError) {
        return {
          ok: false,
          message: err.kind === 'timeout' ? errorMessageOf('REQUEST_TIMEOUT') : errorMessageOf('SERVER_UNREACHABLE'),
        }
      }
      if (err instanceof ServerError) return { ok: false, message: err.message }
      return { ok: false, message: errorMessageOf('SERVER_UNREACHABLE') }
    }
  }

  // ---------- 刷新凭证 ----------

  /** 刷新凭证（验签通过后覆盖旧凭证）。成功返回 true。 */
  async refresh(): Promise<boolean> {
    const cred = this.credential
    const client = this.makeClient()
    if (!cred || !client || !this.deviceId) return false
    let payload: CredentialPayload
    try {
      payload = await client.refresh({
        license_id: cred.token.license_id,
        device_id: this.deviceId,
        client_version: this.deps.getClientVersion?.() ?? '0.0.0',
      })
    } catch (err) {
      if (err instanceof ServerError) {
        // refresh 错误体未签名，不据此删除凭证；仅更新展示用 reason/message
        this.reasonCode = err.reasonCode
        this.message = err.message
        if (err.reasonCode === 'LICENSE_REVOKED' || err.reasonCode === 'DEVICE_REVOKED') {
          // 与心跳签名路径双保险：未签名不隔离，但保持锁定展示
          this.setState(this.state === 'LOCAL_EXPIRED' ? 'LOCAL_EXPIRED' : this.state, err.reasonCode, err.message)
        }
        this.emit()
      } else if (err instanceof NetworkError) {
        this.serverReachable = false
        this.emit()
      }
      return false
    }
    const token = payload.license
    if (!token || typeof payload.signature !== 'string' || !this.verifyToken(token, payload.signature)) {
      this.log('[license] refresh 响应验签失败，忽略')
      return false
    }
    if (token.device_id !== this.deviceId) return false
    // license_version 单调递增：拒绝回退
    if (token.license_version < cred.token.license_version) {
      this.log('[license] refresh 响应 license_version 回退，忽略')
      return false
    }
    this.credential = {
      ...cred,
      token,
      signature: payload.signature,
      last_trusted_server_time: advanceTrustedTime(cred, token.issued_at),
      last_warning_threshold_sent: null, // 新有效期，重置提醒
      revoked: false,
    }
    this.touchMaxObserved(this.credential)
    this.persist()
    this.serverReachable = true
    this.lastHeartbeatAt = this.nowIso()
    this.expiryWarning = null
    this.setState('SERVER_ACTIVE')
    this.checkExpiryWarning()
    // 刷新成功（如暂停被恢复）：确保心跳周期已重启
    this.startHeartbeat()
    return true
  }

  // ---------- 心跳 ----------

  startHeartbeat(): void {
    this.stopped = false
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    // 应用启动后立即先做一次服务器检查，再进入周期
    void this.heartbeatOnce()
  }

  stopHeartbeat(): void {
    this.stopped = true
    if (this.heartbeatTimer) {
      clearTimeout(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private scheduleNext(delaySeconds: number): void {
    if (this.stopped) return
    if (this.heartbeatTimer) clearTimeout(this.heartbeatTimer)
    this.heartbeatTimer = setTimeout(() => {
      void this.heartbeatOnce()
    }, Math.max(1, delaySeconds) * 1000)
  }

  /** 单次心跳（并发去重：上一次未结束不叠加）。 */
  async heartbeatOnce(): Promise<void> {
    if (this.heartbeatInFlight || this.stopped) return
    const cred = this.credential
    const client = this.makeClient()
    if (!cred || !client || !this.deviceId) return
    this.heartbeatInFlight = true
    try {
      const payload = await this.heartbeatWithRetry(client, cred)
      if (payload) this.handleHeartbeatPayload(payload, cred)
    } finally {
      this.heartbeatInFlight = false
    }
    // 安排下一跳（锁定类终态不再继续心跳，由 handleHeartbeatPayload 内 stopHeartbeat 处理）
    if (!this.stopped) this.scheduleNext(this.config.heartbeatIntervalSeconds)
  }

  /** 网络失败按 retry_delays 快速重试，之后等下周期（SERVER_UNREACHABLE，不锁定）。 */
  private async heartbeatWithRetry(
    client: LicenseServerClient,
    cred: StoredCredential,
  ): Promise<HeartbeatPayload | null> {
    const attempts = 1 + this.config.retryDelaysSeconds.length
    for (let i = 0; i < attempts; i += 1) {
      try {
        return await client.heartbeat({
          license_id: cred.token.license_id,
          device_id: this.deviceId ?? '',
          session_id: '',
          client_version: this.deps.getClientVersion?.() ?? '0.0.0',
          license_version: cred.token.license_version,
          timestamp: this.nowIso(),
          nonce: randomBytes(16).toString('hex'),
        })
      } catch (err) {
        if (err instanceof ServerError) {
          this.handleHeartbeatError(err)
          return null
        }
        // NetworkError：重试或进入 SERVER_UNREACHABLE
        if (i < attempts - 1) {
          await sleep(this.config.retryDelaysSeconds[i] * 1000)
          continue
        }
        this.serverReachable = false
        // 连接失败 ≠ 撤销：保持本地可用性，仅更新状态为非阻断提示
        if (this.computeUsable()) {
          this.setState('SERVER_UNREACHABLE', 'SERVER_UNREACHABLE', errorMessageOf('SERVER_UNREACHABLE'))
        } else {
          this.emit()
        }
        return null
      }
    }
    return null
  }

  /** 心跳 unsigned 错误体：不锁定、不删凭证，仅记录展示信息（权威否定走签名响应路径）。 */
  private handleHeartbeatError(err: ServerError): void {
    this.serverReachable = true
    this.reasonCode = err.reasonCode
    this.message = err.message
    this.log(`[license] 心跳业务错误: ${err.reasonCode}`)
    this.emit()
  }

  private handleHeartbeatPayload(payload: HeartbeatPayload, cred: StoredCredential): void {
    // 只信任验签通过的响应
    let verified = false
    try {
      verified = verifySignedResponse(this.deps.getPublicKeyPem(), payload)
    } catch {
      verified = false
    }
    if (!verified) {
      this.log('[license] 心跳响应验签失败，忽略（可能非目标服务器或响应被篡改）')
      return
    }
    // license_version 单调递增：旧响应不覆盖新状态
    const incomingVersion = typeof payload.license_version === 'number' ? payload.license_version : null
    if (payload.status === 'active' && incomingVersion !== null && incomingVersion < cred.token.license_version) {
      this.log('[license] 心跳响应 license_version 回退，忽略')
      return
    }

    this.serverReachable = true
    this.lastHeartbeatAt = this.nowIso()
    cred.last_trusted_server_time = advanceTrustedTime(cred, payload.server_time)
    // 运行时时间回拨检测
    if (detectTimeRollback(cred, this.clock(), this.config.clockSkewToleranceSeconds)) {
      this.persist()
      this.stopHeartbeat()
      this.setState('TIME_TAMPER_DETECTED', null, '检测到系统时间异常回拨，请校准系统时间后重启应用')
      return
    }
    this.touchMaxObserved(cred)

    switch (payload.status) {
      case 'active': {
        this.persist()
        this.setState('SERVER_ACTIVE')
        this.checkExpiryWarning()
        if (payload.refresh_required === true) {
          void this.refresh()
        }
        // 服务器建议的心跳间隔优先
        if (typeof payload.next_heartbeat_seconds === 'number' && payload.next_heartbeat_seconds > 0) {
          this.config.heartbeatIntervalSeconds = payload.next_heartbeat_seconds
        }
        break
      }
      case 'revoked': {
        // 验签通过的撤销：标记本地撤销（持久化 revoked 标记，凭证从此不可用=隔离）、锁定
        cred.revoked = true
        this.persist()
        this.stopHeartbeat()
        this.setState('REVOKED', 'LICENSE_REVOKED', payload.message ?? errorMessageOf('LICENSE_REVOKED'))
        break
      }
      case 'suspended': {
        // 锁定但保留凭证
        this.persist()
        this.stopHeartbeat()
        this.setState('SUSPENDED', 'LICENSE_SUSPENDED', payload.message ?? errorMessageOf('LICENSE_SUSPENDED'))
        break
      }
      case 'expired': {
        this.persist()
        this.setState('LOCAL_EXPIRED', 'LICENSE_EXPIRED', payload.message ?? errorMessageOf('LICENSE_EXPIRED'))
        void this.refresh().then((ok) => {
          if (!ok) this.setState('LOCAL_EXPIRED', this.reasonCode ?? 'LICENSE_EXPIRED', this.message)
        })
        break
      }
      default:
        break
    }
  }

  // ---------- 到期提醒 ----------

  /** 剩余 3 天 / 1 天 / 1 小时各提醒一次（阈值持久化在凭证存储里）。 */
  checkExpiryWarning(): void {
    const cred = this.credential
    if (!cred || !this.computeUsable()) return
    const due = dueExpiryWarning(
      cred.token.expires_at,
      this.clock(),
      this.config.expiryWarningThresholdsSeconds,
      cred.last_warning_threshold_sent,
    )
    if (due) {
      cred.last_warning_threshold_sent = due.thresholdSeconds
      this.persist()
      this.expiryWarning = due
      this.emit()
    } else if (this.expiryWarning) {
      // 更新剩余时间展示（不换档）
      const remaining = remainingSeconds(cred.token.expires_at, this.clock())
      if (remaining !== null) {
        this.expiryWarning = { thresholdSeconds: this.expiryWarning.thresholdSeconds, remainingSeconds: remaining }
      }
    }
  }

  // ---------- 登出 ----------

  /** 清除本地凭证，回到未激活状态。 */
  logout(): void {
    this.stopHeartbeat()
    this.deps.storage.clear()
    this.credential = null
    this.serverReachable = null
    this.lastHeartbeatAt = null
    this.expiryWarning = null
    this.setState('NO_LICENSE')
  }

  dispose(): void {
    this.stopHeartbeat()
    this.listeners.clear()
  }
}

// ---------- 供测试暴露的纯判定 ----------

/** 心跳业务状态是否为锁定类终态（验签通过后）。 */
export function isTerminalLockStatus(status: string): boolean {
  return status === 'revoked' || status === 'suspended'
}

export { canonicalize }

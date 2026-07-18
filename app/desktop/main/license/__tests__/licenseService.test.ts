/**
 * LicenseService 状态机 + 离线规则表（任务书 §五 表格逐行覆盖 + §十九 客户端部分）。
 * 全部用注入的假 fetch / 假 storage / 假时钟，不依赖 electron、不依赖真实服务器。
 */
import { describe, expect, it, afterEach } from 'vitest'
import { LicenseService } from '../licenseService'
import { loadLicenseConfig } from '../config'
import type { StoredCredential } from '../types'
import {
  FakeClock,
  FakeLicenseServer,
  MemoryStorage,
  SERVER_URL,
  makeKeyPair,
  makeStoredCredential,
} from './fakeServer'

const DEVICE_ID = 'a'.repeat(64)
const OTHER_DEVICE_ID = 'b'.repeat(64)
const T0 = Date.parse('2026-07-17T12:00:00Z')

const keyPair = makeKeyPair()

const flush = (ms = 30): Promise<void> => new Promise((r) => setTimeout(r, ms))

interface Harness {
  service: LicenseService
  server: FakeLicenseServer
  storage: MemoryStorage
  clock: FakeClock
}

const liveServices: LicenseService[] = []

function makeHarness(overrides?: {
  licenseStatus?: 'active' | 'suspended' | 'revoked' | 'expired'
  expiresAt?: string | null
  licenseVersion?: number
  licenseKey?: string
  stored?: StoredCredential | null
  deviceId?: string
}): Harness {
  const clock = new FakeClock(T0)
  const server = new FakeLicenseServer(
    {
      id: 'lic_test_0001',
      key: overrides?.licenseKey ?? 'AIREV-TEST-KEY1-KEY2',
      status: overrides?.licenseStatus ?? 'active',
      expiresAt: overrides?.expiresAt === undefined ? new Date(T0 + 30 * 86400 * 1000).toISOString() : overrides.expiresAt,
      licenseVersion: overrides?.licenseVersion ?? 1,
      features: ['main'],
    },
    keyPair.privateKey,
    () => clock.iso(),
  )
  const storage = new MemoryStorage()
  storage.value = overrides?.stored ?? null
  const service = new LicenseService({
    storage,
    getDeviceId: () => Promise.resolve(overrides?.deviceId ?? DEVICE_ID),
    getPublicKeyPem: () => keyPair.publicKeyPem,
    getClientVersion: () => '0.1.0',
    fetchFn: server.fetch,
    clock: clock.now,
    config: loadLicenseConfig({
      AI_REVIEW_LICENSE_HEARTBEAT_INTERVAL_SECONDS: '3600',
      AI_REVIEW_LICENSE_RETRY_DELAYS: '0',
    }),
    log: () => {},
  })
  liveServices.push(service)
  return { service, server, storage, clock }
}

afterEach(() => {
  while (liveServices.length > 0) liveServices.pop()?.dispose()
})

describe('启动流程', () => {
  it('无本地凭证 → NO_LICENSE', async () => {
    const { service } = makeHarness()
    const snap = await service.init()
    expect(snap.state).toBe('NO_LICENSE')
    expect(snap.usable).toBe(false)
  })

  it('规则表：签名无效 → 禁止（INVALID_SIGNATURE + 隔离凭证）', async () => {
    const server = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server, DEVICE_ID)
    stored.signature = Buffer.alloc(64).toString('base64') // 合法 base64 但内容错误
    const { service, storage } = makeHarness({ stored })
    const snap = await service.init()
    expect(snap.state).toBe('INVALID_SIGNATURE')
    expect(snap.usable).toBe(false)
    expect(storage.quarantined).toContain('invalid-signature')
  })

  it('规则表：设备不匹配 → 禁止（DEVICE_MISMATCH）', async () => {
    const server = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    // 凭证签名有效，但绑定的是另一台设备
    const stored = makeStoredCredential(server, OTHER_DEVICE_ID)
    const { service } = makeHarness({ stored })
    const snap = await service.init()
    expect(snap.state).toBe('DEVICE_MISMATCH')
    expect(snap.usable).toBe(false)
  })

  it('本地已标记撤销 → 直接 REVOKED', async () => {
    const server = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server, DEVICE_ID, {}, { revoked: true })
    const { service } = makeHarness({ stored })
    const snap = await service.init()
    expect(snap.state).toBe('REVOKED')
    expect(snap.usable).toBe(false)
  })

  it('系统时间回拨超容差 → TIME_TAMPER_DETECTED', async () => {
    const server = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server, DEVICE_ID, {}, {
      max_observed_time: new Date(T0 + 10_000 * 1000).toISOString(),
    })
    const { service } = makeHarness({ stored })
    const snap = await service.init()
    expect(snap.state).toBe('TIME_TAMPER_DETECTED')
    expect(snap.usable).toBe(false)
  })

  it('回拨在容差内 → 正常放行', async () => {
    const server = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server, DEVICE_ID, {}, {
      max_observed_time: new Date(T0 + 100 * 1000).toISOString(), // 仅早 100 秒
    })
    const { service } = makeHarness({ stored })
    const snap = await service.init()
    expect(['LOCAL_VALID', 'SERVER_ACTIVE']).toContain(snap.state)
  })
})

describe('离线规则表（任务书 §五）', () => {
  it('未过期+签名有效+服务器 active → 正常并更新本地状态', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID)
    const { service, server, storage } = makeHarness({ stored })
    const snap = await service.init()
    expect(['LOCAL_VALID', 'SERVER_ACTIVE']).toContain(snap.state)
    expect(snap.usable).toBe(true)
    await flush()
    expect(service.getState().state).toBe('SERVER_ACTIVE')
    expect(server.heartbeatCalls).toBeGreaterThanOrEqual(1)
    // 可信服务器时间已写入本地凭证
    expect(storage.value?.last_trusted_server_time).not.toBeNull()
    expect(service.canUseFeature('main')).toBe(true)
    expect(service.canUseFeature('nonexistent')).toBe(false)
  })

  it('未过期+服务器 revoked（签名通过）→ 立即锁定、凭证标记', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID)
    const { service, server, storage } = makeHarness({ stored })
    await service.init()
    await flush() // 等启动后的首次心跳完成，避免手动心跳被并发去重
    server.license.status = 'revoked'
    await service.heartbeatOnce()
    const snap = service.getState()
    expect(snap.state).toBe('REVOKED')
    expect(snap.usable).toBe(false)
    expect(service.canUseFeature('main')).toBe(false)
    expect(storage.value?.revoked).toBe(true)
  })

  it('未过期+服务器 suspended → 锁定但保留凭证', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID)
    const { service, server, storage } = makeHarness({ stored })
    await service.init()
    await flush()
    server.license.status = 'suspended'
    await service.heartbeatOnce()
    const snap = service.getState()
    expect(snap.state).toBe('SUSPENDED')
    expect(snap.usable).toBe(false)
    // 凭证保留（未清除、未隔离）
    expect(storage.value).not.toBeNull()
    expect(storage.cleared).toBe(false)
    expect(storage.quarantined).toHaveLength(0)
  })

  it('未过期+服务器不可达 → 继续使用（SERVER_UNREACHABLE 不锁定）', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID)
    const { service, server } = makeHarness({ stored })
    await service.init()
    await flush()
    server.reachable = false
    await service.heartbeatOnce()
    const snap = service.getState()
    expect(snap.state).toBe('SERVER_UNREACHABLE')
    expect(snap.usable).toBe(true)
    expect(service.canUseFeature('main')).toBe(true)
    expect(snap.serverReachable).toBe(false)
  })

  it('已过期+服务器续期成功 → 保存新凭证继续', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    // 本地凭证已过期（相对假时钟），服务器侧许可证仍有效
    const stored = makeStoredCredential(server0, DEVICE_ID, {
      expires_at: new Date(T0 - 1000).toISOString(),
    })
    const { service, server, storage } = makeHarness({ stored })
    const snap = await service.init()
    expect(server.refreshCalls).toBe(1)
    expect(snap.state).toBe('SERVER_ACTIVE')
    expect(snap.usable).toBe(true)
    // 新凭证已保存（过期时间被服务器的未来时间覆盖）
    expect(storage.value?.token.expires_at).not.toBe(stored.token.expires_at)
  })

  it('已过期+不可达 → 禁止（停留 LOCAL_EXPIRED）', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID, {
      expires_at: new Date(T0 - 1000).toISOString(),
    })
    const { service, server } = makeHarness({ stored })
    server.reachable = false
    const snap = await service.init()
    expect(snap.state).toBe('LOCAL_EXPIRED')
    expect(snap.usable).toBe(false)
    expect(service.canUseFeature('main')).toBe(false)
  })
})

describe('激活推送与失败状态（任务 1 回归：激活后必须可跳转/可见错误）', () => {
  it('激活成功：依次推送 CONNECTING_SERVER → SERVER_ACTIVE，凭证落盘', async () => {
    const { service, storage } = makeHarness()
    await service.init()
    const pushed: string[] = []
    service.subscribe((s) => pushed.push(s.state))
    const result = await service.activate({
      serverUrl: SERVER_URL,
      licenseKey: 'AIREV-TEST-KEY1-KEY2',
      deviceName: 'test',
    })
    expect(result.success).toBe(true)
    // LicenseGate 依赖这条推送序列从激活页切到主界面
    expect(pushed).toEqual(['CONNECTING_SERVER', 'SERVER_ACTIVE'])
    expect(service.getState().state).toBe('SERVER_ACTIVE')
    expect(storage.value).not.toBeNull()
  })

  it('激活失败（密钥无效）：回退 NO_LICENSE 且携带 reasonCode/message（激活页重挂后据此显示错误）', async () => {
    const { service } = makeHarness()
    await service.init()
    const result = await service.activate({
      serverUrl: SERVER_URL,
      licenseKey: 'AIREV-WRON-KEY0-0000',
      deviceName: 'test',
    })
    expect(result.success).toBe(false)
    expect(result.reasonCode).toBe('LICENSE_NOT_FOUND')
    const snap = service.getState()
    expect(snap.state).toBe('NO_LICENSE')
    expect(snap.reasonCode).toBe('LICENSE_NOT_FOUND')
    expect(snap.message).toBeTruthy()
  })

  it('激活失败（服务器不可达）：回退 NO_LICENSE 且携带 SERVER_UNREACHABLE', async () => {
    const { service, server } = makeHarness()
    await service.init()
    server.reachable = false
    const result = await service.activate({
      serverUrl: SERVER_URL,
      licenseKey: 'AIREV-TEST-KEY1-KEY2',
      deviceName: 'test',
    })
    expect(result.success).toBe(false)
    const snap = service.getState()
    expect(snap.state).toBe('NO_LICENSE')
    expect(snap.reasonCode).toBe('SERVER_UNREACHABLE')
    expect(snap.message).toBeTruthy()
  })
})

describe('license_version 单调性', () => {
  it('旧版本心跳响应不覆盖新状态（忽略）', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    // 本地凭证已经是 v2，服务器响应 v1 → 忽略
    const stored = makeStoredCredential(server0, DEVICE_ID, { license_version: 2 })
    const { service } = makeHarness({ stored })
    server0.license.licenseVersion = 1
    const snap = await service.init()
    expect(snap.state).toBe('LOCAL_VALID') // 心跳被忽略，未推进到 SERVER_ACTIVE
    await service.heartbeatOnce()
    expect(service.getState().state).toBe('LOCAL_VALID')
    expect(service.getState().lastServerTime).toBeNull()
  })

  it('refresh 响应版本回退 → 拒绝覆盖', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID, { license_version: 2 })
    const { service, server } = makeHarness({ stored })
    server.license.licenseVersion = 1
    await service.init()
    const ok = await service.refresh()
    expect(ok).toBe(false)
    expect(service.getState().licenseVersion).toBe(2)
  })

  it('refresh_required → 自动调 refresh 覆盖新凭证', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 2, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID, { license_version: 1 })
    const { service, server, storage } = makeHarness({ stored, licenseVersion: 2 })
    await service.init()
    await service.heartbeatOnce()
    await flush()
    expect(server.refreshCalls).toBeGreaterThanOrEqual(1)
    expect(storage.value?.token.license_version).toBe(2)
    expect(service.getState().state).toBe('SERVER_ACTIVE')
  })
})

describe('并发控制', () => {
  it('激活幂等：并发两次 activate 只发一次请求', async () => {
    const { service, server } = makeHarness()
    await service.init()
    const params = { serverUrl: SERVER_URL, licenseKey: 'AIREV-TEST-KEY1-KEY2', deviceName: 'test' }
    const p1 = service.activate(params)
    const p2 = service.activate(params)
    expect(p1).toBe(p2) // 复用进行中的同一 Promise
    const [r1, r2] = await Promise.all([p1, p2])
    expect(r1.success).toBe(true)
    expect(r2.success).toBe(true)
    expect(server.activateCalls).toBe(1)
  })

  it('心跳并发去重：上一次未结束不叠加', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID)
    const { service, server } = makeHarness({ stored })
    await service.init()
    await flush() // 等启动后的首次心跳完成
    const callsBefore = server.heartbeatCalls

    let release!: () => void
    server.heartbeatGate = new Promise<void>((resolve) => {
      release = resolve
    })
    const h1 = service.heartbeatOnce()
    await flush() // 确保第一次心跳已发出并在等待 gate
    const h2 = service.heartbeatOnce() // 应被去重，直接返回
    await h2
    expect(server.heartbeatCalls).toBe(callsBefore + 1)
    release()
    await h1
    server.heartbeatGate = null
  })
})

describe('登出', () => {
  it('logout 清除凭证并回到 NO_LICENSE', async () => {
    const server0 = new FakeLicenseServer(
      { id: 'lic_x', key: 'k', status: 'active', expiresAt: null, licenseVersion: 1, features: ['main'] },
      keyPair.privateKey,
      () => new Date(T0).toISOString(),
    )
    const stored = makeStoredCredential(server0, DEVICE_ID)
    const { service, storage } = makeHarness({ stored })
    await service.init()
    service.logout()
    expect(service.getState().state).toBe('NO_LICENSE')
    expect(storage.cleared).toBe(true)
    expect(service.canUseFeature('main')).toBe(false)
  })
})

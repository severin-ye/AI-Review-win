/**
 * 阶段 5/6 端到端集成冒烟脚本（依赖真实 license-server，不进 vitest 默认套件，可重复运行）。
 *
 * 运行方式（仓库根，Git Bash）：
 *   1. 启动许可证服务器：
 *        cd app/license-server && ../server/.venv/Scripts/python.exe run.py
 *      （另开终端；员工 API 在 8768，管理 API 在 127.0.0.1:8767；结束后记得杀掉）
 *   2. 打包并运行：
 *        node_modules/.bin/esbuild scripts/license-smoke.ts --bundle --platform=node \
 *          --format=esm --outfile=scripts/.license-smoke.bundle.mjs \
 *          --banner:js="import { createRequire } from 'module'; const require = createRequire(import.meta.url);"
 *        node scripts/.license-smoke.bundle.mjs
 *   3. 清理：杀掉 license-server 进程；删除 scripts/.license-smoke.bundle.mjs（已入 .gitignore）。
 *
 * 覆盖：对拍向量 / ping / 建证 / 错误 key / 激活+验签 / 冷启动放行 / 心跳验签+篡改负例 /
 *       重放与时间偏差 / 撤销链路（含冷启动 REVOKED）/ 断连不锁定。
 * 说明：每次运行使用唯一设备 ID（服务器按全局 device_id 校验归属），可安全重复执行；
 *       会在开发 .data 中留下已撤销的测试许可证（无害，管理页可见可删）。
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  canonicalize,
  verifyCredential,
  verifySignedResponse,
} from '../app/desktop/main/license/canonical'
import { LicenseService } from '../app/desktop/main/license/licenseService'
import { CredentialStorage } from '../app/desktop/main/license/storage'
import { computeDeviceId } from '../app/desktop/main/license/deviceId'
import { loadLicenseConfig } from '../app/desktop/main/license/config'
import { LicenseServerClient } from '../app/desktop/main/license/serverClient'

const __dirname2 = path.dirname(fileURLToPath(import.meta.url))
const REPO = path.resolve(__dirname2, '..')
const ADMIN = 'http://127.0.0.1:8767'
const EMPLOYEE = 'http://127.0.0.1:8768'
const PUBLIC_KEY_PEM = fs.readFileSync(
  path.join(REPO, 'app/desktop/resources/license-public.pem'),
  'utf8',
)
// 服务器按全局 device_id 校验归属（一个设备同时只能绑定一张许可证），
// 因此每次冒烟运行使用唯一设备 ID，避免与历史运行/同运行的第二张许可证冲突。
const RUN_ID = `${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`
const DEVICE_ID_A = computeDeviceId('ai-review', `SMOKE-A-${RUN_ID}`, 'a'.repeat(64))
const DEVICE_ID_B = computeDeviceId('ai-review', `SMOKE-B-${RUN_ID}`, 'b'.repeat(64))

let failures = 0
function check(name: string, cond: boolean, detail = ''): void {
  if (cond) {
    console.log(`  ✔ ${name}`)
  } else {
    failures += 1
    console.error(`  ✘ ${name} ${detail}`)
  }
}

/** 轮询等待条件满足（后台立即心跳与手动心跳存在并发去重，状态变化需要等待）。 */
async function waitFor(name: string, fn: () => boolean, timeoutMs = 8000): Promise<boolean> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (fn()) return true
    await new Promise((r) => setTimeout(r, 100))
  }
  check(name, false, `等待超时（${String(timeoutMs)}ms）`)
  return false
}

async function adminFetch(pathname: string, body?: unknown): Promise<any> {
  const res = await fetch(`${ADMIN}${pathname}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return res.json()
}

function makeService(storageDir: string, deviceId: string): LicenseService {
  const storage = new CredentialStorage(path.join(storageDir, 'license.dat'), undefined, () => {})
  const config = loadLicenseConfig({ AI_REVIEW_LICENSE_HEARTBEAT_INTERVAL_SECONDS: '3600' })
  return new LicenseService({
    storage,
    getDeviceId: () => Promise.resolve(deviceId),
    getPublicKeyPem: () => PUBLIC_KEY_PEM,
    getClientVersion: () => '0.1.0',
    config,
    log: () => {},
  })
}

async function main(): Promise<void> {
  // ---- 0. 对拍向量 ----
  console.log('== 0. 签名对拍向量 ==')
  const vectors = JSON.parse(
    fs.readFileSync(path.join(REPO, 'app/license-server/tests/vectors/license_vectors.json'), 'utf8'),
  ) as {
    public_key_pem: string
    cases: { name: string; token: unknown; canonical: string; signature: string; expect_verify: boolean }[]
  }
  for (const c of vectors.cases) {
    check(`canonical 一致 (${c.name})`, canonicalize(c.token) === c.canonical)
    check(
      `验签 expect=${String(c.expect_verify)} (${c.name})`,
      verifyCredential(vectors.public_key_pem, c.token, c.signature) === c.expect_verify,
    )
  }

  // ---- 1. ping ----
  console.log('== 1. ping 连通 ==')
  const probe = new LicenseServerClient(EMPLOYEE, 10)
  const pong = await probe.ping()
  check('ping success', pong.success === true, JSON.stringify(pong))
  console.log(`     server_time=${pong.server_time} fingerprint=${pong.key_fingerprint ?? ''} dev=${String(pong.dev)}`)

  // ---- 2. 创建许可证 ----
  console.log('== 2. 管理端创建许可证 ==')
  const created = await adminFetch('/api/v1/admin/licenses', {
    name: '冒烟测试',
    validity_mode: 'duration',
    duration_days: 30,
    max_devices: 2,
  })
  check('创建成功', created.success === true && typeof created.license_key === 'string')
  const licenseKey: string = created.license_key
  const licenseId: string = created.license.id
  console.log(`     license_id=${licenseId} key=${licenseKey.slice(0, 10)}-****-****`)

  // ---- 3. 错误 key 激活 ----
  console.log('== 3. 错误密钥激活被拒 ==')
  const dir1 = fs.mkdtempSync(path.join(REPO, '.smoke-'))
  const svc1 = makeService(dir1, DEVICE_ID_A)
  await svc1.init()
  check('初始 NO_LICENSE', svc1.getState().state === 'NO_LICENSE')
  const bad = await svc1.activate({ serverUrl: EMPLOYEE, licenseKey: 'AIREV-AAAA-AAAA-AAAA', deviceName: 'smoke' })
  check('激活失败 LICENSE_NOT_FOUND', !bad.success && bad.reasonCode === 'LICENSE_NOT_FOUND', JSON.stringify(bad))

  // ---- 4. 正确 key 激活 ----
  console.log('== 4. 正确密钥激活 ==')
  const ok = await svc1.activate({ serverUrl: EMPLOYEE, licenseKey, deviceName: 'smoke' })
  check('激活成功', ok.success === true, JSON.stringify(ok))
  const snap4 = svc1.getState()
  check('状态 SERVER_ACTIVE', snap4.state === 'SERVER_ACTIVE', snap4.state)
  check('usable=true', snap4.usable)
  check('canUseFeature(main)', svc1.canUseFeature('main'))
  check('凭证文件已写入', fs.existsSync(path.join(dir1, 'license.dat')))
  const stored = JSON.parse(
    fs.readFileSync(path.join(dir1, 'license.dat'), 'utf8').replace(/^PLAIN:/, ''),
  ) as { token: unknown; signature: string }
  check('落盘凭证验签通过', verifyCredential(PUBLIC_KEY_PEM, stored.token, stored.signature))

  // 幂等：重复激活复用进行中的调用（此处顺序调用也成功，设备已绑定走幂等路径）
  const again = await svc1.activate({ serverUrl: EMPLOYEE, licenseKey, deviceName: 'smoke' })
  check('重复激活幂等成功', again.success === true)
  svc1.dispose()

  // ---- 5. 冷启动：本地凭证放行 ----
  console.log('== 5. 冷启动 LOCAL_VALID 放行 ==')
  const svc2 = makeService(dir1, DEVICE_ID_A)
  const snap5 = await svc2.init()
  // init 返回时本地校验已完成（后台立即心跳可能已把它推进到 SERVER_ACTIVE）
  check(
    '启动后 LOCAL_VALID 或 SERVER_ACTIVE',
    ['LOCAL_VALID', 'SERVER_ACTIVE'].includes(snap5.state),
    snap5.state,
  )
  check('启动即可用', snap5.usable)
  await svc2.heartbeatOnce()
  await waitFor('心跳后 SERVER_ACTIVE', () => svc2.getState().state === 'SERVER_ACTIVE')
  svc2.dispose()

  // ---- 6. 真实心跳响应验签 / 篡改负例 ----
  console.log('== 6. 心跳响应验签 + 篡改负例 ==')
  const hb = await probe.heartbeat({
    license_id: licenseId,
    device_id: DEVICE_ID_A,
    session_id: '',
    client_version: '0.1.0',
    license_version: 1,
    timestamp: new Date().toISOString(),
    nonce: 'smoke-nonce-1',
  })
  check('心跳 active', hb.status === 'active', JSON.stringify(hb))
  check('真实心跳响应验签通过', verifySignedResponse(PUBLIC_KEY_PEM, hb))
  const tampered = { ...hb, expires_at: '2999-01-01T00:00:00Z' }
  check('篡改 expires_at 后验签失败', !verifySignedResponse(PUBLIC_KEY_PEM, tampered))
  const badSig = { ...hb, signature: hb.signature.slice(0, -4) + 'AAAA' }
  check('破坏签名串后验签失败', !verifySignedResponse(PUBLIC_KEY_PEM, badSig))

  // ---- 7. 协议负例：重放 / 时间偏差 ----
  console.log('== 7. 重放与时间偏差 ==')
  try {
    await probe.heartbeat({
      license_id: licenseId,
      device_id: DEVICE_ID_A,
      session_id: '',
      client_version: '0.1.0',
      license_version: 1,
      timestamp: new Date().toISOString(),
      nonce: 'smoke-nonce-1', // 与上一条相同
    })
    check('同 nonce 重放被拒', false, '服务器未拒绝')
  } catch (err) {
    check('同 nonce 重放 → REPLAY_DETECTED', (err as { reasonCode?: string }).reasonCode === 'REPLAY_DETECTED')
  }
  try {
    await probe.heartbeat({
      license_id: licenseId,
      device_id: DEVICE_ID_A,
      session_id: '',
      client_version: '0.1.0',
      license_version: 1,
      timestamp: new Date(Date.now() - 3600_000).toISOString(), // 偏差 1 小时
      nonce: 'smoke-nonce-2',
    })
    check('错位时间戳被拒', false, '服务器未拒绝')
  } catch (err) {
    check('错位时间戳 → SERVER_TIME_INVALID', (err as { reasonCode?: string }).reasonCode === 'SERVER_TIME_INVALID')
  }

  // ---- 8. 撤销 → 心跳锁定 ----
  console.log('== 8. 撤销链路 ==')
  const revoked = await adminFetch(`/api/v1/admin/licenses/${licenseId}/revoke`, { reason: '冒烟测试' })
  check('管理端撤销成功', revoked.success === true, JSON.stringify(revoked))
  const svc3 = makeService(dir1, DEVICE_ID_A)
  await svc3.init()
  await svc3.heartbeatOnce()
  await waitFor('撤销后状态 REVOKED', () => svc3.getState().state === 'REVOKED')
  const snap8 = svc3.getState()
  check('撤销后 usable=false', !snap8.usable)
  check('撤销后 canUseFeature=false', !svc3.canUseFeature('main'))
  const storedAfter = JSON.parse(
    fs.readFileSync(path.join(dir1, 'license.dat'), 'utf8').replace(/^PLAIN:/, ''),
  ) as { revoked?: boolean }
  check('本地凭证已标记 revoked', storedAfter.revoked === true)
  svc3.dispose()
  // 冷启动：revoked 标记生效
  const svc4 = makeService(dir1, DEVICE_ID_A)
  const snap8b = await svc4.init()
  check('冷启动直接 REVOKED', snap8b.state === 'REVOKED', snap8b.state)
  check('冷启动不可用', !snap8b.usable)
  svc4.dispose()

  // ---- 9. 服务器不可达 ≠ 撤销 ----
  console.log('== 9. 不可达行为 ==')
  const dir9 = fs.mkdtempSync(path.join(REPO, '.smoke-'))
  {
    // 先在正确服务器激活一个新许可证，再把服务指向错误端口模拟断连
    const created2 = await adminFetch('/api/v1/admin/licenses', { duration_days: 30, max_devices: 1 })
    const key2: string = created2.license_key
    const svc9 = makeService(dir9, DEVICE_ID_B)
    await svc9.init()
    const act = await svc9.activate({ serverUrl: EMPLOYEE, licenseKey: key2, deviceName: 'smoke' })
    check('第二张许可证激活成功', act.success === true)
    await waitFor('激活后 SERVER_ACTIVE', () => svc9.getState().state === 'SERVER_ACTIVE')
    // 指向不可达端口
    ;(svc9 as unknown as { serverUrl: string }).serverUrl = 'http://127.0.0.1:9'
    const cfg = loadLicenseConfig({ AI_REVIEW_LICENSE_RETRY_DELAYS: '0,0' })
    ;(svc9 as unknown as { config: typeof cfg }).config = cfg
    await svc9.heartbeatOnce()
    // 后台立即心跳可能仍在飞（并发去重会让手动调用空转），循环触发直到一次真实发出
    const deadline = Date.now() + 10_000
    while (svc9.getState().state !== 'SERVER_UNREACHABLE' && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 300))
      await svc9.heartbeatOnce()
    }
    check('断连后 SERVER_UNREACHABLE', svc9.getState().state === 'SERVER_UNREACHABLE', svc9.getState().state)
    const snap9 = svc9.getState()
    check('断连后仍可用（连接失败≠撤销）', snap9.usable)
    check('断连后 canUseFeature=true', svc9.canUseFeature('main'))
    svc9.dispose()
    await adminFetch(`/api/v1/admin/licenses/${created2.license.id}/revoke`, { reason: '冒烟清理' })
  }

  // 清理临时目录
  for (const d of [dir1, dir9]) {
    try {
      fs.rmSync(d, { recursive: true, force: true })
    } catch {
      /* ignore */
    }
  }

  console.log(failures === 0 ? '\n全部通过 ✅' : `\n${String(failures)} 项失败 ❌`)
  process.exit(failures === 0 ? 0 : 1)
}

main().catch((err) => {
  console.error('冒烟脚本异常:', err)
  process.exit(1)
})

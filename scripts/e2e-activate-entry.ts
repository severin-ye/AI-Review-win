/**
 * 端到端验证（任务 1 根因定位用）：
 *   真实 Electron 主进程（真实 LicenseService / registerLicenseIpc）
 *   + 真实 preload 构建产物（out/preload/index.js）
 *   + 真实 React 构建产物（out/renderer/index.html）
 *   + 本地假许可证服务器（127.0.0.1:18999，真实 Ed25519 签名，复用主进程 canonical）
 *
 * 验证链路：window.licenseApi.activate 成功
 *   → service 状态机 → IPC push license:stateChanged → preload → LicenseGate → 主界面。
 *
 * 不触碰 8767/8768 的真实 license-server，不触碰用户 userData（临时目录）。
 *
 * 运行：
 *   node_modules\.bin\esbuild scripts\e2e-activate-entry.ts --bundle --platform=node ^
 *     --format=cjs --external:electron --outfile=scripts\.e2e-main.cjs
 *   node_modules\.bin\electron scripts\.e2e-main.cjs
 */
import http from 'node:http'
import os from 'node:os'
import path from 'node:path'
import fs from 'node:fs'
import { generateKeyPairSync, sign as cryptoSign } from 'node:crypto'
import { app, BrowserWindow, ipcMain } from 'electron'
import { canonicalize } from '../app/desktop/main/license/canonical'
import { loadLicenseConfig } from '../app/desktop/main/license/config'
import { registerLicenseIpc } from '../app/desktop/main/license/ipc'
import { LicenseService } from '../app/desktop/main/license/licenseService'
import { CredentialStorage } from '../app/desktop/main/license/storage'

const FAKE_PORT = 18999
const LICENSE_KEY = 'AIREV-E2E-TEST-KEY1'
const DEVICE_ID = 'e'.repeat(64)

const { publicKey, privateKey } = generateKeyPairSync('ed25519')
const publicKeyPem = publicKey.export({ format: 'pem', type: 'spki' }).toString()

const nowIso = (): string => new Date().toISOString()
const signObj = (obj: unknown): string =>
  cryptoSign(null, Buffer.from(canonicalize(obj), 'utf8'), privateKey).toString('base64')
const signResp = (body: Record<string, unknown>): Record<string, unknown> => ({
  ...body,
  signature: signObj(body),
})

function makeToken(deviceId: string): Record<string, unknown> {
  return {
    schema_version: 1,
    license_id: 'lic_e2e_0001',
    device_id: deviceId,
    issued_at: nowIso(),
    expires_at: new Date(Date.now() + 30 * 86400_000).toISOString(),
    features: ['main'],
    license_version: 1,
  }
}

function startFakeServer(): http.Server {
  return http.createServer((req, res) => {
    let raw = ''
    req.on('data', (chunk: Buffer) => {
      raw += chunk.toString('utf8')
    })
    req.on('end', () => {
      const body: Record<string, unknown> = raw ? (JSON.parse(raw) as Record<string, unknown>) : {}
      const url = req.url ?? ''
      const json = (obj: unknown, status = 200): void => {
        res.writeHead(status, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify(obj))
      }
      if (url.endsWith('/api/v1/ping')) {
        json({ success: true, server_time: nowIso(), key_fingerprint: 'SHA256:e2e', dev: true })
        return
      }
      if (url.endsWith('/api/v1/licenses/activate')) {
        if (body['license_key'] !== LICENSE_KEY) {
          json({ success: false, reason_code: 'LICENSE_NOT_FOUND', message: '许可证密钥无效' }, 404)
          return
        }
        const token = makeToken(String(body['device_id']))
        json({ success: true, license: token, signature: signObj(token) })
        return
      }
      if (url.endsWith('/api/v1/licenses/heartbeat')) {
        json(
          signResp({
            status: 'active',
            server_time: nowIso(),
            expires_at: new Date(Date.now() + 30 * 86400_000).toISOString(),
            license_version: 1,
            next_heartbeat_seconds: 3600,
          }),
        )
        return
      }
      if (url.endsWith('/api/v1/licenses/refresh')) {
        const token = makeToken(String(body['device_id']))
        json({ success: true, license: token, signature: signObj(token) })
        return
      }
      json({ success: false, reason_code: 'NOT_FOUND', message: 'unknown path' }, 404)
    })
  })
}

const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms))

async function main(): Promise<void> {
  const server = startFakeServer()
  await new Promise<void>((resolve) => server.listen(FAKE_PORT, '127.0.0.1', resolve))

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-review-e2e-'))
  app.setPath('userData', tmp)
  await app.whenReady()

  const service = new LicenseService({
    storage: new CredentialStorage(path.join(tmp, 'license.dat'), undefined, (m) =>
      console.log('[storage]', m),
    ),
    getDeviceId: () => Promise.resolve(DEVICE_ID),
    getPublicKeyPem: () => publicKeyPem,
    getClientVersion: () => '0.1.0-e2e',
    config: loadLicenseConfig({
      AI_REVIEW_LICENSE_HEARTBEAT_INTERVAL_SECONDS: '3600',
      AI_REVIEW_LICENSE_RETRY_DELAYS: '0',
    }),
    log: (m) => console.log('[service]', m),
  })
  await service.init()

  let win: BrowserWindow | null = null
  registerLicenseIpc(service, () => win)
  // 渲染层业务组件需要的 dummy handler（本测试不关心后端连通）
  ipcMain.handle('backend:url', () => 'http://127.0.0.1:9')
  ipcMain.handle('app:version', () => '0.1.0-e2e')
  ipcMain.handle('shell:showItemInFolder', () => {})

  const repoRoot = path.resolve(__dirname, '..')
  win = new BrowserWindow({
    width: 1280,
    height: 800,
    show: false,
    webPreferences: {
      preload: path.join(repoRoot, 'out', 'preload', 'index.js'),
      contextIsolation: true,
    },
  })
  win.webContents.on('console-message', (_e, _level, message) =>
    console.log('[renderer]', message),
  )
  await win.loadFile(path.join(repoRoot, 'out', 'renderer', 'index.html'))

  const exec = (code: string): Promise<unknown> => win!.webContents.executeJavaScript(code, true)
  const waitFor = async (pred: () => Promise<boolean>, label: string, timeout = 20000): Promise<void> => {
    const t0 = Date.now()
    while (Date.now() - t0 < timeout) {
      if (await pred()) return
      await sleep(250)
    }
    throw new Error(`等待超时: ${label}`)
  }

  const result: Record<string, unknown> = {}
  try {
    await waitFor(
      async () => Boolean(await exec(`document.body.innerText.includes('激活许可证')`)),
      '激活页出现',
    )
    result.initialPage = 'activation-page-shown'
    await exec(
      `window.__events = []; window.licenseApi.onStateChanged((s) => { window.__events.push(s.state) }); 'subscribed'`,
    )

    // —— 场景 1：错误密钥激活 → 必须回到激活页且【显示错误提示】（任务 1 修复点）——
    result.failActivateResult = await exec(
      `window.licenseApi.activate({ serverUrl: 'http://127.0.0.1:${String(FAKE_PORT)}', licenseKey: 'AIREV-WRON-KEY0-0000', deviceName: 'e2e' })`,
    )
    await sleep(2000)
    const failText = String(await exec(`document.body.innerText`))
    result.failStillOnActivationPage = failText.includes('激活许可证')
    result.failErrorVisible = failText.includes('许可证密钥无效')
    result.failState = await exec(`window.licenseApi.getState().then((s) => s.state + '/' + String(s.reasonCode))`)

    // —— 场景 2：正确密钥激活 → 必须立即跳转主界面 ——
    result.activateResult = await exec(
      `window.licenseApi.activate({ serverUrl: 'http://127.0.0.1:${String(FAKE_PORT)}', licenseKey: '${LICENSE_KEY}', deviceName: 'e2e' })`,
    )
    await sleep(2500)
    result.events = await exec(`window.__events`)
    result.stateAfter = await exec(`window.licenseApi.getState().then((s) => s.state)`)
    const text = String(await exec(`document.body.innerText.slice(0, 500)`))
    result.showsActivationPage = text.includes('激活许可证')
    result.showsMainUi = text.includes('文档库')
    result.bodyExcerpt = text.slice(0, 200)
    result.credentialFileWritten = fs.existsSync(path.join(tmp, 'license.dat'))
  } catch (err) {
    result.error = err instanceof Error ? err.message : String(err)
  }
  console.log(`E2E_RESULT ${JSON.stringify(result, null, 2)}`)
  server.close()
  app.quit()
}

void main()

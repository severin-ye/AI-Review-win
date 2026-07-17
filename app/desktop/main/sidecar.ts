import { spawn, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import net from 'node:net'
import path from 'node:path'

export interface SidecarHandle {
  port: number
  url: string
  process: ChildProcess
}

export interface StartSidecarOptions {
  isDev: boolean
  appPath: string
  resourcesPath: string
  onLog?: (line: string) => void
}

const HEALTH_TIMEOUT_MS = 60_000
const HEALTH_INTERVAL_MS = 300

/** 让操作系统分配一个空闲端口，避免与既有服务冲突 */
export function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      const port = typeof address === 'object' && address !== null ? address.port : 0
      server.close(() => resolve(port))
    })
  })
}

function resolveBackendDir(isDev: boolean, resourcesPath: string, appPath: string): string {
  // dev：仓库根目录下的 app/server/；prod：打包后随 resources 分发的 backend/（M2 打包里程碑落地）
  return isDev ? path.join(appPath, 'app', 'server') : path.join(resourcesPath, 'backend')
}

/** 启动 Python FastAPI sidecar，返回进程句柄与 baseUrl。
 * dev：app/server/.venv（或系统 python）跑 uvicorn --reload；
 * prod：PyInstaller 单文件 ai-review-backend.exe（electron-builder extraResources → resources/backend/）。
 */
export async function startSidecar(options: StartSidecarOptions): Promise<SidecarHandle> {
  const { isDev, onLog } = options
  const backendDir = resolveBackendDir(isDev, options.resourcesPath, options.appPath)

  const port = await findFreePort()
  let command: string
  let args: string[]
  let cwd: string
  if (isDev) {
    // 优先使用后端独立 venv；dev 下 venv 不存在则回退系统 python
    const venvPython = path.join(backendDir, '.venv', 'Scripts', 'python.exe')
    command = fs.existsSync(venvPython) ? venvPython : 'python'
    args = ['-m', 'uvicorn', 'app.main:app', '--port', String(port), '--host', '127.0.0.1', '--reload']
    cwd = backendDir
  } else {
    command = path.join(backendDir, 'ai-review-backend.exe')
    args = ['--port', String(port)]
    cwd = path.dirname(command)
  }

  const child = spawn(command, args, {
    cwd,
    env: {
      ...process.env,
      AI_REVIEW_DEV: isDev ? '1' : '0',
      AI_REVIEW_PACKAGED: isDev ? '0' : '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  child.stdout?.on('data', (chunk: Buffer) => onLog?.(`[sidecar] ${chunk.toString().trimEnd()}`))
  child.stderr?.on('data', (chunk: Buffer) => onLog?.(`[sidecar:err] ${chunk.toString().trimEnd()}`))
  child.on('exit', (code) => onLog?.(`[sidecar] exited, code=${String(code)}`))

  return { port, url: `http://127.0.0.1:${port}`, process: child }
}

/** 轮询 /api/health 直到返回 200（超时抛错） */
export async function waitForHealthy(url: string, timeoutMs = HEALTH_TIMEOUT_MS): Promise<void> {
  const deadline = Date.now() + timeoutMs
  let lastError: unknown = null
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${url}/api/health`)
      if (response.ok) return
      lastError = new Error(`health status ${String(response.status)}`)
    } catch (error) {
      lastError = error
    }
    await new Promise((resolve) => setTimeout(resolve, HEALTH_INTERVAL_MS))
  }
  throw new Error(`sidecar health check timeout: ${String(lastError)}`)
}

/** 结束 sidecar 进程树（Windows 用 taskkill /T，确保 --reload 派生的子进程也被清理） */
export function stopSidecar(handle: SidecarHandle | null): void {
  const child = handle?.process
  if (!child || child.killed || child.exitCode !== null) return
  if (process.platform === 'win32') {
    try {
      spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' })
    } catch {
      // 进程可能已退出，忽略
    }
  } else {
    try {
      child.kill('SIGTERM')
    } catch {
      // 同上
    }
  }
}

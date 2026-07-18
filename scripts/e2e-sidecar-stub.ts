/**
 * e2e 专用 sidecar 桩（仅 scripts/build-e2e-shell.mjs 经 esbuild 插件替换 './sidecar' 时生效）。
 * 不启动 Python，只在本机随机端口应答 /api/health = 200，让真实 index.ts 的 bootstrap 走完。
 */
import http from 'node:http'
import type { ChildProcess } from 'node:child_process'

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

const servers = new Set<http.Server>()

export async function startSidecar(options: StartSidecarOptions): Promise<SidecarHandle> {
  const server = http.createServer((req, res) => {
    if ((req.url ?? '').startsWith('/api/health')) {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end('{"status":"ok"}')
      return
    }
    res.writeHead(404)
    res.end()
  })
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  servers.add(server)
  const address = server.address()
  const port = typeof address === 'object' && address !== null ? address.port : 0
  options.onLog?.(`[sidecar-stub] listening on ${String(port)}`)
  const fakeChild = { killed: false, exitCode: null, pid: 0 } as unknown as ChildProcess
  return { port, url: `http://127.0.0.1:${String(port)}`, process: fakeChild }
}

export async function waitForHealthy(_url: string, _timeoutMs?: number): Promise<void> {
  // 桩即刻就绪
}

export function stopSidecar(_handle: SidecarHandle | null): void {
  for (const server of servers) server.close()
  servers.clear()
}

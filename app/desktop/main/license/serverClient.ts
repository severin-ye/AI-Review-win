/**
 * 许可证服务器 HTTP 客户端（不依赖 electron；fetch/超时可注入，vitest 可测）。
 * 协议以 app/license-server 代码为准：
 *   POST /api/v1/licenses/activate | heartbeat | refresh；GET /api/v1/ping
 *   错误体：{"success": false, "reason_code": ..., "message": ...}
 */
import type { LicenseToken } from './types'

export type FetchLike = (url: string, init?: RequestInit) => Promise<Response>

/** 网络层错误（超时/不可达/非 JSON）——与业务错误（reason_code）区分：连接失败 ≠ 撤销 */
export class NetworkError extends Error {
  constructor(
    message: string,
    readonly kind: 'timeout' | 'unreachable' | 'bad_response',
  ) {
    super(message)
    this.name = 'NetworkError'
  }
}

/** 服务器返回的业务错误（unsigned error body） */
export class ServerError extends Error {
  constructor(
    readonly reasonCode: string,
    message: string,
    readonly httpStatus: number,
  ) {
    super(message)
    this.name = 'ServerError'
  }
}

export interface CredentialPayload {
  license: LicenseToken
  signature: string
  [k: string]: unknown
}

export interface HeartbeatPayload {
  status: 'active' | 'revoked' | 'suspended' | 'expired'
  server_time: string
  reason_code?: string
  message?: string
  expires_at?: string | null
  license_version?: number
  next_heartbeat_seconds?: number
  refresh_required?: boolean
  signature: string
  [k: string]: unknown
}

export interface PingPayload {
  success: boolean
  server_time: string
  key_fingerprint?: string
  dev?: boolean
  server_version?: string
}

export interface ActivateApiRequest {
  license_key: string
  device_id: string
  device_name: string
  platform: string
  os_version: string
  client_version: string
  session_id: string
  nonce: string
}

export interface HeartbeatApiRequest {
  license_id: string
  device_id: string
  session_id: string
  client_version: string
  license_version: number
  timestamp: string
  nonce: string
}

export interface RefreshApiRequest {
  license_id: string
  device_id: string
  client_version: string
}

/** 规范化服务器地址：去尾斜杠；无协议则补 http://。 */
export function normalizeServerUrl(raw: string): string {
  let url = raw.trim()
  if (url && !/^https?:\/\//i.test(url)) url = `http://${url}`
  return url.replace(/\/+$/, '')
}

export class LicenseServerClient {
  constructor(
    private readonly baseUrl: string,
    private readonly timeoutSeconds: number,
    private readonly fetchFn: FetchLike = fetch,
  ) {}

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), this.timeoutSeconds * 1000)
    let res: Response
    try {
      res = await this.fetchFn(`${this.baseUrl}${path}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      })
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        throw new NetworkError('请求超时', 'timeout')
      }
      throw new NetworkError('无法连接许可证服务器', 'unreachable')
    } finally {
      clearTimeout(timer)
    }
    let payload: unknown
    try {
      payload = await res.json()
    } catch {
      throw new NetworkError(`服务器响应无法解析（HTTP ${String(res.status)}）`, 'bad_response')
    }
    const obj = payload as Record<string, unknown>
    if (!res.ok || obj['success'] === false) {
      const reasonCode = typeof obj['reason_code'] === 'string' ? obj['reason_code'] : 'INTERNAL_SERVER_ERROR'
      const message = typeof obj['message'] === 'string' ? obj['message'] : `服务器错误（HTTP ${String(res.status)}）`
      throw new ServerError(reasonCode, message, res.status)
    }
    return payload as T
  }

  ping(): Promise<PingPayload> {
    return this.request<PingPayload>('GET', '/api/v1/ping')
  }

  activate(req: ActivateApiRequest): Promise<CredentialPayload> {
    return this.request<CredentialPayload>('POST', '/api/v1/licenses/activate', req)
  }

  heartbeat(req: HeartbeatApiRequest): Promise<HeartbeatPayload> {
    return this.request<HeartbeatPayload>('POST', '/api/v1/licenses/heartbeat', req)
  }

  refresh(req: RefreshApiRequest): Promise<CredentialPayload> {
    return this.request<CredentialPayload>('POST', '/api/v1/licenses/refresh', req)
  }
}

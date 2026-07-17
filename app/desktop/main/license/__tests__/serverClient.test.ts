/**
 * serverClient 协议客户端小测：URL 规整、错误分类（网络错误 ≠ 业务错误）、超时映射。
 */
import { describe, expect, it } from 'vitest'
import {
  LicenseServerClient,
  NetworkError,
  ServerError,
  normalizeServerUrl,
  type FetchLike,
} from '../serverClient'

describe('normalizeServerUrl', () => {
  it('去尾斜杠、补协议、去空白', () => {
    expect(normalizeServerUrl('  http://192.168.1.100:8768/ ')).toBe('http://192.168.1.100:8768')
    expect(normalizeServerUrl('192.168.1.100:8768')).toBe('http://192.168.1.100:8768')
    expect(normalizeServerUrl('https://lic.example.com/')).toBe('https://lic.example.com')
  })
})

describe('错误分类', () => {
  it('连接失败 → NetworkError(unreachable)，不是业务错误', async () => {
    const failFetch: FetchLike = () => Promise.reject(new TypeError('fetch failed'))
    const client = new LicenseServerClient('http://x', 5, failFetch)
    const err = await client.ping().catch((e: unknown) => e)
    expect(err).toBeInstanceOf(NetworkError)
    expect((err as NetworkError).kind).toBe('unreachable')
  })

  it('业务错误体 → ServerError(reason_code/message/httpStatus)', async () => {
    const errFetch: FetchLike = () =>
      Promise.resolve(
        new Response(
          JSON.stringify({ success: false, reason_code: 'LICENSE_NOT_FOUND', message: '许可证密钥无效，请核对后重试' }),
          { status: 404 },
        ),
      )
    const client = new LicenseServerClient('http://x', 5, errFetch)
    const err = await client
      .activate({
        license_key: 'k',
        device_id: 'd',
        device_name: '',
        platform: '',
        os_version: '',
        client_version: '0.1.0',
        session_id: '',
        nonce: 'n',
      })
      .catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ServerError)
    expect((err as ServerError).reasonCode).toBe('LICENSE_NOT_FOUND')
    expect((err as ServerError).httpStatus).toBe(404)
  })

  it('非 JSON 响应 → NetworkError(bad_response)', async () => {
    const badFetch: FetchLike = () => Promise.resolve(new Response('not json', { status: 200 }))
    const client = new LicenseServerClient('http://x', 5, badFetch)
    const err = await client.ping().catch((e: unknown) => e)
    expect(err).toBeInstanceOf(NetworkError)
    expect((err as NetworkError).kind).toBe('bad_response')
  })
})

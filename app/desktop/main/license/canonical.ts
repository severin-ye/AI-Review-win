/**
 * canonical JSON 序列化与 Ed25519 验签（纯函数，不依赖 electron，vitest 可直接对拍）。
 *
 * 与服务端 license_server/crypto.py 逐字节一致：
 *   json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
 * 即：键递归排序（按 Unicode 码位）、无空白、非 ASCII 原样输出、不转义 "/"。
 *
 * 签名对象规则：
 *   - 激活/刷新响应：signature 是对 "license"（token）对象 canonical bytes 的签名
 *   - 心跳响应：signature 是对整个响应体去掉 signature 字段后的 canonical bytes 的签名
 */
import { createPublicKey, verify as cryptoVerify, type KeyObject } from 'node:crypto'

/** 按 Unicode 码位比较两个字符串（与 Python sort_keys 的排序语义一致）。 */
function compareCodePoints(a: string, b: string): number {
  const ia = Array.from(a)
  const ib = Array.from(b)
  const len = Math.min(ia.length, ib.length)
  for (let i = 0; i < len; i += 1) {
    const ca = ia[i].codePointAt(0) ?? 0
    const cb = ib[i].codePointAt(0) ?? 0
    if (ca !== cb) return ca - cb
  }
  return ia.length - ib.length
}

/** 递归生成 canonical JSON 文本。 */
export function canonicalize(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'boolean' || typeof value === 'number') {
    // 协议内数值均为整数/布尔，JSON.stringify 与 Python json.dumps 输出一致
    return JSON.stringify(value)
  }
  if (typeof value === 'string') {
    // JSON.stringify 不转义 "/"，非 ASCII 原样输出（与 ensure_ascii=False 一致）
    return JSON.stringify(value)
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalize(item)).join(',')}]`
  }
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>
    const keys = Object.keys(obj)
      .filter((k) => obj[k] !== undefined)
      .sort(compareCodePoints)
    const body = keys.map((k) => `${JSON.stringify(k)}:${canonicalize(obj[k])}`).join(',')
    return `{${body}}`
  }
  throw new TypeError(`canonicalize: 不支持的类型 ${typeof value}`)
}

/** canonical JSON 的 UTF-8 字节。 */
export function canonicalBytes(value: unknown): Buffer {
  return Buffer.from(canonicalize(value), 'utf8')
}

let cachedKey: { pem: string; key: KeyObject } | null = null

function toKeyObject(publicKeyPem: string): KeyObject {
  if (cachedKey && cachedKey.pem === publicKeyPem) return cachedKey.key
  const key = createPublicKey(publicKeyPem)
  cachedKey = { pem: publicKeyPem, key }
  return key
}

/** Ed25519 验签：签名格式非法或验签失败均返回 false（不抛异常）。 */
export function verifyEd25519(
  publicKeyPem: string,
  payload: Uint8Array,
  signatureB64: string,
): boolean {
  try {
    const signature = Buffer.from(signatureB64, 'base64')
    if (signature.length !== 64) return false
    return cryptoVerify(null, Buffer.from(payload), toKeyObject(publicKeyPem), signature)
  } catch {
    return false
  }
}

/** 对对象 canonical bytes 验签。 */
export function verifySignedObject(
  publicKeyPem: string,
  obj: unknown,
  signatureB64: string,
): boolean {
  try {
    return verifyEd25519(publicKeyPem, canonicalBytes(obj), signatureB64)
  } catch {
    return false
  }
}

/** 验签激活/刷新响应中的凭证（签名对象 = token 本身）。 */
export function verifyCredential(
  publicKeyPem: string,
  token: unknown,
  signatureB64: string,
): boolean {
  return verifySignedObject(publicKeyPem, token, signatureB64)
}

/** 验签心跳类响应（签名对象 = 去掉 signature 字段后的整个响应体）。 */
export function verifySignedResponse(
  publicKeyPem: string,
  body: Record<string, unknown>,
): boolean {
  const signature = body['signature']
  if (typeof signature !== 'string') return false
  const rest: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(body)) {
    if (k !== 'signature') rest[k] = v
  }
  return verifySignedObject(publicKeyPem, rest, signature)
}

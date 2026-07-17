/**
 * canonical JSON 与 Ed25519 验签对拍（任务书 §十九：用服务端 vectors 对拍）。
 * 向量来源：app/license-server/tests/vectors/license_vectors.json（Python 端生成）。
 */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { canonicalBytes, canonicalize, verifyCredential, verifySignedResponse } from '../canonical'

interface VectorCase {
  name: string
  token: unknown
  canonical: string
  signature: string
  expect_verify: boolean
}

interface Vectors {
  public_key_pem: string
  cases: VectorCase[]
}

const vectors = JSON.parse(
  readFileSync(
    path.resolve(__dirname, '../../../../license-server/tests/vectors/license_vectors.json'),
    'utf8',
  ),
) as Vectors

describe('canonical JSON 与 Python 端逐字节一致', () => {
  for (const c of vectors.cases) {
    it(`${c.name}: canonical 字符串一致`, () => {
      expect(canonicalize(c.token)).toBe(c.canonical)
    })
    it(`${c.name}: canonical UTF-8 字节一致`, () => {
      expect(canonicalBytes(c.token).equals(Buffer.from(c.canonical, 'utf8'))).toBe(true)
    })
  }

  it('键递归排序 + 无空白', () => {
    expect(canonicalize({ b: 1, a: { d: 2, c: [3, { z: 1, y: 2 }] } })).toBe(
      '{"a":{"c":[3,{"y":2,"z":1}],"d":2},"b":1}',
    )
  })

  it('非 ASCII 原样输出（ensure_ascii=False 等价），不转义 /', () => {
    expect(canonicalize({ msg: '许可证已被管理员撤销', path: 'a/b' })).toBe(
      '{"msg":"许可证已被管理员撤销","path":"a/b"}',
    )
  })

  it('键排序按 Unicode 码位（与 Python sort_keys 一致）', () => {
    // 码位：'Z'=0x5A(90) < 'a'=0x61(97) < '中'=0x4E2D(20013)
    expect(canonicalize({ a: 1, Z: 2, 中: 3 })).toBe('{"Z":2,"a":1,"中":3}')
  })

  it('布尔/null/整数序列化', () => {
    expect(canonicalize({ t: true, f: false, n: null, i: 42 })).toBe('{"f":false,"i":42,"n":null,"t":true}')
  })
})

describe('Ed25519 验签（服务端对拍向量）', () => {
  it('valid_token 验签通过', () => {
    const c = vectors.cases.find((x) => x.name === 'valid_token')
    expect(c).toBeDefined()
    expect(verifyCredential(vectors.public_key_pem, c!.token, c!.signature)).toBe(true)
  })

  it.each(vectors.cases.filter((x) => !x.expect_verify).map((x) => [x.name, x] as const))(
    '%s 验签必须失败',
    (_name, c) => {
      expect(verifyCredential(vectors.public_key_pem, c.token, c.signature)).toBe(false)
    },
  )

  it('verifySignedResponse：签名对象为去掉 signature 的整个响应体', () => {
    const body = vectors.cases[0].token as Record<string, unknown>
    // 用向量公钥对应的私钥不可行，这里验证结构语义：错签名 → false；缺 signature → false
    expect(verifySignedResponse(vectors.public_key_pem, { ...body })).toBe(false)
    expect(verifySignedResponse(vectors.public_key_pem, { ...body, signature: '!!!!' })).toBe(false)
  })
})

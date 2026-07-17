/**
 * 错误码 → 中文文案一致性（任务书 §十九：renderer 文案与 schemas.py ERROR_MESSAGES 一致）。
 * 来源：直接正则提取 app/license-server/license_server/schemas.py 的 ErrorCode 枚举与
 * ERROR_MESSAGES 字典，与主进程、渲染层两份映射逐项对比（主进程与渲染层 tsconfig 独立，
 * 映射各存一份，必须保持同步）。
 */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { LICENSE_ERROR_MESSAGES as mainMessages } from '../types'
import { LICENSE_ERROR_MESSAGES as rendererMessages } from '../../../../../app/web/src/license/types'

const schemasPy = readFileSync(
  path.resolve(__dirname, '../../../../../app/license-server/license_server/schemas.py'),
  'utf8',
)

/** 从 schemas.py 提取 ErrorCode 枚举成员名。 */
function extractErrorCodes(): string[] {
  const enumBlock = /class ErrorCode\(str, Enum\):\n((?:\s+\w+ = "\w+"\n)+)/.exec(schemasPy)
  if (!enumBlock) throw new Error('schemas.py 中未找到 ErrorCode 枚举')
  return [...enumBlock[1].matchAll(/(\w+) = "\w+"/g)].map((m) => m[1])
}

/** 从 schemas.py 提取 ERROR_MESSAGES 字典（ErrorCode.X: "文案"）。 */
function extractErrorMessages(): Record<string, string> {
  const dictBlock = /ERROR_MESSAGES: dict\[ErrorCode, str\] = \{\n((?:\s+ErrorCode\.\w+: "[^"]*",\n)+)\}/.exec(
    schemasPy,
  )
  if (!dictBlock) throw new Error('schemas.py 中未找到 ERROR_MESSAGES 字典')
  const out: Record<string, string> = {}
  for (const m of dictBlock[1].matchAll(/ErrorCode\.(\w+): "([^"]*)",/g)) {
    out[m[1]] = m[2]
  }
  return out
}

describe('错误码映射与服务端 schemas.py 一致', () => {
  const serverMessages = extractErrorMessages()

  it('schemas.py 提取自检：枚举成员与文案一一对应', () => {
    const codes = extractErrorCodes()
    expect(codes.length).toBeGreaterThan(10)
    for (const code of codes) {
      expect(serverMessages[code], `schemas.py 缺少 ${code} 的文案`).toBeTruthy()
    }
  })

  it('主进程映射 = 服务端映射', () => {
    expect(mainMessages).toEqual(serverMessages)
  })

  it('渲染层映射 = 服务端映射', () => {
    expect(rendererMessages).toEqual(serverMessages)
  })
})

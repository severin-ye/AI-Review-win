/**
 * 字符级 diff（LCS DP），用于 correction 卡片「原句 vs 建议句」差异词高亮。
 * 中文按字比对正合适；输入为短片段（<数百字），O(n·m) DP 足够快。
 */
export interface DiffPart {
  text: string
  type: 'same' | 'del' | 'ins'
}

export function diffChars(a: string, b: string): DiffPart[] {
  const m = a.length
  const n = b.length
  if (m === 0 && n === 0) return []
  if (m === 0) return [{ text: b, type: 'ins' }]
  if (n === 0) return [{ text: a, type: 'del' }]

  // dp[i][j] = a[:i] 与 b[:j] 的 LCS 长度
  const dp: Uint32Array[] = []
  for (let i = 0; i <= m; i++) dp.push(new Uint32Array(n + 1))
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1])
    }
  }
  const parts: DiffPart[] = []
  const push = (text: string, type: DiffPart['type']) => {
    if (!text) return
    const last = parts[parts.length - 1]
    if (last && last.type === type) last.text += text
    else parts.push({ text, type })
  }
  let i = m
  let j = n
  const stack: DiffPart[] = []
  while (i > 0 && j > 0) {
    if (a[i - 1] === b[j - 1]) {
      stack.push({ text: a[i - 1], type: 'same' })
      i--
      j--
    } else if (dp[i - 1][j] >= dp[i][j - 1]) {
      stack.push({ text: a[i - 1], type: 'del' })
      i--
    } else {
      stack.push({ text: b[j - 1], type: 'ins' })
      j--
    }
  }
  while (i > 0) stack.push({ text: a[--i], type: 'del' })
  while (j > 0) stack.push({ text: b[--j], type: 'ins' })
  for (let k = stack.length - 1; k >= 0; k--) push(stack[k].text, stack[k].type)
  return parts
}

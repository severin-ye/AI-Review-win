import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { diffChars } from '@/lib/diff'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from '@/components/ui/sonner'
import type { BlockItem, EvidenceItem, SentenceItem } from '@/api/client'
import {
  filteredIds,
  useWorkbenchStore,
  type FlatCorrection,
  type WorkbenchFilters,
} from '@/stores/workbenchStore'

/* ---------- 视觉映射 ---------- */

const SEVERITY_META: Record<string, { label: string; highlight: string; badge: string }> = {
  high: {
    label: '高',
    highlight: 'bg-red-200/70 hover:bg-red-300/70 text-red-900',
    badge: 'bg-red-50 text-red-700 border-red-200',
  },
  medium: {
    label: '中',
    highlight: 'bg-orange-200/70 hover:bg-orange-300/70 text-orange-900',
    badge: 'bg-orange-50 text-orange-700 border-orange-200',
  },
  low: {
    label: '低',
    highlight: 'bg-yellow-200/70 hover:bg-yellow-300/70 text-yellow-900',
    badge: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  },
}

const ERROR_TYPE_BADGE: Record<string, string> = {
  事实错误: 'bg-red-50 text-red-700 border-red-200',
  术语错误: 'bg-violet-50 text-violet-700 border-violet-200',
  语法错误: 'bg-blue-50 text-blue-700 border-blue-200',
  格式错误: 'bg-slate-50 text-slate-600 border-slate-200',
}

const DECISION_META: Record<string, { label: string; className: string }> = {
  accepted: { label: '已采纳', className: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  rejected: { label: '已保留原文', className: 'bg-slate-100 text-slate-500 border-slate-200' },
  custom: { label: '已自定义', className: 'bg-teal-100 text-teal-700 border-teal-200' },
}

const SOURCE_META: Record<string, { label: string; className: string }> = {
  vector: { label: '向量', className: 'bg-blue-50 text-blue-600 border-blue-200' },
  keyword: { label: '关键词', className: 'bg-amber-50 text-amber-600 border-amber-200' },
}

function severityOf(sentence: SentenceItem): string | null {
  let best: string | null = null
  for (const c of sentence.corrections) {
    if (c.decision !== 'pending') continue
    if (c.severity === 'high') return 'high'
    if (c.severity === 'medium') best = 'medium'
    else if (c.severity === 'low' && best === null) best = 'low'
  }
  return best
}

/* ---------- 顶栏 ---------- */

function TopBar({ onRejectAll }: { onRejectAll: () => void }) {
  const navigate = useNavigate()
  const filename = useWorkbenchStore((s) => s.filename)
  const status = useWorkbenchStore((s) => s.status)
  const corrections = useWorkbenchStore((s) => s.corrections)
  const order = useWorkbenchStore((s) => s.order)
  const filters = useWorkbenchStore((s) => s.filters)
  const setFilter = useWorkbenchStore((s) => s.setFilter)
  const batch = useWorkbenchStore((s) => s.batch)

  const total = order.length
  const decided = order.filter((id) => corrections[id]?.decision !== 'pending').length
  const pct = total === 0 ? 100 : Math.round((decided / total) * 100)

  const selectClass =
    'h-8 rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-400'

  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5">
      <Button variant="ghost" size="sm" onClick={() => navigate('/documents')}>
        ← 返回
      </Button>
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold">{filename}</div>
        <div className="text-[10px] text-slate-400">{status === 'manual_done' ? '审校完成' : '人工审校中'}</div>
      </div>
      <Separator orientation="vertical" className="h-6" />
      {/* 决定进度 */}
      <div className="flex items-center gap-2">
        <div className="h-2 w-36 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs text-slate-500">
          {decided}/{total}
        </span>
      </div>
      <Separator orientation="vertical" className="h-6" />
      {/* 筛选器 */}
      <select
        className={selectClass}
        value={filters.decision}
        onChange={(e) => setFilter('decision', e.target.value as WorkbenchFilters['decision'])}
      >
        <option value="all">全部决定</option>
        <option value="pending">待决定</option>
        <option value="accepted">已采纳</option>
        <option value="rejected">已保留原文</option>
        <option value="custom">已自定义</option>
      </select>
      <select
        className={selectClass}
        value={filters.errorType}
        onChange={(e) => setFilter('errorType', e.target.value as WorkbenchFilters['errorType'])}
      >
        <option value="all">全部类型</option>
        <option value="事实错误">事实错误</option>
        <option value="术语错误">术语错误</option>
        <option value="语法错误">语法错误</option>
        <option value="格式错误">格式错误</option>
      </select>
      <select
        className={selectClass}
        value={filters.severity}
        onChange={(e) => setFilter('severity', e.target.value as WorkbenchFilters['severity'])}
      >
        <option value="all">全部严重度</option>
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
      {/* 批量操作 */}
      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => void batch({ severity: 'low' }, 'accept', '接受全部低风险')}
        >
          接受全部 low
        </Button>
        <Button variant="outline" size="sm" onClick={onRejectAll}>
          拒绝全部
        </Button>
      </div>
    </div>
  )
}

/* ---------- 左栏：文档原文 ---------- */

function DocumentPane() {
  const blocks = useWorkbenchStore((s) => s.blocks)
  const select = useWorkbenchStore((s) => s.select)
  const selectedId = useWorkbenchStore((s) => s.selectedId)
  const corrections = useWorkbenchStore((s) => s.corrections)

  const handleClick = (sentence: SentenceItem) => {
    const target =
      sentence.corrections.find((c) => c.decision === 'pending') ?? sentence.corrections[0]
    if (target) select(target.id)
  }

  return (
    <div className="h-full overflow-y-auto px-4 py-3">
      {blocks.map((block: BlockItem) => (
        <div key={block.id} className="mb-4">
          <div className="mb-1 flex items-center gap-2 text-xs text-slate-400">
            <span className="font-medium">
              #{block.idx + 1} {block.chapter ?? ''}
            </span>
            {block.is_reference && (
              <span className="rounded-full bg-purple-50 px-1.5 py-0.5 text-[10px] text-purple-500">
                参考文献
              </span>
            )}
          </div>
          <div className="space-y-1 text-sm leading-6 text-slate-700">
            {block.sentences.map((s) => {
              const sev = severityOf(s)
              const hasSelected = s.corrections.some((c) => c.id === selectedId)
              const clickable = s.corrections.length > 0
              return (
                <button
                  key={s.id}
                  type="button"
                  disabled={!clickable}
                  onClick={() => handleClick(s)}
                  className={cn(
                    'block w-full rounded px-1.5 py-0.5 text-left transition-colors',
                    sev ? SEVERITY_META[sev].highlight : clickable && 'hover:bg-slate-100',
                    !clickable && 'cursor-default',
                    hasSelected && 'ring-2 ring-blue-400',
                    s.corrections.length > 0 &&
                      s.corrections.every((c) => corrections[c.id]?.decision !== 'pending') &&
                      'opacity-60',
                  )}
                >
                  {s.text}
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

/* ---------- 中栏：correction 卡片 ---------- */

function DiffText({ parts, side }: { parts: ReturnType<typeof diffChars>; side: 'del' | 'ins' }) {
  return (
    <>
      {parts.map((p, i) => {
        if (p.type === 'same') return <span key={i}>{p.text}</span>
        if (p.type === side) {
          return (
            <mark
              key={i}
              className={cn(
                'rounded px-0.5',
                side === 'del' ? 'bg-red-200 text-red-800 line-through' : 'bg-emerald-200 text-emerald-800',
              )}
            >
              {p.text}
            </mark>
          )
        }
        return null
      })}
    </>
  )
}

/** 原句/建议句视图：original 片段能定位回句中则整句呈现并高亮差异词，否则仅片段 diff。 */
function SentenceDiff({ correction, view }: { correction: FlatCorrection; view: 'original' | 'suggestion' }) {
  const parts = useMemo(
    () => diffChars(correction.original, correction.suggestion),
    [correction.original, correction.suggestion],
  )
  const pos = correction.sentence_text.indexOf(correction.original)
  if (view === 'original') {
    if (pos < 0) return <DiffText parts={parts} side="del" />
    return (
      <>
        <span className="text-slate-400">{correction.sentence_text.slice(0, pos)}</span>
        <DiffText parts={parts} side="del" />
        <span className="text-slate-400">{correction.sentence_text.slice(pos + correction.original.length)}</span>
      </>
    )
  }
  if (pos < 0) return <DiffText parts={parts} side="ins" />
  return (
    <>
      <span className="text-slate-400">{correction.sentence_text.slice(0, pos)}</span>
      <DiffText parts={parts} side="ins" />
      <span className="text-slate-400">{correction.sentence_text.slice(pos + correction.original.length)}</span>
    </>
  )
}

function CorrectionCard({ correction }: { correction: FlatCorrection }) {
  const selectedId = useWorkbenchStore((s) => s.selectedId)
  const editingId = useWorkbenchStore((s) => s.editingId)
  const select = useWorkbenchStore((s) => s.select)
  const setEditing = useWorkbenchStore((s) => s.setEditing)
  const decide = useWorkbenchStore((s) => s.decide)
  const undo = useWorkbenchStore((s) => s.undo)
  const [customText, setCustomText] = useState(correction.suggestion)

  const pending = correction.decision === 'pending'
  const editing = editingId === correction.id
  const sev = SEVERITY_META[correction.severity] ?? SEVERITY_META.low

  const confirmCustom = () => {
    const text = customText.trim()
    if (!text) {
      toast.error('自定义文本不能为空')
      return
    }
    void decide(correction.id, 'custom', text)
  }

  return (
    <Card
      id={`correction-card-${correction.id}`}
      onClick={() => select(correction.id)}
      className={cn(
        'cursor-pointer transition-all',
        selectedId === correction.id && 'ring-2 ring-blue-400',
        // 决定后灰绿标记
        !pending && 'border-emerald-200 bg-emerald-50/50 opacity-75',
      )}
    >
      <CardContent className="space-y-2.5 p-3.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="outline" className={cn('text-[10px]', ERROR_TYPE_BADGE[correction.error_type])}>
            {correction.error_type}
          </Badge>
          <Badge variant="outline" className={cn('text-[10px]', sev.badge)}>
            {sev.label}危
          </Badge>
          <span className="text-[10px] text-slate-300">
            块 #{correction.block_idx + 1}
            {correction.chapter ? ` · ${correction.chapter}` : ''}
          </span>
          {!pending && (
            <Badge variant="outline" className={cn('ml-auto text-[10px]', DECISION_META[correction.decision].className)}>
              {DECISION_META[correction.decision].label}
            </Badge>
          )}
        </div>

        <div className="rounded-md bg-slate-50 px-2.5 py-1.5 text-sm leading-6">
          <span className="mr-1.5 text-[10px] font-medium text-slate-400">原句</span>
          <SentenceDiff correction={correction} view="original" />
        </div>
        <div className="rounded-md bg-emerald-50/60 px-2.5 py-1.5 text-sm leading-6">
          <span className="mr-1.5 text-[10px] font-medium text-slate-400">建议</span>
          {correction.decision === 'custom' && correction.custom_text ? (
            <span className="text-teal-800">{correction.custom_text}</span>
          ) : (
            <SentenceDiff correction={correction} view="suggestion" />
          )}
        </div>

        {correction.explanation && (
          <p className="text-xs leading-5 text-slate-500">{correction.explanation}</p>
        )}

        {editing ? (
          <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
            <textarea
              autoFocus
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  confirmCustom()
                }
                if (e.key === 'Escape') setEditing(null)
              }}
              rows={2}
              className="w-full rounded-md border border-blue-300 bg-white px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="输入自定义修订文本（Enter 确认，Shift+Enter 换行，Esc 取消）"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={confirmCustom}>
                确认自定义 (Enter)
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>
                取消
              </Button>
            </div>
          </div>
        ) : pending ? (
          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
            <Button size="sm" variant="outline" onClick={() => void decide(correction.id, 'rejected')}>
              保留原文 (1)
            </Button>
            <Button size="sm" onClick={() => void decide(correction.id, 'accepted')}>
              采纳 (2)
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                setCustomText(correction.suggestion)
                setEditing(correction.id)
              }}
            >
              自定义 (3)
            </Button>
          </div>
        ) : (
          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
            <Button size="sm" variant="ghost" onClick={() => void undo(correction.id)}>
              撤销
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CorrectionsPane() {
  const order = useWorkbenchStore((s) => s.order)
  const corrections = useWorkbenchStore((s) => s.corrections)
  const filters = useWorkbenchStore((s) => s.filters)
  const selectedId = useWorkbenchStore((s) => s.selectedId)
  const visible = filteredIds({ order, corrections, filters })

  useEffect(() => {
    if (selectedId === null) return
    document
      .getElementById(`correction-card-${selectedId}`)
      ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selectedId])

  if (visible.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
        {order.length === 0 ? '该文档暂无审校建议' : '当前筛选条件下无修改建议'}
      </div>
    )
  }
  return (
    <div className="h-full space-y-3 overflow-y-auto px-4 py-3">
      {visible.map((id) => (
        <CorrectionCard key={id} correction={corrections[id]} />
      ))}
    </div>
  )
}

/* ---------- 右栏：证据面板 ---------- */

function EvidencePane() {
  const selectedId = useWorkbenchStore((s) => s.selectedId)
  const corrections = useWorkbenchStore((s) => s.corrections)
  const blocks = useWorkbenchStore((s) => s.blocks)

  const correction = selectedId !== null ? corrections[selectedId] : null
  const sentence: SentenceItem | null = useMemo(() => {
    if (!correction) return null
    for (const block of blocks) {
      const found = block.sentences.find((s) => s.id === correction.sentence_id)
      if (found) return found
    }
    return null
  }, [blocks, correction])

  if (!correction || !sentence) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
        选中一张修改卡片后，此处显示该句的 3+3 检索证据
      </div>
    )
  }
  if (sentence.evidence.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
        该句无检索证据（未执行检索 / 检索已关闭 / 知识库无相关内容）
      </div>
    )
  }
  return (
    <div className="h-full space-y-2.5 overflow-y-auto px-4 py-3">
      <div className="text-xs text-slate-400">
        证据 {sentence.evidence.length} 条 · 蓝框为 AI 在解释中引用的证据
      </div>
      {sentence.evidence.map((e: EvidenceItem, idx: number) => {
        const meta = SOURCE_META[e.source] ?? SOURCE_META.keyword
        const referenced = correction.evidence_ids.includes(e.id)
        return (
          <div
            key={e.id}
            className={cn(
              'rounded-md border bg-white p-2.5 text-xs',
              referenced ? 'border-blue-400 ring-1 ring-blue-300' : 'border-slate-200',
            )}
          >
            <div className="mb-1 flex items-center gap-1.5">
              <span className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-500">
                E{idx + 1}
              </span>
              <span className={cn('rounded border px-1.5 py-0.5 text-[10px]', meta.className)}>
                {meta.label}
              </span>
              <span className="truncate font-medium text-slate-500">{e.doc_name}</span>
              {referenced && (
                <span className="ml-auto rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600">
                  AI 引用
                </span>
              )}
            </div>
            <div className="leading-5 text-slate-600">{e.chunk_text}</div>
          </div>
        )
      })}
    </div>
  )
}

/* ---------- 页面 ---------- */

export default function WorkbenchPage() {
  const { docId } = useParams<{ docId?: string }>()
  const navigate = useNavigate()
  const loading = useWorkbenchStore((s) => s.loading)
  const error = useWorkbenchStore((s) => s.error)
  const storeDocId = useWorkbenchStore((s) => s.docId)
  const load = useWorkbenchStore((s) => s.load)
  const reset = useWorkbenchStore((s) => s.reset)
  const [confirmRejectAll, setConfirmRejectAll] = useState(false)
  const batch = useWorkbenchStore((s) => s.batch)
  const order = useWorkbenchStore((s) => s.order)

  useEffect(() => {
    if (docId) void load(docId)
    return () => reset()
  }, [docId, load, reset])

  // 键盘快捷键：j/k/↑/↓ 切换卡片，1 保留原文 / 2 采纳 / 3 自定义
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const state = useWorkbenchStore.getState()
      if (state.editingId !== null) return // 自定义输入中：按键交给输入框
      const target = e.target as HTMLElement | null
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault()
        state.moveSelection(1)
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault()
        state.moveSelection(-1)
      } else if (['1', '2', '3'].includes(e.key) && state.selectedId !== null) {
        const c = state.corrections[state.selectedId]
        if (!c || c.decision !== 'pending') return
        e.preventDefault()
        if (e.key === '1') void state.decide(c.id, 'rejected')
        else if (e.key === '2') void state.decide(c.id, 'accepted')
        else state.setEditing(c.id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  if (!docId) {
    return (
      <section className="flex h-full flex-col items-center justify-center gap-3 text-slate-400">
        <p className="text-sm">请先从文档库选择一篇文档进入审校。</p>
        <Button variant="outline" size="sm" onClick={() => navigate('/documents')}>
          前往文档库
        </Button>
      </section>
    )
  }

  return (
    <section className="-m-6 flex h-screen flex-col">
      <TopBar onRejectAll={() => setConfirmRejectAll(true)} />
      {error && (
        <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>
      )}
      {loading || storeDocId !== docId ? (
        <div className="flex flex-1 items-center justify-center text-sm text-slate-400">加载中…</div>
      ) : (
        <div className="grid flex-1 grid-cols-12 overflow-hidden">
          <div className="col-span-4 overflow-hidden border-r border-slate-200 bg-white">
            <div className="border-b border-slate-100 px-4 py-2 text-xs font-medium text-slate-400">
              文档原文（高亮句可点击定位）
            </div>
            <div className="h-[calc(100%-2rem)]">
              <DocumentPane />
            </div>
          </div>
          <div className="col-span-5 overflow-hidden border-r border-slate-200 bg-slate-50/60">
            <div className="border-b border-slate-100 px-4 py-2 text-xs font-medium text-slate-400">
              修改建议（{order.length} 条）· 快捷键 j/k 切换 · 1 保留原文 · 2 采纳 · 3 自定义
            </div>
            <div className="h-[calc(100%-2rem)]">
              <CorrectionsPane />
            </div>
          </div>
          <div className="col-span-3 overflow-hidden bg-white">
            <div className="border-b border-slate-100 px-4 py-2 text-xs font-medium text-slate-400">
              证据面板
            </div>
            <div className="h-[calc(100%-2rem)]">
              <EvidencePane />
            </div>
          </div>
        </div>
      )}

      <Dialog open={confirmRejectAll} onOpenChange={setConfirmRejectAll}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>拒绝全部待决定建议？</DialogTitle>
            <DialogDescription>
              将把当前文档所有「待决定」的修改建议批量标记为保留原文（可逐条撤销）。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmRejectAll(false)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setConfirmRejectAll(false)
                void batch({}, 'reject', '拒绝全部')
              }}
            >
              确认拒绝全部
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}

import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import {
  deleteDocument,
  exportDocument,
  getDocumentDetail,
  getDocumentEvidence,
  getExportDownloadUrl,
  getParsed,
  isBrowserPreview,
  listDocuments,
  listExports,
  listKbDocuments,
  retrieveDocument,
  reviewDocument,
  runDocument,
  subscribeJobEvents,
  uploadDocument,
  type DocumentDetail,
  type DocumentEvidence,
  type DocumentItem,
  type EvidenceSentence,
  type ExportItem,
} from '@/api/client'

const STATUS_META: Record<string, { label: string; className: string }> = {
  uploaded: { label: '已上传', className: 'bg-slate-100 text-slate-600' },
  parsed: { label: '已解析', className: 'bg-blue-50 text-blue-700' },
  segmented: { label: '已分句', className: 'bg-green-50 text-green-700' },
  retrieving: { label: '检索中', className: 'bg-amber-50 text-amber-700' },
  retrieved: { label: '已检索', className: 'bg-indigo-50 text-indigo-700' },
  reviewing: { label: '审校中', className: 'bg-amber-50 text-amber-700' },
  pending_manual: { label: '待人工审校', className: 'bg-orange-50 text-orange-700' },
  manual_done: { label: '审校完成', className: 'bg-emerald-50 text-emerald-700' },
  done: { label: '已导出', className: 'bg-teal-50 text-teal-700' },
  failed: { label: '失败', className: 'bg-red-50 text-red-600' },
}

function StatusChip({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, className: 'bg-amber-50 text-amber-700' }
  return (
    <span className={clsx('inline-block rounded-full px-2 py-0.5 text-xs', meta.className)}>
      {meta.label}
    </span>
  )
}

/* ---------- 审校进度：进度圈 + 时间 ---------- */

/** 环形进度：total 未知时退化为旋转圈（indeterminate）。 */
function ProgressRing({ done, total }: { done: number; total: number | null }) {
  if (total === null || total === 0) {
    return (
      <span className="inline-block h-10 w-10 animate-spin rounded-full border-[3px] border-emerald-500 border-t-transparent" />
    )
  }
  const size = 40
  const stroke = 3.5
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Math.min(1, done / total)
  return (
    <div className="relative h-10 w-10 shrink-0">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#a7f3d0" strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="#10b981"
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className="transition-all duration-500"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-semibold text-emerald-700">
        {Math.round(pct * 100)}%
      </span>
    </div>
  )
}

function formatClock(ms: number): string {
  const d = new Date(ms)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function formatElapsed(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
}

const SOURCE_META: Record<string, { label: string; className: string }> = {
  vector: { label: '向量', className: 'bg-blue-50 text-blue-600 border-blue-200' },
  keyword: { label: '关键词', className: 'bg-amber-50 text-amber-600 border-amber-200' },
}

function SentenceEvidence({ sentence }: { sentence: EvidenceSentence }) {
  return (
    <div className="mt-2 space-y-2 rounded-md border border-slate-100 bg-slate-50/60 p-3">
      {sentence.queries.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">
            重写问题（{sentence.queries.length}）
          </div>
          <ol className="space-y-0.5">
            {sentence.queries.map((q) => (
              <li key={q.id} className="text-xs leading-5 text-slate-500">
                <span className="mr-1.5 text-slate-300">Q{q.idx + 1}</span>
                {q.text}
                {q.idx === 0 && (
                  <span className="ml-1.5 rounded bg-slate-200/70 px-1 py-0.5 text-[10px] text-slate-400">
                    原句
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>
      )}
      {sentence.evidence.length > 0 ? (
        <div>
          <div className="mb-1 text-xs font-medium text-slate-500">
            证据（{sentence.evidence.length} 条，3+3 混合检索）
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {sentence.evidence.map((e) => {
              const meta = SOURCE_META[e.source] ?? SOURCE_META.keyword
              return (
                <div
                  key={e.id}
                  className="rounded-md border border-slate-200 bg-white p-2.5 text-xs"
                >
                  <div className="mb-1 flex items-center gap-1.5">
                    <span className={clsx('rounded border px-1.5 py-0.5 text-[10px]', meta.className)}>
                      {meta.label}
                    </span>
                    <span className="font-medium text-slate-500">{e.doc_name}</span>
                    <span className="ml-auto text-[10px] text-slate-300">
                      #{e.rank} · {e.score.toFixed(4)}
                    </span>
                  </div>
                  <div className="leading-5 text-slate-600">
                    {e.chunk_text.length > 160 ? `${e.chunk_text.slice(0, 160)}…` : e.chunk_text}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="text-xs text-slate-400">无证据（知识库无相关内容或已跳过）</div>
      )}
    </div>
  )
}

/** M5：导出产物面板（清洁版 + 留痕版；Electron 打开所在文件夹，浏览器预览降级为下载链接） */
function ExportPanel({
  items,
  adopted,
  urls,
}: {
  items: ExportItem[]
  adopted: number | null
  urls: Record<number, string>
}) {
  if (items.length === 0) return null
  return (
    <div className="border-b border-slate-100 bg-teal-50/40 px-4 py-2.5">
      <div className="text-xs font-medium text-slate-600">
        导出产物（采纳 {adopted ?? 0} 条修订）
      </div>
      <div className="mt-1.5 space-y-1.5">
        {items.map((item) => (
          <div key={item.kind} className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded bg-teal-100 px-1.5 py-0.5 text-teal-700">{item.label}</span>
            <span className="font-medium text-slate-600">{item.name}</span>
            {item.size != null && (
              <span className="text-slate-400">({(item.size / 1024).toFixed(1)} KB)</span>
            )}
            {!item.exists && <span className="text-red-500">文件缺失，请重新导出</span>}
            {item.exists &&
              (isBrowserPreview() ? (
                <a
                  href={urls[item.kind]}
                  download={item.name}
                  className="rounded border border-teal-200 px-2 py-0.5 text-teal-600 hover:bg-teal-50"
                >
                  下载
                </a>
              ) : (
                <button
                  type="button"
                  onClick={() => void window.api.showItemInFolder(item.path)}
                  className="rounded border border-teal-200 px-2 py-0.5 text-teal-600 hover:bg-teal-50"
                >
                  打开所在文件夹
                </button>
              ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function BlockTree({
  detail,
  evidence,
}: {
  detail: DocumentDetail
  evidence: DocumentEvidence | null
}) {  const [openBlocks, setOpenBlocks] = useState<Set<number>>(new Set())
  const [openSentences, setOpenSentences] = useState<Set<number>>(new Set())

  const toggle = (set_: Dispatch<SetStateAction<Set<number>>>, id: number) => {
    set_((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const evidenceMap = new Map<number, EvidenceSentence>()
  if (evidence) {
    for (const block of evidence.blocks) {
      for (const s of block.sentences) evidenceMap.set(s.id, s)
    }
  }

  if (detail.blocks.length === 0) {
    return <div className="px-4 py-3 text-sm text-slate-400">暂无分块，请先点击「解析」。</div>
  }

  return (
    <div className="divide-y divide-slate-100 px-4 py-2">
      {detail.blocks.map((block) => (
        <div key={block.id} className="py-1.5">
          <button
            type="button"
            onClick={() => toggle(setOpenBlocks, block.id)}
            className="flex w-full items-center gap-2 rounded px-1 py-1 text-left text-sm hover:bg-slate-50"
          >
            <span className="text-slate-400">{openBlocks.has(block.id) ? '▾' : '▸'}</span>
            <span className="font-medium text-slate-700">
              #{block.idx + 1} {block.chapter ?? '（无章节）'}
            </span>
            {block.is_reference && (
              <span className="rounded-full bg-purple-50 px-2 py-0.5 text-xs text-purple-600">
                参考文献
              </span>
            )}
            <span className="ml-auto text-xs text-slate-400">{block.sentences.length} 句</span>
          </button>
          {openBlocks.has(block.id) && (
            <ol className="mt-1 space-y-1 border-l-2 border-slate-100 pl-6">
              {block.sentences.map((s) => {
                const ev = evidenceMap.get(s.id)
                const skipped = ev?.skipped ?? false
                const expandable = ev !== undefined && !skipped
                return (
                  <li key={s.id} className="text-sm leading-6 text-slate-600">
                    <button
                      type="button"
                      disabled={!expandable}
                      onClick={() => toggle(setOpenSentences, s.id)}
                      className={clsx(
                        'w-full rounded px-1 py-0.5 text-left',
                        expandable ? 'hover:bg-blue-50/60 cursor-pointer' : 'cursor-default',
                      )}
                    >
                      <span className="mr-2 text-xs text-slate-300">{s.idx + 1}.</span>
                      {s.text}
                      {skipped && (
                        <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-400">
                          跳过审校
                        </span>
                      )}
                      {expandable && ev.queries.length > 0 && (
                        <span className="ml-2 text-xs text-blue-400">
                          {openSentences.has(s.id) ? '▾' : '▸'} {ev.queries.length} 问 ·{' '}
                          {ev.evidence.length} 证
                        </span>
                      )}
                    </button>
                    {openSentences.has(s.id) && ev !== undefined && (
                      <SentenceEvidence sentence={ev} />
                    )}
                  </li>
                )
              })}
            </ol>
          )}
        </div>
      ))}
    </div>
  )
}

export default function DocumentsPage() {
  const navigate = useNavigate()
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [retrievingId, setRetrievingId] = useState<string | null>(null)
  const [reviewingId, setReviewingId] = useState<string | null>(null)
  const [reviewProgress, setReviewProgress] = useState<string | null>(null)
  const [reviewStart, setReviewStart] = useState<number | null>(null)
  const [reviewBlocks, setReviewBlocks] = useState<{ done: number; total: number | null }>({
    done: 0,
    total: null,
  })
  const [nowTick, setNowTick] = useState<number>(Date.now())
  const [exportingId, setExportingId] = useState<string | null>(null)
  const [exportData, setExportData] = useState<
    Record<string, { items: ExportItem[]; adopted: number | null; urls: Record<number, string> }>
  >({})
  const [kbReady, setKbReady] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<DocumentDetail | null>(null)
  const [evidence, setEvidence] = useState<DocumentEvidence | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [showParsed, setShowParsed] = useState(false)
  const [parsedText, setParsedText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const refresh = useCallback(async () => {
    try {
      const [docList, kbList] = await Promise.all([listDocuments(), listKbDocuments()])
      setDocs(docList)
      setKbReady(kbList.some((k) => k.status === 'indexed' && k.chunk_count > 0))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  // 审校进行中：每秒刷新一次「已持续时间」
  useEffect(() => {
    if (reviewingId === null) return
    const timer = setInterval(() => setNowTick(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [reviewingId])

  // 列表中存在瞬态状态（审校中/检索中）时轮询刷新：
  // 页面重开后也能跟上后台任务结束（done）或被启动清理标记为 failed，不会一直卡在「审校中」
  useEffect(() => {
    const hasTransient = docs.some((d) => d.status === 'reviewing' || d.status === 'retrieving')
    if (!hasTransient) return
    const timer = setTimeout(() => void refresh(), 2000)
    return () => clearTimeout(timer)
  }, [docs, refresh])

  const handleUpload = async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      await uploadDocument(file)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
    }
  }

  const loadDetail = async (id: string) => {
    setDetailLoading(true)
    setShowParsed(false)
    setParsedText(null)
    try {
      const detailData = await getDocumentDetail(id)
      setDetail(detailData)
      if (detailData.status === 'retrieved') {
        setEvidence(await getDocumentEvidence(id))
      } else {
        setEvidence(null)
      }
      if (['manual_done', 'done'].includes(detailData.status)) {
        void loadExports(id) // M5：展示已有导出产物
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setDetail(null)
      setEvidence(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleRun = async (id: string) => {
    setRunningId(id)
    setError(null)
    try {
      await runDocument(id)
      await refresh()
      if (expandedId === id) await loadDetail(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      await refresh()
    } finally {
      setRunningId(null)
    }
  }

  const handleRetrieve = async (id: string) => {
    setRetrievingId(id)
    setError(null)
    try {
      const result = await retrieveDocument(id)
      if (result.rewritten === 0) {
        setError('提示：未配置 LLM，本次检索降级为原句直接检索（设置页配置 llm.* 后启用查询重写）')
      }
      await refresh()
      if (expandedId === id) await loadDetail(id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      await refresh()
    } finally {
      setRetrievingId(null)
    }
  }

  /** M4：触发 LLM 审校（后台线程），SSE 跟踪进度（进度圈+计时），完成跳工作台，失败明确提示。 */
  const handleReview = async (id: string) => {
    setReviewingId(id)
    setReviewProgress('审校启动中…')
    setReviewStart(null)
    setReviewBlocks({ done: 0, total: null })
    setError(null)
    const clearReview = () => {
      setReviewingId(null)
      setReviewProgress(null)
      setReviewStart(null)
      setReviewBlocks({ done: 0, total: null })
    }
    let close: (() => void) | null = null
    try {
      const { job_id } = await reviewDocument(id)
      setReviewStart(Date.now())
      close = await subscribeJobEvents(job_id, {
        onEvent: (event, data) => {
          if (event === 'start') {
            const total = typeof data.blocks === 'number' ? data.blocks : null
            setReviewBlocks({ done: 0, total })
            setReviewProgress(`审校中：共 ${String(data.blocks ?? '?')} 个块`)
          } else if (event === 'progress' && data.block_idx !== undefined) {
            const total = typeof data.blocks === 'number' ? data.blocks : null
            setReviewBlocks({ done: (data.block_idx as number) + 1, total })
            setReviewProgress(
              `审校中：块 ${String((data.block_idx as number) + 1)}/${String(data.blocks ?? '?')}` +
                (typeof data.corrections === 'number' ? `，本块 ${data.corrections} 条建议` : ''),
            )
          } else if (event === 'error') {
            setError(`审校失败：${String(data.message ?? '未知错误')}`)
          }
        },
        onDone: (status) => {
          clearReview()
          if (status === 'done') {
            void refresh()
            navigate(`/workbench/${id}`)
          } else {
            // 失败：取回后端记录的错误原因，刷新列表让状态芯片显示「失败」
            void (async () => {
              try {
                const detailData = await getDocumentDetail(id)
                setError(`审校失败：${detailData.error ?? '未知错误，请重试'}`)
              } catch {
                setError('审校失败：未知错误，请重试')
              }
              await refresh()
            })()
          }
        },
        onError: (err) => {
          clearReview()
          setError(`审校失败：${err.message}`)
          void refresh()
        },
      })
    } catch (e) {
      close?.()
      clearReview()
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  /** M5：加载导出产物列表（含浏览器预览模式下的下载链接）。 */
  const loadExports = async (id: string) => {
    try {
      const data = await listExports(id)
      const urls: Record<number, string> = {}
      for (const kind of [1, 2] as const) {
        urls[kind] = await getExportDownloadUrl(id, kind)
      }
      setExportData((prev) => ({ ...prev, [id]: { items: data.exports, adopted: data.adopted, urls } }))
    } catch {
      /* 产物列表加载失败不阻塞页面 */
    }
  }

  /** M5：导出双版本 docx（同步接口，完成后刷新产物面板与文档状态）。 */
  const handleExport = async (id: string) => {
    setExportingId(id)
    setError(null)
    try {
      const result = await exportDocument(id)
      if (result.warnings.length > 0) {
        setError(
          `导出完成，但 ${result.warnings.length} 条修订未能在原文中定位（已保留原文）：` +
            `${result.warnings[0]}${result.warnings.length > 1 ? ' 等' : ''}`,
        )
      }
      await loadExports(id)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setExportingId(null)
    }
    if (expandedId === id) await loadDetail(id)
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      await deleteDocument(id)
      if (expandedId === id) {
        setExpandedId(null)
        setDetail(null)
        setEvidence(null)
      }
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const toggleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null)
      setDetail(null)
      setEvidence(null)
      return
    }
    setExpandedId(id)
    await loadDetail(id)
  }

  const toggleParsed = async (id: string) => {
    if (showParsed) {
      setShowParsed(false)
      return
    }
    try {
      setParsedText(await getParsed(id))
      setShowParsed(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">文档库</h1>
        <input
          ref={fileInputRef}
          type="file"
          accept=".docx"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void handleUpload(file)
            e.target.value = ''
          }}
        />
        <button
          type="button"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? '上传中…' : '上传文档'}
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      {reviewingId !== null && (
        <div className="mb-3 flex items-center gap-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3">
          <ProgressRing done={reviewBlocks.done} total={reviewBlocks.total} />
          <div className="min-w-0">
            <div className="text-sm font-medium text-emerald-700">
              {reviewProgress ?? '审校启动中…'}
            </div>
            <div className="mt-0.5 text-xs text-emerald-600/80">
              {reviewStart !== null ? (
                <>
                  开始于 {formatClock(reviewStart)} · 已持续 {formatElapsed(nowTick - reviewStart)}
                </>
              ) : (
                '正在启动审校任务…'
              )}
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-sm text-slate-400">
          加载中…
        </div>
      ) : docs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
          暂无文档，点击右上角「上传文档」开始
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs text-slate-500">
                <th className="px-4 py-2 font-medium">文件名</th>
                <th className="w-24 px-4 py-2 font-medium">状态</th>
                <th className="w-44 px-4 py-2 font-medium">上传时间</th>
                <th className="w-72 px-4 py-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <Fragment key={doc.id}>
                  <tr
                    onClick={() => void toggleExpand(doc.id)}
                    className={clsx(
                      'cursor-pointer border-b border-slate-100 hover:bg-slate-50',
                      expandedId === doc.id && 'bg-blue-50/40',
                    )}
                  >
                    <td className="px-4 py-2.5">
                      <div className="font-medium text-slate-700">{doc.filename}</div>
                      {doc.error && <div className="mt-0.5 text-xs text-red-500">{doc.error}</div>}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusChip status={doc.status} />
                    </td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">
                      {new Date(doc.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={runningId === doc.id || retrievingId === doc.id}
                          onClick={() => void handleRun(doc.id)}
                          className="rounded border border-blue-200 px-2.5 py-1 text-xs text-blue-600 hover:bg-blue-50 disabled:opacity-50"
                        >
                          {runningId === doc.id ? '解析中…' : '解析'}
                        </button>
                        <button
                          type="button"
                          disabled={
                            retrievingId === doc.id ||
                            runningId === doc.id ||
                            !kbReady ||
                            !['segmented', 'retrieved', 'failed'].includes(doc.status)
                          }
                          title={
                            kbReady
                              ? '对全文档句子执行 3+3 混合检索'
                              : '请先在医学知识库页上传并索引参考文档'
                          }
                          onClick={() => void handleRetrieve(doc.id)}
                          className="rounded border border-indigo-200 px-2.5 py-1 text-xs text-indigo-600 hover:bg-indigo-50 disabled:opacity-50"
                        >
                          {retrievingId === doc.id ? '检索中…' : '检索'}
                        </button>
                        {['segmented', 'retrieved', 'failed'].includes(doc.status) && (
                          <button
                            type="button"
                            disabled={reviewingId === doc.id || runningId === doc.id || retrievingId === doc.id}
                            title="LLM 结构化审校（需先在设置页配置 llm.*）；失败后可重试"
                            onClick={() => void handleReview(doc.id)}
                            className="rounded border border-emerald-200 px-2.5 py-1 text-xs text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                          >
                            {reviewingId === doc.id
                              ? '审校中…'
                              : doc.status === 'failed'
                                ? '重试审校'
                                : 'AI 审校'}
                          </button>
                        )}
                        {doc.status === 'reviewing' && (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-amber-600">
                            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
                            审校中…
                          </span>
                        )}
                        {doc.status === 'pending_manual' && (
                          <button
                            type="button"
                            onClick={() => navigate(`/workbench/${doc.id}`)}
                            className="rounded border border-orange-200 px-2.5 py-1 text-xs text-orange-600 hover:bg-orange-50"
                          >
                            继续审校
                          </button>
                        )}
                        {['manual_done', 'done'].includes(doc.status) && (
                          <button
                            type="button"
                            onClick={() => navigate(`/workbench/${doc.id}`)}
                            className="rounded border border-emerald-200 px-2.5 py-1 text-xs text-emerald-600 hover:bg-emerald-50"
                          >
                            查看审校
                          </button>
                        )}
                        {['manual_done', 'done'].includes(doc.status) && (
                          <button
                            type="button"
                            disabled={exportingId === doc.id}
                            title="导出双版本 docx：清洁版（_审校修订1_）+ 留痕版（_审校修订2_）"
                            onClick={() => void handleExport(doc.id)}
                            className="rounded border border-teal-200 px-2.5 py-1 text-xs text-teal-600 hover:bg-teal-50 disabled:opacity-50"
                          >
                            {exportingId === doc.id ? '导出中…' : '导出成稿'}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => void handleDelete(doc.id)}
                          className="rounded border border-slate-200 px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-50"
                        >
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedId === doc.id && (
                    <tr className="border-b border-slate-100 bg-slate-50/50">
                      <td colSpan={4} className="p-0">
                        {exportData[doc.id] && (
                          <ExportPanel
                            items={exportData[doc.id].items}
                            adopted={exportData[doc.id].adopted}
                            urls={exportData[doc.id].urls}
                          />
                        )}
                        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2">
                          <span className="text-xs font-medium text-slate-500">
                            分块结果{evidence ? '（点击句子展开重写问题与证据）' : ''}
                          </span>
                          <button
                            type="button"
                            onClick={() => void toggleParsed(doc.id)}
                            className="rounded border border-slate-200 px-2 py-0.5 text-xs text-slate-500 hover:bg-white"
                          >
                            {showParsed ? '隐藏 parsed.md' : '查看 parsed.md'}
                          </button>
                        </div>
                        {showParsed && parsedText !== null && (
                          <pre className="max-h-72 overflow-auto whitespace-pre-wrap border-b border-slate-100 bg-white px-4 py-3 text-xs leading-5 text-slate-600">
                            {parsedText}
                          </pre>
                        )}
                        {detailLoading ? (
                          <div className="px-4 py-3 text-sm text-slate-400">加载中…</div>
                        ) : detail && detail.id === doc.id ? (
                          <BlockTree detail={detail} evidence={evidence} />
                        ) : (
                          <div className="px-4 py-3 text-sm text-slate-400">暂无详情</div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

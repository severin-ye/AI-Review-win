import { useCallback, useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import {
  deleteKbDocument,
  listKbDocuments,
  reindexKbDocument,
  subscribeJobEvents,
  uploadKbDocument,
  type KbDocumentItem,
} from '@/api/client'

const STATUS_META: Record<string, { label: string; className: string }> = {
  indexing: { label: '索引中', className: 'bg-amber-50 text-amber-700' },
  indexed: { label: '已索引', className: 'bg-green-50 text-green-700' },
  failed: { label: '索引失败', className: 'bg-red-50 text-red-600' },
  uploaded: { label: '已上传', className: 'bg-slate-100 text-slate-600' },
}

function StatusChip({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, className: 'bg-slate-100 text-slate-600' }
  return (
    <span className={clsx('inline-block rounded-full px-2 py-0.5 text-xs', meta.className)}>
      {meta.label}
    </span>
  )
}

interface ProgressItem {
  jobId: string
  label: string
  lines: string[]
  done: boolean
}

export default function KnowledgeBasePage() {
  const [docs, setDocs] = useState<KbDocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<ProgressItem[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const closersRef = useRef<Array<() => void>>([])

  const refresh = useCallback(async () => {
    try {
      setDocs(await listKbDocuments())
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const closers = closersRef.current
    return () => closers.forEach((close) => close())
  }, [refresh])

  const pushLine = (jobId: string, line: string) => {
    setProgress((prev) =>
      prev.map((p) => (p.jobId === jobId ? { ...p, lines: [...p.lines.slice(-19), line] } : p)),
    )
  }

  const trackJob = useCallback(
    async (jobId: string, label: string) => {
      setProgress((prev) => [{ jobId, label, lines: ['开始索引…'], done: false }, ...prev.slice(0, 4)])
      const close = await subscribeJobEvents(jobId, {
        onEvent: (event, data) => {
          if (event === 'loaded') pushLine(jobId, `已加载文本 ${String(data.chars)} 字`)
          else if (event === 'chunked') pushLine(jobId, `切块完成：${String(data.chunks)} 块`)
          else if (event === 'embedding')
            pushLine(jobId, `向量化 ${String(data.done)}/${String(data.total)}`)
          else if (event === 'bm25') pushLine(jobId, `BM25 索引重建：${String(data.indexed_chunks)} 块`)
          else if (event === 'skipped') pushLine(jobId, `⏭ ${String(data.reason)}`)
          else if (event === 'error') pushLine(jobId, `❌ ${String(data.message)}`)
        },
        onDone: (status) => {
          pushLine(jobId, status === 'done' ? '✅ 索引完成' : '❌ 索引失败')
          setProgress((prev) => prev.map((p) => (p.jobId === jobId ? { ...p, done: true } : p)))
          void refresh()
        },
        onError: () => {
          setProgress((prev) => prev.map((p) => (p.jobId === jobId ? { ...p, done: true } : p)))
          void refresh()
        },
      })
      closersRef.current.push(close)
    },
    [refresh],
  )

  const handleUpload = async (files: FileList) => {
    setUploading(true)
    setError(null)
    try {
      for (const file of Array.from(files)) {
        const result = await uploadKbDocument(file)
        void trackJob(result.job_id, file.name)
      }
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
    }
  }

  const handleReindex = async (doc: KbDocumentItem) => {
    setBusyId(doc.id)
    setError(null)
    try {
      const { job_id } = await reindexKbDocument(doc.id)
      void trackJob(job_id, `重新索引：${doc.filename}`)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyId(null)
    }
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      await deleteKbDocument(id)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">医学知识库</h1>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.csv,.docx"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) void handleUpload(e.target.files)
            e.target.value = ''
          }}
        />
        <button
          type="button"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? '上传中…' : '上传参考文档'}
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      {progress.length > 0 && (
        <div className="mb-4 space-y-2">
          {progress.map((p) => (
            <div
              key={p.jobId}
              className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-xs"
            >
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={clsx(
                    'inline-block h-2 w-2 rounded-full',
                    p.done ? 'bg-green-500' : 'animate-pulse bg-amber-500',
                  )}
                />
                <span className="font-medium text-slate-600">{p.label}</span>
              </div>
              <div className="space-y-0.5 font-mono text-slate-400">
                {p.lines.map((line, i) => (
                  <div key={i}>{line}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-sm text-slate-400">
          加载中…
        </div>
      ) : docs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
          知识库为空，上传指南 / 药品说明书等参考文档（pdf / txt / csv / docx）后自动索引
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs text-slate-500">
                <th className="px-4 py-2 font-medium">文件名</th>
                <th className="w-24 px-4 py-2 font-medium">状态</th>
                <th className="w-24 px-4 py-2 font-medium">chunk 数</th>
                <th className="w-44 px-4 py-2 font-medium">上传时间</th>
                <th className="w-44 px-4 py-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-slate-700">{doc.filename}</div>
                    {doc.content_hash && (
                      <div className="mt-0.5 font-mono text-xs text-slate-300">
                        hash {doc.content_hash}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusChip status={doc.status} />
                  </td>
                  <td className="px-4 py-2.5 text-slate-600">{doc.chunk_count}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">
                    {new Date(doc.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busyId === doc.id || doc.status === 'indexing'}
                        onClick={() => void handleReindex(doc)}
                        className="rounded border border-blue-200 px-2.5 py-1 text-xs text-blue-600 hover:bg-blue-50 disabled:opacity-50"
                      >
                        重新索引
                      </button>
                      <button
                        type="button"
                        disabled={doc.status === 'indexing'}
                        onClick={() => void handleDelete(doc.id)}
                        className="rounded border border-slate-200 px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-50 disabled:opacity-50"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

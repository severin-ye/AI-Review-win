import { useCallback, useEffect, useState } from 'react'
import {
  downloadModels,
  getModelsStatus,
  getSettings,
  putSettings,
  subscribeJobEvents,
  testLlmConnection,
  type ModelsStatus,
} from '@/api/client'
import LicenseStatusSection from '@/license/LicenseStatusSection'

interface FieldDef {
  key: string
  label: string
  placeholder?: string
  type?: 'text' | 'password' | 'number' | 'select'
  options?: { value: string; label: string }[]
  hint?: string
}

const sections: { title: string; fields: FieldDef[] }[] = [
  {
    title: 'LLM（OpenAI 兼容协议，查询重写与审校共用）',
    fields: [
      { key: 'llm.base_url', label: 'Base URL', placeholder: 'https://api.openai.com/v1' },
      {
        key: 'llm.api_key',
        label: 'API Key',
        type: 'password',
        placeholder: 'sk-…',
        hint: '密钥仅写入不回读：已保存时显示掩码（****+后4位），保持掩码保存则原值不变；输入新值即替换，清空即删除',
      },
      { key: 'llm.model', label: '模型', placeholder: 'gpt-4o-mini / deepseek-chat / …' },
    ],
  },
  {
    title: '检索参数（每句 3+3 混合检索）',
    fields: [
      {
        key: 'retrieve.query_count',
        label: '查询重写数量',
        type: 'number',
        hint: '默认 8，范围 5-10；一次 LLM 调用生成，含原句',
      },
      { key: 'retrieve.vector_topk', label: '向量检索条数', type: 'number', hint: '默认 3' },
      { key: 'retrieve.bm25_topk', label: '关键词检索条数', type: 'number', hint: '默认 3' },
    ],
  },
  {
    title: 'Embedding',
    fields: [
      {
        key: 'embedding.provider',
        label: 'Provider',
        type: 'select',
        options: [
          { value: 'local', label: 'local（本地 BGE-M3，sentence-transformers）' },
          { value: 'openai', label: 'openai（走 LLM Base URL 的 /embeddings）' },
        ],
      },
      {
        key: 'embedding.model',
        label: '模型',
        placeholder: 'BAAI/bge-m3',
        hint: 'local=HF 模型名（或下方「模型管理」预下载到本地目录，自动探测）；openai=远端模型名',
      },
    ],
  },
  {
    title: '导出',
    fields: [
      {
        key: 'output.dir',
        label: '导出目录',
        placeholder: '留空 = projects/<doc_id>/exports/',
        hint: '双版本 docx（清洁版 _审校修订1_ / 留痕版 _审校修订2_）的输出目录；留空则随文档项目目录',
      },
    ],
  },
]

function asString(value: unknown, fallback = ''): string {
  if (value === undefined || value === null) return fallback
  return String(value)
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(2)} GB`
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(1)} KB`
}

/** M5 模型管理：SaT / BGE-M3 本地状态展示 + hf-mirror 预下载（jobs/SSE 进度）。 */
function ModelManager() {
  const [status, setStatus] = useState<ModelsStatus | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  const load = useCallback(async () => {
    try {
      setStatus(await getModelsStatus())
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : String(e) })
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleDownload = async () => {
    setDownloading(true)
    setProgress('启动下载…')
    setMessage(null)
    let close: (() => void) | null = null
    try {
      const { job_id } = await downloadModels()
      close = await subscribeJobEvents(job_id, {
        onEvent: (event, data) => {
          if (event === 'progress') {
            const label = `${String(data.model ?? '')}/${String(data.file ?? '')}`
            if (data.status === 'downloading') {
              setProgress(`下载中：${label}（${String(data.done ?? 0)}/${String(data.total ?? '?')}）`)
            } else if (data.status === 'done') {
              setProgress(`已完成 ${String(data.done ?? '?')}/${String(data.total ?? '?')}：${label}`)
            } else if (data.status === 'exists') {
              setProgress(`已存在跳过：${label}`)
            }
          } else if (event === 'warning' || event === 'error') {
            setMessage({ ok: false, text: String(data.message ?? '下载失败') })
          }
        },
        onDone: (s) => {
          setDownloading(false)
          setProgress(null)
          setMessage(
            s === 'done'
              ? { ok: true, text: '模型下载完成，已就绪' }
              : { ok: false, text: '部分文件下载失败，可重新点击下载（断点续传）' },
          )
          void load()
        },
        onError: (err) => {
          setDownloading(false)
          setProgress(null)
          setMessage({ ok: false, text: err.message })
          void load()
        },
      })
    } catch (e) {
      close?.()
      setDownloading(false)
      setProgress(null)
      setMessage({ ok: false, text: e instanceof Error ? e.message : String(e) })
    }
  }

  const rows: { key: keyof Pick<ModelsStatus, 'sat' | 'sat_tokenizer' | 'bge_m3'>; label: string; note: string }[] = [
    { key: 'sat', label: 'SaT 分句模型', note: 'sat-3l-sm（约 815MB）' },
    { key: 'sat_tokenizer', label: 'SaT 分词器', note: 'xlm-roberta-base tokenizer' },
    { key: 'bge_m3', label: 'BGE-M3 向量模型', note: 'bge-m3（约 2.27GB，检索用）' },
  ]

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h2 className="mb-1 text-sm font-semibold text-slate-700">模型管理</h2>
      <p className="mb-3 text-xs text-slate-400">
        本地模型目录自动探测（{status?.models_dir ?? '<数据目录>/models'}）；从 hf-mirror 预下载，支持断点续传
      </p>
      <div className="space-y-2">
        {rows.map(({ key, label, note }) => {
          const entry = status?.[key]
          return (
            <div key={key} className="flex items-center gap-2 text-sm">
              <span
                className={
                  entry?.ready
                    ? 'rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700'
                    : 'rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500'
                }
              >
                {entry?.ready ? '已就绪' : '未下载'}
              </span>
              <span className="font-medium text-slate-600">{label}</span>
              <span className="text-xs text-slate-400">{note}</span>
              <span className="ml-auto text-xs text-slate-400">
                {entry?.exists ? formatBytes(entry.size_bytes) : '—'}
                {entry?.loaded && <span className="ml-2 text-emerald-600">已加载</span>}
              </span>
            </div>
          )
        })}
      </div>
      {progress && (
        <div className="mt-3 flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          {progress}
        </div>
      )}
      {message && (
        <div className={`mt-3 text-xs ${message.ok ? 'text-green-600' : 'text-red-600'}`}>
          {message.text}
        </div>
      )}
      <button
        type="button"
        disabled={downloading}
        onClick={() => void handleDownload()}
        className="mt-4 rounded-md border border-blue-300 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 disabled:opacity-50"
      >
        {downloading ? '下载中…' : '下载 / 补齐缺失模型'}
      </button>
    </div>
  )
}

/** LLM 连通测试状态：idle（未测/配置已改）→ testing（测试中 tag）→ ok（绿勾）/ fail（红叉） */
interface LlmTestState {
  state: 'idle' | 'testing' | 'ok' | 'fail'
  message?: string
  latencyMs?: number
}

export default function SettingsPage() {
  const [values, setValues] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [llmTest, setLlmTest] = useState<LlmTestState>({ state: 'idle' })

  const load = useCallback(async () => {
    try {
      const settings = await getSettings()
      const initial: Record<string, string> = {}
      for (const section of sections) {
        for (const field of section.fields) {
          initial[field.key] = asString(settings[field.key])
        }
      }
      setValues(initial)
      setMessage(null)
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : String(e) })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const payload: Record<string, unknown> = {}
      for (const section of sections) {
        for (const field of section.fields) {
          const raw = values[field.key] ?? ''
          payload[field.key] = field.type === 'number' ? Number(raw) || 0 : raw
        }
      }
      await putSettings(payload)
      setMessage({ ok: true, text: '已保存' })
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : String(e) })
      setSaving(false)
      return
    }
    setSaving(false)
    // 保存成功 → 自动做 LLM 连通性测试（测试中 tag → 绿勾 / 红叉）
    setLlmTest({ state: 'testing' })
    try {
      const result = await testLlmConnection()
      if (result.ok) {
        setLlmTest({ state: 'ok', latencyMs: result.latency_ms, message: result.model })
      } else {
        setLlmTest({ state: 'fail', message: result.message ?? '未知错误' })
      }
    } catch (e) {
      setLlmTest({ state: 'fail', message: e instanceof Error ? e.message : String(e) })
    }
  }

  /** 编辑 llm.* 字段时使上次测试结果失效（避免绿勾/红叉与当前表单值不符）。 */
  const handleFieldChange = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    if (key.startsWith('llm.') && llmTest.state !== 'idle') {
      setLlmTest({ state: 'idle' })
    }
  }

  if (loading) {
    return (
      <section className="max-w-xl">
        <h1 className="mb-4 text-xl font-semibold">设置</h1>
        <div className="rounded-lg border border-slate-200 bg-white p-10 text-center text-sm text-slate-400">
          加载中…
        </div>
      </section>
    )
  }

  return (
    <section className="max-w-xl">
      <h1 className="mb-4 text-xl font-semibold">设置</h1>
      <div className="space-y-5">
        {sections.map((section) => (
          <div key={section.title} className="rounded-lg border border-slate-200 bg-white p-6">
            <h2 className="mb-3 text-sm font-semibold text-slate-700">{section.title}</h2>
            <div className="space-y-4">
              {section.fields.map((field) => (
                <label key={field.key} className="block">
                  <span className="mb-1 block text-sm font-medium text-slate-600">
                    {field.label}
                    <span className="ml-2 font-mono text-xs text-slate-300">{field.key}</span>
                  </span>
                  {field.type === 'select' ? (
                    <select
                      value={values[field.key] ?? ''}
                      onChange={(e) => handleFieldChange(field.key, e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
                    >
                      {field.options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'}
                      value={values[field.key] ?? ''}
                      placeholder={field.placeholder}
                      onChange={(e) => handleFieldChange(field.key, e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
                    />
                  )}
                  {field.hint && <span className="mt-1 block text-xs text-slate-400">{field.hint}</span>}
                </label>
              ))}
            </div>
          </div>
        ))}
        <ModelManager />
        <LicenseStatusSection />
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={saving || llmTest.state === 'testing'}
            onClick={() => void handleSave()}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? '保存中…' : llmTest.state === 'testing' ? '保存并测试中…' : '保存'}
          </button>
          {message && (
            <span className={message.ok ? 'text-sm text-green-600' : 'text-sm text-red-600'}>
              {message.text}
            </span>
          )}
          {/* LLM 连通性测试状态 tag：保存后自动触发 */}
          {llmTest.state === 'testing' && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs text-amber-700">
              <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
              LLM 连通性测试中…
            </span>
          )}
          {llmTest.state === 'ok' && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
              <span className="text-emerald-600">✓</span>
              LLM 连接正常
              {llmTest.message && <span className="text-emerald-500">（{llmTest.message}）</span>}
              {llmTest.latencyMs != null && (
                <span className="text-emerald-400">{llmTest.latencyMs}ms</span>
              )}
            </span>
          )}
          {llmTest.state === 'fail' && (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600"
              title={llmTest.message}
            >
              <span>✗</span>
              LLM 连接失败
            </span>
          )}
        </div>
        {llmTest.state === 'fail' && llmTest.message && (
          <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs leading-5 text-red-600">
            {llmTest.message}
          </div>
        )}
      </div>
    </section>
  )
}

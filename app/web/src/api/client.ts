/**
 * fetch 封装：baseUrl 由主进程经预加载脚本注入（window.api.getBackendUrl）。
 * 非 Electron 环境（浏览器调试）回退到 127.0.0.1:8765（配合 npm run backend:dev）。
 */

let baseUrlPromise: Promise<string> | null = null

export function getBaseUrl(): Promise<string> {
  if (!baseUrlPromise) {
    baseUrlPromise =
      typeof window !== 'undefined' && window.api
        ? window.api.getBackendUrl()
        : Promise.resolve('http://127.0.0.1:8765')
  }
  return baseUrlPromise
}

/** 纯浏览器预览模式（无 Electron 预加载注入的 window.api）——UI 据此显示提示条并降级系统集成功能 */
export function isBrowserPreview(): boolean {
  return typeof window !== 'undefined' && !window.api
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${String(res.status)} ${res.statusText}`)
  }
  return (await res.json()) as T
}

/* ---------- M2 文档库 ---------- */

export interface DocumentItem {
  id: string
  filename: string
  status: string
  error: string | null
  created_at: string
}

export interface CorrectionItem {
  id: number
  original: string
  suggestion: string
  error_type: string
  severity: 'high' | 'medium' | 'low' | string
  explanation: string
  evidence_ids: number[]
  decision: 'pending' | 'accepted' | 'rejected' | 'custom'
  custom_text: string | null
  decided_at: string | null
}

export interface SentenceItem {
  id: number
  idx: number
  text: string
  corrections: CorrectionItem[]
  evidence: EvidenceItem[]
}

export interface BlockItem {
  id: number
  idx: number
  chapter: string | null
  is_reference: boolean
  text: string
  sentences: SentenceItem[]
}

export interface DocumentDetail {
  id: string
  filename: string
  status: string
  error: string | null
  blocks: BlockItem[]
}

export interface RunResult {
  job_id: string
  status: string
  blocks: number
  sentences: number
  segmenter: string
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const base = await getBaseUrl()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${base}/api/documents`, { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`上传失败: ${String(res.status)} ${detail}`)
  }
  return (await res.json()) as DocumentItem
}

export function listDocuments(): Promise<DocumentItem[]> {
  return apiFetch<DocumentItem[]>('/api/documents')
}

export async function runDocument(id: string): Promise<RunResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/documents/${id}/run`, { method: 'POST' })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `解析失败: ${String(res.status)}`)
  }
  return (await res.json()) as RunResult
}

export function getDocumentDetail(id: string): Promise<DocumentDetail> {
  return apiFetch<DocumentDetail>(`/api/documents/${id}/detail`)
}

export async function getParsed(id: string): Promise<string> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/documents/${id}/parsed`)
  if (!res.ok) {
    throw new Error(`获取 parsed.md 失败: ${String(res.status)}`)
  }
  return res.text()
}

export function deleteDocument(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/documents/${id}`, { method: 'DELETE' })
}

/* ---------- M3 医学知识库 ---------- */

export interface KbDocumentItem {
  id: string
  filename: string
  status: string // indexing | indexed | failed
  chunk_count: number
  content_hash: string
  created_at: string
}

export interface KbUploadResult extends KbDocumentItem {
  job_id: string
}

export async function uploadKbDocument(file: File): Promise<KbUploadResult> {
  const base = await getBaseUrl()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${base}/api/kb/documents`, { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`上传失败: ${String(res.status)} ${detail}`)
  }
  return (await res.json()) as KbUploadResult
}

export function listKbDocuments(): Promise<KbDocumentItem[]> {
  return apiFetch<KbDocumentItem[]>('/api/kb/documents')
}

export function deleteKbDocument(id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/api/kb/documents/${id}`, { method: 'DELETE' })
}

export function reindexKbDocument(id: string): Promise<{ job_id: string; id: string }> {
  return apiFetch<{ job_id: string; id: string }>(`/api/kb/documents/${id}/reindex`, {
    method: 'POST',
  })
}

/* ---------- M3 检索 ---------- */

export interface RetrieveResult {
  job_id: string
  status: string
  sentences: number
  evidence: number
  rewritten: number
}

export async function retrieveDocument(id: string): Promise<RetrieveResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/documents/${id}/retrieve`, { method: 'POST' })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `检索失败: ${String(res.status)}`)
  }
  return (await res.json()) as RetrieveResult
}

export interface QueryItem {
  id: number
  idx: number
  text: string
}

export interface EvidenceItem {
  id: number
  source: 'vector' | 'keyword'
  chunk_text: string
  doc_name: string
  score: number
  rank: number
}

export interface EvidenceSentence {
  id: number
  idx: number
  text: string
  skipped: boolean
  queries: QueryItem[]
  evidence: EvidenceItem[]
}

export interface EvidenceBlock {
  id: number
  idx: number
  chapter: string | null
  is_reference: boolean
  sentences: EvidenceSentence[]
}

export interface DocumentEvidence {
  id: string
  filename: string
  status: string
  blocks: EvidenceBlock[]
}

export function getDocumentEvidence(id: string): Promise<DocumentEvidence> {
  return apiFetch<DocumentEvidence>(`/api/documents/${id}/evidence`)
}

/* ---------- 设置 ---------- */

export type SettingsMap = Record<string, unknown>

export function getSettings(): Promise<SettingsMap> {
  return apiFetch<SettingsMap>('/api/settings')
}

export function putSettings(payload: SettingsMap): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>('/api/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export interface LlmTestResult {
  ok: boolean
  stage?: 'config' | 'connect'
  message?: string
  model?: string
  latency_ms?: number
  reply?: string
}

/** LLM 连通性测试（后端读库中已保存配置发起一次最小调用；失败不抛错，ok=false+message）。 */
export async function testLlmConnection(): Promise<LlmTestResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/settings/test-llm`, { method: 'POST' })
  if (!res.ok) {
    throw new Error(`连通测试请求失败: ${String(res.status)}`)
  }
  return (await res.json()) as LlmTestResult
}

/* ---------- M4 审校与人工决定 ---------- */

export interface ReviewStartResult {
  job_id: string
  status: string
}

/** 触发 LLM 审校（后台线程）；进度用 subscribeJobEvents(job_id) 订阅。 */
export async function reviewDocument(id: string, force = false): Promise<ReviewStartResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/documents/${id}/review?force=${force}`, { method: 'POST' })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `审校失败: ${String(res.status)}`)
  }
  return (await res.json()) as ReviewStartResult
}

export interface DecisionResult {
  correction: CorrectionItem
  document_status: string
}

export async function decideCorrection(
  id: number,
  decision: 'accepted' | 'rejected' | 'custom' | 'pending',
  customText?: string,
): Promise<DecisionResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/corrections/${id}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, custom_text: customText ?? null }),
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `决定失败: ${String(res.status)}`)
  }
  return (await res.json()) as DecisionResult
}

export interface BatchFilter {
  severity?: string
  error_type?: string
  decision?: string
}

export interface BatchResult {
  affected: number
  document_status: string
}

export async function batchDecide(
  docId: string,
  filter: BatchFilter,
  action: 'accept' | 'reject',
): Promise<BatchResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/documents/${docId}/decisions/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filter, action }),
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `批量操作失败: ${String(res.status)}`)
  }
  return (await res.json()) as BatchResult
}

export interface JobInfo {
  id: string
  type: string
  status: string
  document_id: string | null
}

export function getJob(jobId: string): Promise<JobInfo> {
  return apiFetch<JobInfo>(`/api/jobs/${jobId}`)
}

/* ---------- M5 导出双版本 docx ---------- */

export interface ExportResult {
  job_id: string
  status: string
  clean_path: string
  marked_path: string
  adopted: number
  warnings: string[]
  tables_restored: Record<string, number>
}

export interface ExportItem {
  kind: 1 | 2
  label: string
  name: string
  path: string
  exists: boolean
  size: number | null
}

export interface ExportListResult {
  exports: ExportItem[]
  adopted: number | null
}

/** 触发导出（同步执行）：生成 清洁版(_审校修订1_) + 留痕版(_审校修订2_)。 */
export async function exportDocument(id: string): Promise<ExportResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/documents/${id}/export`, { method: 'POST' })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `导出失败: ${String(res.status)}`)
  }
  return (await res.json()) as ExportResult
}

export function listExports(id: string): Promise<ExportListResult> {
  return apiFetch<ExportListResult>(`/api/documents/${id}/exports`)
}

/** 导出产物下载地址（kind=1 清洁版 / 2 留痕版）；浏览器预览模式下用作 <a> 下载链接。 */
export async function getExportDownloadUrl(id: string, kind: 1 | 2): Promise<string> {
  const base = await getBaseUrl()
  return `${base}/api/documents/${id}/exports/${kind}`
}

/* ---------- M5 模型管理 ---------- */

export interface ModelEntry {
  path: string
  exists: boolean
  size_bytes: number
  file_count: number
  missing_files: string[]
  ready: boolean
  loaded: boolean
}

export interface ModelsStatus {
  models_dir: string
  sat: ModelEntry
  sat_tokenizer: ModelEntry
  bge_m3: ModelEntry
}

export function getModelsStatus(): Promise<ModelsStatus> {
  return apiFetch<ModelsStatus>('/api/models/status')
}

export interface DownloadModelsResult {
  job_id: string
  models: string[]
}

export async function downloadModels(models?: string[]): Promise<DownloadModelsResult> {
  const base = await getBaseUrl()
  const res = await fetch(`${base}/api/models/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ models: models ?? ['sat', 'sat-tokenizer', 'bge-m3'] }),
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail ?? `模型下载失败: ${String(res.status)}`)
  }
  return (await res.json()) as DownloadModelsResult
}

/* ---------- SSE 任务事件 ---------- */

export interface JobEventHandlers {
  onEvent?: (event: string, data: Record<string, unknown>) => void
  onDone?: (status: string) => void
  onError?: (err: Error) => void
}

/** 订阅 /api/jobs/{id}/events（SSE）。返回关闭函数。 */
export async function subscribeJobEvents(
  jobId: string,
  handlers: JobEventHandlers,
): Promise<() => void> {
  const base = await getBaseUrl()
  const source = new EventSource(`${base}/api/jobs/${jobId}/events`)
  const listener = (event: string) => (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data as string) as Record<string, unknown>
      handlers.onEvent?.(event, data)
    } catch {
      /* 忽略无法解析的事件 */
    }
  }
  const events = [
    'start',
    'loaded',
    'chunked',
    'embedding',
    'bm25',
    'progress',
    'skipped',
    'warning',
    'stage_done',
    'error',
  ]
  const removers = events.map((name) => {
    const fn = listener(name)
    source.addEventListener(name, fn)
    return () => source.removeEventListener(name, fn)
  })
  source.addEventListener('done', (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data as string) as { status?: string }
      handlers.onDone?.(data.status ?? 'done')
    } catch {
      handlers.onDone?.('done')
    }
    source.close()
  })
  source.onerror = () => {
    handlers.onError?.(new Error('SSE 连接中断'))
    source.close()
  }
  return () => {
    removers.forEach((fn) => fn())
    source.close()
  }
}

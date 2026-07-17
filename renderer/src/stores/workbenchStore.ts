import { create } from 'zustand'
import {
  batchDecide,
  decideCorrection,
  getDocumentDetail,
  type BlockItem,
  type CorrectionItem,
} from '@/api/client'
import { toast } from '@/components/ui/sonner'

/** 扁平化后的 correction：携带所属句/块上下文，供卡片列表直接渲染。 */
export interface FlatCorrection extends CorrectionItem {
  sentence_id: number
  sentence_text: string
  block_idx: number
  chapter: string | null
}

export interface WorkbenchFilters {
  decision: 'all' | 'pending' | 'accepted' | 'rejected' | 'custom'
  errorType: 'all' | '事实错误' | '术语错误' | '语法错误' | '格式错误'
  severity: 'all' | 'high' | 'medium' | 'low'
}

interface WorkbenchState {
  docId: string | null
  filename: string
  status: string
  loading: boolean
  error: string | null
  blocks: BlockItem[]
  /** correction id → 扁平化 correction（决定在此乐观更新） */
  corrections: Record<number, FlatCorrection>
  /** 文档顺序的 correction id 列表 */
  order: number[]
  filters: WorkbenchFilters
  selectedId: number | null
  /** 自定义输入框打开的 correction id */
  editingId: number | null

  load: (docId: string) => Promise<void>
  reset: () => void
  setFilter: <K extends keyof WorkbenchFilters>(key: K, value: WorkbenchFilters[K]) => void
  select: (id: number | null) => void
  setEditing: (id: number | null) => void
  moveSelection: (delta: number) => void
  decide: (id: number, decision: 'accepted' | 'rejected' | 'custom', customText?: string) => Promise<void>
  undo: (id: number) => Promise<void>
  batch: (filter: { severity?: string }, action: 'accept' | 'reject', label: string) => Promise<void>
}

function flatten(blocks: BlockItem[]): {
  corrections: Record<number, FlatCorrection>
  order: number[]
} {
  const corrections: Record<number, FlatCorrection> = {}
  const order: number[] = []
  for (const block of blocks) {
    for (const sentence of block.sentences) {
      for (const c of sentence.corrections) {
        corrections[c.id] = {
          ...c,
          sentence_id: sentence.id,
          sentence_text: sentence.text,
          block_idx: block.idx,
          chapter: block.chapter,
        }
        order.push(c.id)
      }
    }
  }
  return { corrections, order }
}

/** 当前筛选条件下的可见 id 列表（文档顺序）。 */
export function filteredIds(state: Pick<WorkbenchState, 'order' | 'corrections' | 'filters'>): number[] {
  return state.order.filter((id) => {
    const c = state.corrections[id]
    if (!c) return false
    if (state.filters.decision !== 'all' && c.decision !== state.filters.decision) return false
    if (state.filters.errorType !== 'all' && c.error_type !== state.filters.errorType) return false
    if (state.filters.severity !== 'all' && c.severity !== state.filters.severity) return false
    return true
  })
}

export const useWorkbenchStore = create<WorkbenchState>((set, get) => ({
  docId: null,
  filename: '',
  status: '',
  loading: false,
  error: null,
  blocks: [],
  corrections: {},
  order: [],
  filters: { decision: 'all', errorType: 'all', severity: 'all' },
  selectedId: null,
  editingId: null,

  load: async (docId) => {
    set({ loading: true, error: null })
    try {
      const detail = await getDocumentDetail(docId)
      const { corrections, order } = flatten(detail.blocks)
      const firstPending = order.find((id) => corrections[id].decision === 'pending') ?? order[0] ?? null
      set({
        docId,
        filename: detail.filename,
        status: detail.status,
        blocks: detail.blocks,
        corrections,
        order,
        selectedId: firstPending,
        loading: false,
      })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e), loading: false })
    }
  },

  reset: () =>
    set({
      docId: null,
      filename: '',
      status: '',
      blocks: [],
      corrections: {},
      order: [],
      selectedId: null,
      editingId: null,
      error: null,
      filters: { decision: 'all', errorType: 'all', severity: 'all' },
    }),

  setFilter: (key, value) => {
    set((s) => ({ filters: { ...s.filters, [key]: value } }))
    // 筛选变更后把选中项落到第一个可见卡片
    const state = get()
    const visible = filteredIds(state)
    if (state.selectedId === null || !visible.includes(state.selectedId)) {
      set({ selectedId: visible[0] ?? null })
    }
  },

  select: (id) => set({ selectedId: id }),
  setEditing: (id) => set({ editingId: id }),

  moveSelection: (delta) => {
    const state = get()
    const visible = filteredIds(state)
    if (visible.length === 0) return
    const cur = state.selectedId === null ? -1 : visible.indexOf(state.selectedId)
    const next = Math.min(visible.length - 1, Math.max(0, (cur === -1 ? 0 : cur) + delta))
    set({ selectedId: visible[next] })
  },

  decide: async (id, decision, customText) => {
    const prev = get().corrections[id]
    if (!prev) return
    // 乐观更新
    set((s) => ({
      corrections: {
        ...s.corrections,
        [id]: { ...prev, decision, custom_text: customText ?? null, decided_at: new Date().toISOString() },
      },
      editingId: null,
    }))
    try {
      const result = await decideCorrection(id, decision, customText)
      set((s) => ({
        status: result.document_status,
        corrections: {
          ...s.corrections,
          [id]: { ...s.corrections[id], ...result.correction },
        },
      }))
      // 自动前进到下一张待决定卡片
      const state = get()
      const nextPending = filteredIds(state).find((cid) => state.corrections[cid].decision === 'pending')
      if (nextPending !== undefined) set({ selectedId: nextPending })
    } catch (e) {
      set((s) => ({ corrections: { ...s.corrections, [id]: prev } })) // 失败回滚
      toast.error(`决定失败：${e instanceof Error ? e.message : String(e)}`)
    }
  },

  undo: async (id) => {
    const prev = get().corrections[id]
    if (!prev) return
    set((s) => ({
      corrections: {
        ...s.corrections,
        [id]: { ...prev, decision: 'pending', custom_text: null, decided_at: null },
      },
    }))
    try {
      const result = await decideCorrection(id, 'pending')
      set((s) => ({
        status: result.document_status,
        corrections: { ...s.corrections, [id]: { ...s.corrections[id], ...result.correction } },
      }))
    } catch (e) {
      set((s) => ({ corrections: { ...s.corrections, [id]: prev } }))
      toast.error(`撤销失败：${e instanceof Error ? e.message : String(e)}`)
    }
  },

  batch: async (filter, action, label) => {
    const docId = get().docId
    if (!docId) return
    try {
      const result = await batchDecide(docId, filter, action)
      toast.success(`${label}：已处理 ${result.affected} 条`)
      await get().load(docId) // 批量影响面广，直接重载
    } catch (e) {
      toast.error(`${label}失败：${e instanceof Error ? e.message : String(e)}`)
    }
  },
}))

import { create } from 'zustand'

interface AppState {
  /** 当前在审校工作台打开的文档 id */
  currentDocumentId: string | null
  setCurrentDocumentId: (id: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  currentDocumentId: null,
  setCurrentDocumentId: (id) => set({ currentDocumentId: id }),
}))

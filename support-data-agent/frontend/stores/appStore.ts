import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Filters } from '@/types'

interface AppState {
  chatOpen: boolean
  toggleChat: () => void

  filters: Filters
  setFilters: (filters: Partial<Filters>) => void
  resetFilters: () => void

  currentPage: string
  setCurrentPage: (page: string) => void

  activeConfigId: string | null
  setActiveConfigId: (id: string | null) => void

  isInitializing: boolean
  setIsInitializing: (isInitializing: boolean) => void
}

const defaultFilters: Filters = {
  period: 'week',
  products: [],
  topics: [],
  categories: [],
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      chatOpen: false,
      toggleChat: () => set((state) => ({ chatOpen: !state.chatOpen })),

      filters: defaultFilters,
      setFilters: (filters) => set((state) => ({
        filters: { ...state.filters, ...filters }
      })),
      resetFilters: () => set({ filters: defaultFilters }),

      currentPage: 'dashboard',
      setCurrentPage: (page) => set({ currentPage: page }),

      activeConfigId: null,
      setActiveConfigId: (id) => set({ activeConfigId: id }),

      isInitializing: true,
      setIsInitializing: (isInitializing) => set({ isInitializing }),
    }),
    {
      name: 'app-storage',
      partialize: (state) => ({
        activeConfigId: state.activeConfigId,
      }),
    }
  )
)

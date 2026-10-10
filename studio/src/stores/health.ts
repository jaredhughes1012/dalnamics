import { create } from 'zustand'
import { fetchHealth, type HealthResponse } from '@/lib/api'

type HealthState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  data?: HealthResponse
  error?: string
  check: () => Promise<void>
}

export const useHealthStore = create<HealthState>((set) => ({
  status: 'idle',
  check: async () => {
    set({ status: 'loading', error: undefined })
    try {
      set({ status: 'success', data: await fetchHealth() })
    } catch (err) {
      set({ status: 'error', data: undefined, error: err instanceof Error ? err.message : String(err) })
    }
  },
}))

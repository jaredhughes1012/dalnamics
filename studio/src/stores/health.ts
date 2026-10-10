import { create } from 'zustand'
import { publicApi, unwrap } from '@/lib/api/client'
import type { components } from '@/lib/api/schema'

type Health = components['schemas']['Health']

type HealthState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  data?: Health
  error?: string
  check: () => Promise<void>
}

export const useHealthStore = create<HealthState>((set) => ({
  status: 'idle',
  check: async () => {
    set({ status: 'loading', error: undefined })
    try {
      set({ status: 'success', data: unwrap(await publicApi.GET('/healthz')) })
    } catch (err) {
      set({ status: 'error', data: undefined, error: err instanceof Error ? err.message : String(err) })
    }
  },
}))

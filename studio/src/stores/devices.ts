import { create } from 'zustand'
import { api, unwrap, type Device } from '@/lib/api/client'
import { errorMessage } from '@/lib/errors'

type DevicesState = {
  status: 'idle' | 'loading' | 'success' | 'error'
  devices: Device[]
  error?: string
  /** Fetches the signed-in user's devices, newest first. */
  load: () => Promise<void>
}

export const useDevicesStore = create<DevicesState>((set) => ({
  status: 'idle',
  devices: [],
  load: async () => {
    set((s) => ({ status: s.status === 'success' ? 'success' : 'loading' }))
    try {
      set({ status: 'success', devices: unwrap(await api.GET('/devices')), error: undefined })
    } catch (err) {
      set({ status: 'error', error: errorMessage(err) })
    }
  },
}))

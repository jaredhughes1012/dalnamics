import { create } from 'zustand'
import { api, unwrap, type Device } from '@/lib/api/client'
import { errorMessage } from '@/lib/errors'

type DevicesState = {
  /** 'error' while the latest load failed; devices then still holds the last list loaded. */
  status: 'idle' | 'loading' | 'success' | 'error'
  devices: Device[]
  error?: string
  /**
   * Fetches the signed-in user's devices, newest first. When it resolves, the
   * state is at least as fresh as this request: a response that arrives after a
   * newer one is dropped.
   */
  load: () => Promise<void>
}

// Requests started, and the newest one whose result is in the state.
let started = 0
let applied = 0

export const useDevicesStore = create<DevicesState>((set) => ({
  status: 'idle',
  devices: [],
  load: async () => {
    const seq = ++started
    set((s) => ({ status: s.status === 'success' ? 'success' : 'loading' }))
    let next: Partial<DevicesState>
    try {
      next = { status: 'success', devices: unwrap(await api.GET('/devices')), error: undefined }
    } catch (err) {
      next = { status: 'error', error: errorMessage(err) }
    }
    if (seq < applied) return
    applied = seq
    set(next)
  },
}))

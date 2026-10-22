import { create } from 'zustand'
import { api, unwrap, type Device } from '@/lib/api/client'
import { errorMessage } from '@/lib/errors'
import { newestWins, reloadStatus, type LoadStatus } from '@/lib/loads'

type DevicesState = {
  /** 'error' while the latest load failed; devices then still holds the last list loaded. */
  status: LoadStatus
  devices: Device[]
  error?: string
  /**
   * Fetches the signed-in user's devices, newest first. When it resolves, the
   * state is at least as fresh as this request: a response that arrives after a
   * newer one is dropped.
   */
  load: () => Promise<void>
}

const loads = newestWins()

export const useDevicesStore = create<DevicesState>((set) => ({
  status: 'idle',
  devices: [],
  load: async () => {
    const seq = loads.start()
    set((s) => ({ status: reloadStatus(s.status) }))
    let next: Partial<DevicesState>
    try {
      next = { status: 'success', devices: unwrap(await api.GET('/devices')), error: undefined }
    } catch (err) {
      next = { status: 'error', error: errorMessage(err) }
    }
    if (loads.claim(seq)) set(next)
  },
}))

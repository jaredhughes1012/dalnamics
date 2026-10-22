import { create } from 'zustand'
import { api, ApiError, unwrap, type Device } from '@/lib/api/client'
import { errorMessage } from '@/lib/errors'

type DeviceState = {
  /** 'error' while the latest load failed; device then still holds the last one loaded. */
  status: 'idle' | 'loading' | 'success' | 'error'
  /** The ID of the device being shown. */
  id?: string
  device?: Device
  /** The api has no such device for the user (404), or the ID isn't a UUID (400). */
  notFound: boolean
  error?: string
  /**
   * Fetches one of the signed-in user's devices. Reloading the same ID keeps
   * the current device on screen; loading another ID clears it first, so the
   * previous device never shows under the new URL. A response that arrives
   * after a newer one, or for an ID no longer shown, is dropped.
   */
  load: (id: string) => Promise<void>
}

// Requests started, and the newest one whose result is in the state.
let started = 0
let applied = 0

export const useDeviceStore = create<DeviceState>((set, get) => ({
  status: 'idle',
  notFound: false,
  load: async (id) => {
    const seq = ++started
    set((s) =>
      s.id === id
        ? { status: s.status === 'success' ? 'success' : 'loading' }
        : { id, status: 'loading', device: undefined, notFound: false, error: undefined },
    )
    let next: Partial<DeviceState>
    try {
      const device = unwrap(await api.GET('/devices/{id}', { params: { path: { id } } }))
      next = { status: 'success', device, notFound: false, error: undefined }
    } catch (err) {
      next =
        err instanceof ApiError && (err.status === 404 || err.status === 400)
          ? { status: 'success', device: undefined, notFound: true, error: undefined }
          : { status: 'error', error: errorMessage(err) }
    }
    if (seq < applied || get().id !== id) return
    applied = seq
    set(next)
  },
}))

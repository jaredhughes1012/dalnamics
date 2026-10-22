import { useEffect } from 'react'
import { devicesRefreshMs } from '@/lib/config'

/**
 * Calls load on mount, then again ms after each call finishes, until unmount.
 * Scheduling after the previous call finishes means slow requests never pile
 * up. A hidden tab skips refreshes and catches up as soon as it's shown again.
 */
export function useRefresh(load: () => Promise<void>, ms = devicesRefreshMs()) {
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined
    let stopped = false
    const refresh = async () => {
      if (!document.hidden) await load()
      if (!stopped) timer = setTimeout(() => void refresh(), ms)
    }
    const onVisibilityChange = () => {
      if (!document.hidden) void load()
    }
    void refresh()
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      stopped = true
      clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [load, ms])
}

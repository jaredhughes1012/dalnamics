/** A store's load status. 'error' while the latest load failed; the data then still holds the last successful load. */
export type LoadStatus = 'idle' | 'loading' | 'success' | 'error'

/**
 * The status to show while reloading data already on screen. Only the first
 * load is 'loading'. A reload after a failure stays 'error', so data from
 * before the failure is never shown as current while the retry is in flight.
 */
export function reloadStatus(status: LoadStatus): LoadStatus {
  return status === 'idle' ? 'loading' : status
}

/**
 * Orders a store's concurrent loads so that the state is always at least as
 * fresh as the newest result applied: a result that arrives after a newer one
 * is dropped.
 */
export function newestWins() {
  // Loads started, and the newest one whose result is in the state.
  let started = 0
  let applied = 0
  return {
    /** Numbers a new load. */
    start: () => ++started,
    /** Reports whether load seq's result may be applied, and records it as applied if so. */
    claim: (seq: number) => {
      if (seq < applied) return false
      applied = seq
      return true
    },
  }
}

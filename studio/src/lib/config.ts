/** Studio settings read from Vite env vars (VITE_*), fixed at build or dev-server start. */

const DEFAULT_DEVICES_REFRESH_MS = 15_000

/**
 * How often the Devices page and each device's page refresh (VITE_DEVICES_REFRESH_MS, in
 * milliseconds). Unset or invalid values fall back to 15 s. The dev server sets
 * 5 s in .env.development.
 */
export function devicesRefreshMs(env: Partial<ImportMetaEnv> = import.meta.env): number {
  const ms = Number(env.VITE_DEVICES_REFRESH_MS)
  return Number.isFinite(ms) && ms > 0 ? ms : DEFAULT_DEVICES_REFRESH_MS
}

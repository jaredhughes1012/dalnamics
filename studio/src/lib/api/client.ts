import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export type User = components['schemas']['User']
export type Tokens = components['schemas']['Tokens']
export type Session = components['schemas']['Session']
export type ApiErrorBody = components['schemas']['Error']

// Requests go through the Vite dev proxy at /api, which forwards to the Go api.
// The base URL is absolute because openapi-fetch builds Request objects, and
// fetch is resolved per call so tests can stub globalThis.fetch.
const options = {
  baseUrl: `${window.location.origin}/api`,
  fetch: (req: Request) => globalThis.fetch(req),
}

/** Client for endpoints that need no credentials (login, signup, refresh, health). */
export const publicApi = createClient<paths>(options)

/** Client for authenticated endpoints. The auth store installs bearer/refresh middleware on it. */
export const api = createClient<paths>(options)

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, body?: Partial<ApiErrorBody>) {
    super(body?.message ?? `Request failed with status ${status}`)
    this.status = status
    this.code = body?.code ?? 'unknown'
  }
}

/** Unwraps an openapi-fetch result, throwing ApiError on failure. */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.data === undefined || !result.response.ok) {
    throw new ApiError(result.response.status, result.error as Partial<ApiErrorBody> | undefined)
  }
  return result.data
}

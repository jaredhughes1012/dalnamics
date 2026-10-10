// Requests go through the Vite dev proxy at /api, which forwards to the Go api.
const API_BASE = '/api'

export type HealthResponse = {
  status: string
  service: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/healthz`)
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

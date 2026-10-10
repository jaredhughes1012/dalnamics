type Handler = (request: Request) => Response | Promise<Response>

/**
 * Stubs fetch with handlers keyed by "METHOD /path" (path without the /api
 * prefix). Unmatched requests fail the test with a 501. Returns the spy so
 * tests can inspect the requests that were made.
 */
export function mockApi(handlers: Record<string, Handler>) {
  const spy = vi.fn(async (input: RequestInfo | URL) => {
    const request = input instanceof Request ? input : new Request(input)
    const path = new URL(request.url).pathname.replace(/^\/api/, '')
    const handler = handlers[`${request.method} ${path}`]
    if (!handler) {
      return Response.json({ code: 'unmocked', message: `No mock for ${request.method} ${path}` }, { status: 501 })
    }
    return handler(request)
  })
  vi.stubGlobal('fetch', spy)
  return spy
}

export const apiError = (status: number, code: string, message: string) => Response.json({ code, message }, { status })

export const testUser = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'jane@example.com',
  name: 'Jane',
  created_at: '2026-01-01T00:00:00Z',
}

export const testTokens = (n = 1) => ({
  access_token: `access-${n}`,
  refresh_token: `refresh-${n}`,
  token_type: 'Bearer' as const,
  expires_in: 900,
})

export const sessionResponse = (user = testUser) => Response.json({ user, tokens: testTokens() })

/** Paths requested, as "METHOD /path", in order. */
export function requestsOf(spy: ReturnType<typeof mockApi>) {
  return spy.mock.calls.map(([input]) => {
    const request = input as Request
    return `${request.method} ${new URL(request.url).pathname.replace(/^\/api/, '')}`
  })
}

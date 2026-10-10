import { api } from '@/lib/api/client'
import { AUTH_STORAGE_KEY, useAuthStore } from '@/stores/auth'
import { apiError, mockApi, requestsOf, testTokens, testUser } from '@/test/api'

function signInWith(tokens = testTokens()) {
  useAuthStore.setState({ user: testUser, tokens })
}

/** /me accepts only access-2, so access-1 forces a refresh. */
function meRequiringRefresh() {
  return (req: Request) =>
    req.headers.get('Authorization') === 'Bearer access-2'
      ? Response.json(testUser)
      : apiError(401, 'invalid_token', 'invalid or expired token')
}

describe('auth store', () => {
  it('persists the session to localStorage', () => {
    signInWith()

    const stored = JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY)!)
    expect(stored.state).toEqual({ user: testUser, tokens: testTokens() })
  })

  it('refreshes once on 401 and retries', async () => {
    signInWith()
    const fetch = mockApi({
      'GET /me': meRequiringRefresh(),
      'POST /auth/refresh': async (req) => {
        expect(await req.json()).toEqual({ refresh_token: 'refresh-1' })
        return Response.json(testTokens(2))
      },
    })

    const { data } = await api.GET('/me')

    expect(data).toEqual(testUser)
    expect(useAuthStore.getState().tokens).toEqual(testTokens(2))
    expect(requestsOf(fetch)).toEqual(['GET /me', 'POST /auth/refresh', 'GET /me'])
  })

  it('shares one refresh between concurrent 401s', async () => {
    signInWith()
    const fetch = mockApi({ 'GET /me': meRequiringRefresh(), 'POST /auth/refresh': () => Response.json(testTokens(2)) })

    const results = await Promise.all([api.GET('/me'), api.GET('/me'), api.GET('/me')])

    expect(results.map((r) => r.data)).toEqual([testUser, testUser, testUser])
    expect(requestsOf(fetch).filter((r) => r === 'POST /auth/refresh')).toHaveLength(1)
  })

  it('signs out when the refresh token is rejected', async () => {
    signInWith()
    mockApi({
      'GET /me': meRequiringRefresh(),
      'POST /auth/refresh': () => apiError(401, 'invalid_token', 'invalid or expired token'),
    })

    const { response } = await api.GET('/me')

    expect(response.status).toBe(401)
    expect(useAuthStore.getState().tokens).toBeUndefined()
    expect(useAuthStore.getState().user).toBeUndefined()
  })
})

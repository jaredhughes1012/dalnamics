import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Middleware } from 'openapi-fetch'
import { api, publicApi, unwrap, type Session, type Tokens, type User } from '@/lib/api/client'

export const AUTH_STORAGE_KEY = 'dalnamics-auth'

type AuthState = {
  user?: User
  tokens?: Tokens
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, name: string, password: string) => Promise<void>
  devLogin: (email: string) => Promise<void>
  logout: () => Promise<void>
  /** Rotates the token pair. Resolves false (and signs out) if the session is gone. */
  refresh: () => Promise<boolean>
}

let refreshing: Promise<boolean> | undefined

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => {
      const start = (session: Session) => set({ user: session.user, tokens: session.tokens })

      return {
        login: async (email, password) => {
          start(unwrap(await publicApi.POST('/auth/login', { body: { email, password } })))
        },
        signup: async (email, name, password) => {
          start(unwrap(await publicApi.POST('/auth/signup', { body: { email, name, password } })))
        },
        devLogin: async (email) => {
          start(unwrap(await publicApi.POST('/auth/dev-login', { body: { email } })))
        },
        logout: async () => {
          try {
            await api.POST('/auth/logout')
          } finally {
            set({ user: undefined, tokens: undefined })
          }
        },
        refresh: () => {
          // Concurrent 401s share one refresh, since each refresh token is single use.
          refreshing ??= (async () => {
            const refreshToken = get().tokens?.refresh_token
            if (!refreshToken) return false
            const { data } = await publicApi.POST('/auth/refresh', { body: { refresh_token: refreshToken } })
            if (!data) {
              set({ user: undefined, tokens: undefined })
              return false
            }
            set({ tokens: data })
            return true
          })().finally(() => {
            refreshing = undefined
          })
          return refreshing
        },
      }
    },
    {
      name: AUTH_STORAGE_KEY,
      partialize: ({ user, tokens }) => ({ user, tokens }),
    },
  ),
)

export const isAuthenticated = () => useAuthStore.getState().tokens !== undefined

// Retry bodies must be captured before the original request is sent.
const pending = new Map<string, Request>()

function withBearer(request: Request, token: string) {
  request.headers.set('Authorization', `Bearer ${token}`)
  return request
}

/** Adds the access token to requests and, on a 401, refreshes once and retries. */
export const authMiddleware: Middleware = {
  onRequest({ request, id }) {
    const token = useAuthStore.getState().tokens?.access_token
    if (!token) return request
    pending.set(id, request.clone())
    return withBearer(request, token)
  },
  async onResponse({ response, id }) {
    const retry = pending.get(id)
    pending.delete(id)
    if (response.status !== 401 || !retry) return response

    if (!(await useAuthStore.getState().refresh())) return response
    return globalThis.fetch(withBearer(retry, useAuthStore.getState().tokens!.access_token))
  },
  onError({ id }) {
    pending.delete(id)
  },
}

api.use(authMiddleware)

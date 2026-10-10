import { useEffect } from 'react'
import { createFileRoute, Outlet, redirect, useRouter } from '@tanstack/react-router'
import { isAuthenticated, useAuthStore } from '@/stores/auth'

/** Layout for routes that require a signed-in user. */
export const Route = createFileRoute('/_authed')({
  beforeLoad: ({ location }) => {
    if (!isAuthenticated()) {
      throw redirect({ to: '/login', search: { redirect: location.href } })
    }
  },
  component: AuthedLayout,
})

function AuthedLayout() {
  // Sends the user to login if their session ends while on the page (logout,
  // failed refresh, or another tab), returning them here once signed back in.
  const signedIn = useAuthStore((s) => s.tokens !== undefined)
  const router = useRouter()
  useEffect(() => {
    if (!signedIn) void router.navigate({ to: '/login', search: { redirect: router.state.location.href } })
  }, [signedIn, router])
  return signedIn ? <Outlet /> : null
}

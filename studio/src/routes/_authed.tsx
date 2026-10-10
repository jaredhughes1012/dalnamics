import { createFileRoute, Navigate, Outlet, redirect } from '@tanstack/react-router'
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
  // Sends the user to login if their session ends while on the page (logout, failed refresh).
  const signedIn = useAuthStore((s) => s.tokens !== undefined)
  if (!signedIn) return <Navigate to="/login" />
  return <Outlet />
}

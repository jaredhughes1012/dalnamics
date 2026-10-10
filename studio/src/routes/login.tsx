import { createFileRoute, Link, redirect, useRouter } from '@tanstack/react-router'
import { AuthCard } from '@/components/auth-card'
import { CenteredPage } from '@/components/centered-page'
import { DevLoginButtons } from '@/components/dev-login-buttons'
import { LoginForm } from '@/components/login-form'
import { safeRedirect } from '@/lib/redirect'
import { isAuthenticated } from '@/stores/auth'

type LoginSearch = { redirect?: string }

export const Route = createFileRoute('/login')({
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    redirect: typeof search.redirect === 'string' ? search.redirect : undefined,
  }),
  beforeLoad: ({ search }) => {
    if (isAuthenticated()) throw redirect({ href: safeRedirect(search.redirect) })
  },
  component: Login,
})

function Login() {
  const { redirect: target } = Route.useSearch()
  const router = useRouter()
  const onSuccess = () => router.history.push(safeRedirect(target))

  return (
    <CenteredPage>
      <AuthCard
        title="Log in"
        description="Log in to dalnamics studio."
        footer={
          <span>
            No account?{' '}
            <Link to="/signup" search={{ redirect: target }} className="underline">
              Create one
            </Link>
          </span>
        }
      >
        <LoginForm onSuccess={onSuccess} />
        <DevLoginButtons onSuccess={onSuccess} />
      </AuthCard>
    </CenteredPage>
  )
}

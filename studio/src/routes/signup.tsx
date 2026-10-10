import { createFileRoute, Link, redirect, useRouter } from '@tanstack/react-router'
import { AuthCard } from '@/components/auth-card'
import { SignupForm } from '@/components/signup-form'
import { safeRedirect } from '@/lib/redirect'
import { isAuthenticated } from '@/stores/auth'

type SignupSearch = { redirect?: string }

export const Route = createFileRoute('/signup')({
  validateSearch: (search: Record<string, unknown>): SignupSearch => ({
    redirect: typeof search.redirect === 'string' ? search.redirect : undefined,
  }),
  beforeLoad: ({ search }) => {
    if (isAuthenticated()) throw redirect({ href: safeRedirect(search.redirect) })
  },
  component: Signup,
})

function Signup() {
  const { redirect: target } = Route.useSearch()
  const router = useRouter()

  return (
    <AuthCard
      title="Create an account"
      description="Sign up with your email."
      footer={
        <span>
          Have an account?{' '}
          <Link to="/login" search={{ redirect: target }} className="underline">
            Log in
          </Link>
        </span>
      }
    >
      <SignupForm onSuccess={() => router.history.push(safeRedirect(target))} />
    </AuthCard>
  )
}

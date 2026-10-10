import { createRootRoute, Link, Outlet, type ErrorComponentProps } from '@tanstack/react-router'
import { AuthCard } from '@/components/auth-card'
import { CenteredPage } from '@/components/centered-page'
import { FormError } from '@/components/form-error'
import { Button } from '@/components/ui/button'
import { errorMessage } from '@/lib/errors'

export const Route = createRootRoute({
  component: Outlet,
  notFoundComponent: NotFound,
  errorComponent: RouteError,
})

function NotFound() {
  return (
    <CenteredPage>
      <AuthCard title="Page not found" description="There's nothing at this address.">
        <Button asChild>
          <Link to="/">Go to dashboard</Link>
        </Button>
      </AuthCard>
    </CenteredPage>
  )
}

function RouteError({ error, reset }: ErrorComponentProps) {
  return (
    <CenteredPage>
      <AuthCard title="Something went wrong" description="This page failed to load.">
        <FormError message={errorMessage(error)} />
        <Button onClick={reset}>Try again</Button>
      </AuthCard>
    </CenteredPage>
  )
}

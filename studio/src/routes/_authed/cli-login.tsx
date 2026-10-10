import { createFileRoute } from '@tanstack/react-router'
import { CliAuthorizeCard, type CliLoginParams } from '@/components/cli-authorize-card'

export const Route = createFileRoute('/_authed/cli-login')({
  validateSearch: (search: Record<string, unknown>): CliLoginParams => ({
    redirect_uri: typeof search.redirect_uri === 'string' ? search.redirect_uri : undefined,
    code_challenge: typeof search.code_challenge === 'string' ? search.code_challenge : undefined,
    state: typeof search.state === 'string' ? search.state : undefined,
  }),
  component: CliLogin,
})

function CliLogin() {
  return <CliAuthorizeCard {...Route.useSearch()} />
}

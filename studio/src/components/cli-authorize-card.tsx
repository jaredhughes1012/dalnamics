import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { AuthCard } from '@/components/auth-card'
import { FormError } from '@/components/form-error'
import { api, unwrap } from '@/lib/api/client'
import { errorMessage } from '@/lib/errors'
import { navigation } from '@/lib/navigation'
import { isLoopbackRedirect } from '@/lib/redirect'
import { useAuthStore } from '@/stores/auth'

export type CliLoginParams = {
  redirect_uri?: string
  code_challenge?: string
  state?: string
}

function callbackURL(redirectURI: string, params: Record<string, string>) {
  const url = new URL(redirectURI)
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v)
  return url.toString()
}

export function CliAuthorizeCard({ redirect_uri, code_challenge, state }: CliLoginParams) {
  const user = useAuthStore((s) => s.user)
  const [error, setError] = useState<string>()
  const [done, setDone] = useState<'approved' | 'denied'>()

  if (!redirect_uri || !code_challenge || !state || !isLoopbackRedirect(redirect_uri)) {
    return (
      <AuthCard title="Invalid cli login link" description="Run `cli auth login` again to get a new link.">
        <FormError message="This link is missing or has invalid parameters." />
      </AuthCard>
    )
  }

  if (done) {
    return (
      <AuthCard
        title={done === 'approved' ? 'cli authorized' : 'cli login cancelled'}
        description="You can close this tab and return to your terminal."
      >
        {null}
      </AuthCard>
    )
  }

  async function authorize() {
    setError(undefined)
    try {
      const { code } = unwrap(await api.POST('/auth/cli/authorize', { body: { code_challenge: code_challenge!, redirect_uri: redirect_uri! } }))
      setDone('approved')
      navigation.assign(callbackURL(redirect_uri!, { code, state: state! }))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  function deny() {
    setDone('denied')
    navigation.assign(callbackURL(redirect_uri!, { error: 'access_denied', state: state! }))
  }

  return (
    <AuthCard title="Authorize the cli?" description={`The cli will be signed in as ${user?.name} (${user?.email}).`}>
      <FormError message={error} />
      <div className="flex gap-2">
        <Button className="flex-1" onClick={() => void authorize()}>
          Authorize
        </Button>
        <Button className="flex-1" variant="outline" onClick={deny}>
          Cancel
        </Button>
      </div>
    </AuthCard>
  )
}

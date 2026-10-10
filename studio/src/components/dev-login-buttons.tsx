import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { FormError } from '@/components/form-error'
import { publicApi } from '@/lib/api/client'
import { errorMessage } from '@/lib/errors'
import { useAuthStore } from '@/stores/auth'

/** One-click login for DEV_EMAILS users. Renders nothing unless the api runs with DEBUG=true. */
export function DevLoginButtons({ onSuccess }: { onSuccess: () => void }) {
  const devLogin = useAuthStore((s) => s.devLogin)
  const [emails, setEmails] = useState<string[]>([])
  const [error, setError] = useState<string>()

  useEffect(() => {
    let cancelled = false
    publicApi
      .GET('/auth/dev-users')
      .then(({ data }) => {
        if (!cancelled && data) setEmails(data.emails)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  if (emails.length === 0) return null

  async function handleClick(email: string) {
    setError(undefined)
    try {
      await devLogin(email)
      onSuccess()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <section aria-label="Dev users" className="flex flex-col gap-2 border-t pt-4">
      <p className="text-sm text-muted-foreground">Dev users</p>
      <FormError message={error} />
      {emails.map((email) => (
        <Button key={email} variant="outline" onClick={() => void handleClick(email)}>
          Continue as {email}
        </Button>
      ))}
    </section>
  )
}

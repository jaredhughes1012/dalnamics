import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealthStore } from '@/stores/health'

export function HealthCard() {
  const { status, data, error, check } = useHealthStore()

  useEffect(() => {
    void check()
  }, [check])

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Studio</CardTitle>
        <CardDescription>API health check</CardDescription>
      </CardHeader>
      <CardContent role="status">
        {status === 'loading' && <p>Checking…</p>}
        {status === 'success' && data && (
          <p className="text-green-600">
            Success: {data.service} is {data.status}
          </p>
        )}
        {status === 'error' && <p className="text-destructive">Unreachable: {error}</p>}
      </CardContent>
      <CardFooter>
        <Button onClick={() => void check()} disabled={status === 'loading'}>
          Check again
        </Button>
      </CardFooter>
    </Card>
  )
}

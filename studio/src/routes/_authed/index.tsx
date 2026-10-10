import { createFileRoute } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { HealthCard } from '@/components/health-card'
import { useAuthStore } from '@/stores/auth'

export const Route = createFileRoute('/_authed/')({
  component: Home,
})

function Home() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  return (
    <div className="flex w-full max-w-sm flex-col gap-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Hello, {user?.name}</h1>
          <p className="text-sm text-muted-foreground">{user?.email}</p>
        </div>
        <Button variant="outline" onClick={() => void logout()}>
          Log out
        </Button>
      </header>
      <HealthCard />
    </div>
  )
}

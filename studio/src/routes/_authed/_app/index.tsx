import { createFileRoute } from '@tanstack/react-router'
import { HealthCard } from '@/components/health-card'
import { useAuthStore } from '@/stores/auth'

export const Route = createFileRoute('/_authed/_app/')({
  component: Dashboard,
})

function Dashboard() {
  const user = useAuthStore((s) => s.user)

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">Hello, {user?.name}</h1>
        <p className="text-sm text-muted-foreground">Dashboard</p>
      </header>
      <HealthCard />
    </div>
  )
}

import { createRootRoute, Outlet } from '@tanstack/react-router'

export const Route = createRootRoute({
  component: () => (
    <main className="flex min-h-svh items-center justify-center bg-background p-6 text-foreground">
      <Outlet />
    </main>
  ),
})

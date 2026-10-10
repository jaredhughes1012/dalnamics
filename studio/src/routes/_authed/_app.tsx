import { createFileRoute, Outlet } from '@tanstack/react-router'
import { NavRail } from '@/components/nav-rail'

/** App shell for signed-in pages: nav rail beside the page content. */
export const Route = createFileRoute('/_authed/_app')({
  component: AppLayout,
})

function AppLayout() {
  return (
    <div className="flex min-h-svh">
      <NavRail />
      <main className="min-w-0 flex-1 p-6 md:p-8">
        <Outlet />
      </main>
    </div>
  )
}

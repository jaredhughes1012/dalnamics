import { Link } from '@tanstack/react-router'
import { Cpu, Hexagon, LayoutDashboard, type LucideIcon } from 'lucide-react'
import { AccountMenu } from '@/components/account-menu'

/** exact: active only on the path itself, not on the pages below it. */
type NavItem = { to: '/' | '/devices'; label: string; icon: LucideIcon; exact: boolean }

const items: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/devices', label: 'Devices', icon: Cpu, exact: false },
]

/** Narrow vertical navigation: logo, page links, and the account menu at the bottom. */
export function NavRail() {
  return (
    <nav
      aria-label="Main"
      className="sticky top-0 flex h-svh w-20 shrink-0 flex-col items-center gap-6 border-r border-sidebar-border bg-sidebar py-4 text-sidebar-foreground"
    >
      <Link
        to="/"
        aria-label="dalnamics"
        className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground outline-none focus-visible:ring-3 focus-visible:ring-sidebar-ring/50"
      >
        <Hexagon className="size-5" />
      </Link>
      <ul className="flex flex-1 flex-col items-center gap-3">
        {items.map((item) => (
          <li key={item.to}>
            <NavRailLink {...item} />
          </li>
        ))}
      </ul>
      <AccountMenu />
    </nav>
  )
}

function NavRailLink({ to, label, icon: Icon, exact }: NavItem) {
  return (
    <Link
      to={to}
      activeOptions={{ exact }}
      className="group flex w-16 flex-col items-center gap-1 text-xs font-medium text-muted-foreground outline-none hover:text-sidebar-foreground data-[status=active]:text-sidebar-accent-foreground"
    >
      <span className="flex h-8 w-14 items-center justify-center rounded-full transition-colors group-hover:bg-sidebar-accent group-focus-visible:ring-3 group-focus-visible:ring-sidebar-ring/50 group-data-[status=active]:bg-sidebar-accent">
        <Icon className="size-5" />
      </span>
      {label}
    </Link>
  )
}

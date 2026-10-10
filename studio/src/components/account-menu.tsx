import { LogOut, Monitor, Moon, Sun, type LucideIcon } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore, type Theme } from '@/stores/theme'

const themes: { value: Theme; label: string; icon: LucideIcon }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

function initials(name = '') {
  // Array.from splits by code point, so characters outside the BMP stay whole.
  const parts = name.trim().split(/\s+/).filter(Boolean).map((part) => Array.from(part)[0])
  return ((parts[0] ?? '') + (parts.length > 1 ? parts.at(-1) : '')).toUpperCase() || '?'
}

/** Account circle that opens the signed-in user's menu: theme and log out. */
export function AccountMenu() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const theme = useThemeStore((s) => s.theme)
  const setTheme = useThemeStore((s) => s.setTheme)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account"
        className="rounded-full outline-none focus-visible:ring-3 focus-visible:ring-sidebar-ring/50"
      >
        <Avatar size="lg">
          <AvatarFallback>{initials(user?.name)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="right" align="end" sideOffset={12} className="w-56">
        <DropdownMenuLabel className="flex flex-col text-sm">
          <span className="truncate text-foreground">{user?.name}</span>
          <span className="truncate text-xs font-normal">{user?.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuLabel>Theme</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={theme} onValueChange={(value) => setTheme(value as Theme)}>
            {themes.map(({ value, label, icon: Icon }) => (
              <DropdownMenuRadioItem key={value} value={value}>
                <Icon />
                {label}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        {/* logout clears the session even when the api call fails, so the error needs no handling here. */}
        <DropdownMenuItem onSelect={() => void logout().catch(() => {})}>
          <LogOut />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

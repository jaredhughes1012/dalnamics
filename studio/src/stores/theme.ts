import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// index.html reads this key and the persisted shape ({ state: { theme } }) to
// apply the theme before first paint; keep the two in sync.
export const THEME_STORAGE_KEY = 'dalnamics-theme'

/** A theme choice; 'system' follows the OS color scheme. */
export type Theme = 'light' | 'dark' | 'system'

type ThemeState = {
  theme: Theme
  setTheme: (theme: Theme) => void
}

const DARK_QUERY = '(prefers-color-scheme: dark)'

/** The color scheme a theme renders in, falling back to light when the OS preference is unknown. */
export function resolveTheme(theme: Theme): 'light' | 'dark' {
  if (theme !== 'system') return theme
  return typeof matchMedia === 'function' && matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme) {
  const scheme = resolveTheme(theme)
  document.documentElement.classList.toggle('dark', scheme === 'dark')
  document.documentElement.style.colorScheme = scheme
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'system',
      setTheme: (theme) => set({ theme }),
    }),
    { name: THEME_STORAGE_KEY, partialize: ({ theme }) => ({ theme }) },
  ),
)

applyTheme(useThemeStore.getState().theme)
useThemeStore.subscribe(({ theme }, prev) => {
  if (theme !== prev.theme) applyTheme(theme)
})

// Follow OS scheme changes and theme changes made in other tabs.
if (typeof matchMedia === 'function') {
  matchMedia(DARK_QUERY).addEventListener('change', () => applyTheme(useThemeStore.getState().theme))
}
window.addEventListener('storage', (event) => {
  if (event.key === THEME_STORAGE_KEY || event.key === null) void useThemeStore.persist.rehydrate()
})

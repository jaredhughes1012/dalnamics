import { resolveTheme, useThemeStore } from '@/stores/theme'

function stubPrefersDark(matches: boolean) {
  vi.stubGlobal('matchMedia', (query: string) => ({ matches: matches && query === '(prefers-color-scheme: dark)' }))
}

describe('theme', () => {
  it('follows the OS by default', () => {
    expect(useThemeStore.getState().theme).toBe('system')
    stubPrefersDark(true)
    expect(resolveTheme('system')).toBe('dark')
    stubPrefersDark(false)
    expect(resolveTheme('system')).toBe('light')
  })

  it('falls back to light when the OS preference is unknown', () => {
    vi.stubGlobal('matchMedia', undefined)
    expect(resolveTheme('system')).toBe('light')
  })

  it('applies the chosen theme to the document', () => {
    useThemeStore.getState().setTheme('dark')
    expect(document.documentElement).toHaveClass('dark')
    expect(document.documentElement.style.colorScheme).toBe('dark')

    useThemeStore.getState().setTheme('light')
    expect(document.documentElement).not.toHaveClass('dark')
  })
})

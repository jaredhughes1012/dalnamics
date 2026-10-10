import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { useAuthStore } from '@/stores/auth'
import { useHealthStore } from '@/stores/health'
import { useThemeStore } from '@/stores/theme'

const initialAuth = useAuthStore.getState()
const initialHealth = useHealthStore.getState()
const initialTheme = useThemeStore.getState()

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState(initialAuth, true)
  useHealthStore.setState(initialHealth, true)
  useThemeStore.setState(initialTheme, true)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

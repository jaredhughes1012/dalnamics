import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { useAuthStore } from '@/stores/auth'
import { useDevicesStore } from '@/stores/devices'
import { useHealthStore } from '@/stores/health'
import { useThemeStore } from '@/stores/theme'

// The first render of a code-split route transforms its module cold, which can
// take over the default 1 s on CI runners.
configure({ asyncUtilTimeout: 3000 })

const initialAuth = useAuthStore.getState()
const initialDevices = useDevicesStore.getState()
const initialHealth = useHealthStore.getState()
const initialTheme = useThemeStore.getState()

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState(initialAuth, true)
  useDevicesStore.setState(initialDevices, true)
  useHealthStore.setState(initialHealth, true)
  useThemeStore.setState(initialTheme, true)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

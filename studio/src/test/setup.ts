import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { useAuthStore } from '@/stores/auth'
import { useHealthStore } from '@/stores/health'

const initialAuth = useAuthStore.getState()
const initialHealth = useHealthStore.getState()

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState(initialAuth, true)
  useHealthStore.setState(initialHealth, true)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

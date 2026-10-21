import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { apiError, mockApi, sessionResponse, testUser } from '@/test/api'
import { renderRoute } from '@/test/render'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

async function signIn() {
  mockApi({
    'POST /auth/login': () => sessionResponse(),
    'GET /healthz': () => Response.json({ status: 'ok', service: 'api' }),
  })
  await useAuthStore.getState().login('jane@example.com', 'hunter22')
}

describe('dashboard', () => {
  it('shows the api health in the app shell', async () => {
    await signIn()
    renderRoute('/')

    expect(await screen.findByRole('heading', { name: 'Hello, Jane' })).toBeInTheDocument()
    expect(await screen.findByText('Success: api is ok')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Main' })
    expect(nav).toContainElement(screen.getByRole('link', { name: 'Dashboard' }))
    expect(nav).toContainElement(screen.getByRole('link', { name: 'Devices' }))
    expect(screen.getByRole('link', { name: 'Devices' })).toHaveAttribute('href', '/devices')
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'dalnamics' })).toHaveAttribute('href', '/')
  })

  it('switches theme from the account menu', async () => {
    const user = userEvent.setup()
    await signIn()
    renderRoute('/')

    await user.click(await screen.findByRole('button', { name: 'Account' }))
    expect(screen.getByRole('menu')).toHaveTextContent('jane@example.com')
    expect(screen.getByRole('menuitemradio', { name: 'System' })).toBeChecked()
    await user.click(screen.getByRole('menuitemradio', { name: 'Dark' }))

    expect(useThemeStore.getState().theme).toBe('dark')
    expect(document.documentElement).toHaveClass('dark')
  })
})

describe('account menu', () => {
  it('shows initials from the first and last name', async () => {
    mockApi({
      'POST /auth/login': () => sessionResponse({ ...testUser, name: '𝓙ane van Doe' }),
      'GET /healthz': () => Response.json({ status: 'ok', service: 'api' }),
    })
    await useAuthStore.getState().login('jane@example.com', 'hunter22')
    renderRoute('/')

    expect(await screen.findByRole('button', { name: 'Account' })).toHaveTextContent(/^𝓙D$/)
  })

  it('signs out even when the api is unreachable', async () => {
    const user = userEvent.setup()
    await signIn()
    mockApi({
      'POST /auth/logout': () => Promise.reject(new TypeError('Failed to fetch')),
      'GET /auth/dev-users': () => apiError(404, 'not_found', 'not found'),
      'GET /healthz': () => Response.json({ status: 'ok', service: 'api' }),
    })
    renderRoute('/')

    await user.click(await screen.findByRole('button', { name: 'Account' }))
    await user.click(screen.getByRole('menuitem', { name: 'Log out' }))

    expect(await screen.findByRole('button', { name: 'Log in' })).toBeInTheDocument()
    expect(useAuthStore.getState().tokens).toBeUndefined()
  })
})

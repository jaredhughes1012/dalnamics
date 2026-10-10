import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { apiError, mockApi, sessionResponse, testUser } from '@/test/api'
import { renderRoute } from '@/test/render'
import { useAuthStore } from '@/stores/auth'

const healthy = () => Response.json({ status: 'ok', service: 'api' })
const noDevUsers = () => apiError(404, 'not_found', 'not found')

describe('login', () => {
  it('redirects signed-out users to login', async () => {
    mockApi({ 'GET /auth/dev-users': noDevUsers })
    const { router } = renderRoute('/')

    expect(await screen.findByRole('button', { name: 'Log in' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
  })

  it('logs in and lands on home', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /auth/dev-users': noDevUsers,
      'POST /auth/login': async (req) => {
        expect(await req.json()).toEqual({ email: 'jane@example.com', password: 'hunter22' })
        return sessionResponse()
      },
      'GET /healthz': healthy,
    })
    renderRoute('/login')

    await user.type(await screen.findByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter22')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('heading', { name: 'Hello, Jane' })).toBeInTheDocument()
    expect(useAuthStore.getState().tokens?.access_token).toBe('access-1')
  })

  it('returns to the page that required login', async () => {
    const user = userEvent.setup()
    mockApi({ 'GET /auth/dev-users': noDevUsers, 'POST /auth/login': () => sessionResponse() })
    const { router } = renderRoute('/cli-login?redirect_uri=http%3A%2F%2F127.0.0.1%3A5555%2Fcallback&code_challenge=c&state=s')

    await user.type(await screen.findByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('Password'), 'hunter22')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('button', { name: 'Authorize' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/cli-login')
  })

  it('shows the api error on bad credentials', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /auth/dev-users': noDevUsers,
      'POST /auth/login': () => apiError(401, 'invalid_credentials', 'invalid email or password'),
    })
    renderRoute('/login')

    await user.type(await screen.findByLabelText('Email'), 'jane@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByText('invalid email or password')).toBeInTheDocument()
    expect(useAuthStore.getState().tokens).toBeUndefined()
  })

  it('hides dev users when dev login is disabled', async () => {
    mockApi({ 'GET /auth/dev-users': noDevUsers })
    renderRoute('/login')

    await screen.findByRole('button', { name: 'Log in' })
    expect(screen.queryByRole('region', { name: 'Dev users' })).not.toBeInTheDocument()
  })

  it('logs in as a dev user with one click', async () => {
    const user = userEvent.setup()
    const dev = { ...testUser, email: 'dev@dalnamics.local', name: 'dev' }
    mockApi({
      'GET /auth/dev-users': () => Response.json({ emails: ['dev@dalnamics.local'] }),
      'POST /auth/dev-login': () => sessionResponse(dev),
      'GET /healthz': healthy,
    })
    renderRoute('/login')

    await user.click(await screen.findByRole('button', { name: 'Continue as dev@dalnamics.local' }))

    expect(await screen.findByRole('heading', { name: 'Hello, dev' })).toBeInTheDocument()
  })

  it('logs out', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /auth/dev-users': noDevUsers,
      'POST /auth/login': () => sessionResponse(),
      'POST /auth/logout': () => new Response(null, { status: 204 }),
      'GET /healthz': healthy,
    })
    await useAuthStore.getState().login('jane@example.com', 'hunter22')
    renderRoute('/')

    await user.click(await screen.findByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('button', { name: 'Log in' })).toBeInTheDocument()
    expect(useAuthStore.getState().tokens).toBeUndefined()
  })
})

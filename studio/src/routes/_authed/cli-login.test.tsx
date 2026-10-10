import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { navigation } from '@/lib/navigation'
import { mockApi, sessionResponse } from '@/test/api'
import { renderRoute } from '@/test/render'
import { useAuthStore } from '@/stores/auth'

const redirectURI = 'http://127.0.0.1:5555/callback'
const cliLoginPath = (redirect = redirectURI) =>
  `/cli-login?${new URLSearchParams({ redirect_uri: redirect, code_challenge: 'challenge', state: 'xyz' })}`

async function signIn() {
  mockApi({ 'POST /auth/login': () => sessionResponse() })
  await useAuthStore.getState().login('jane@example.com', 'hunter22')
}

describe('cli login', () => {
  it('authorizes the cli and redirects to its callback', async () => {
    const user = userEvent.setup()
    await signIn()
    const assign = vi.spyOn(navigation, 'assign').mockImplementation(() => {})
    mockApi({
      'POST /auth/cli/authorize': async (req) => {
        expect(req.headers.get('Authorization')).toBe('Bearer access-1')
        expect(await req.json()).toEqual({ code_challenge: 'challenge', redirect_uri: redirectURI })
        return Response.json({ code: 'the-code' })
      },
    })
    renderRoute(cliLoginPath())

    expect(await screen.findByText(/signed in as Jane \(jane@example.com\)/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Authorize' }))

    expect(await screen.findByText('cli authorized')).toBeInTheDocument()
    expect(assign).toHaveBeenCalledWith(`${redirectURI}?code=the-code&state=xyz`)
  })

  it('reports cancellation to the cli', async () => {
    const user = userEvent.setup()
    await signIn()
    const assign = vi.spyOn(navigation, 'assign').mockImplementation(() => {})
    renderRoute(cliLoginPath())

    await user.click(await screen.findByRole('button', { name: 'Cancel' }))

    expect(assign).toHaveBeenCalledWith(`${redirectURI}?error=access_denied&state=xyz`)
  })

  it('refuses to redirect anywhere but loopback', async () => {
    await signIn()
    renderRoute(cliLoginPath('https://evil.example.com/callback'))

    expect(await screen.findByText('Invalid cli login link')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Authorize' })).not.toBeInTheDocument()
  })
})

import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { apiError, mockApi, requestsOf, sessionResponse } from '@/test/api'
import { renderRoute } from '@/test/render'

async function fillSignup(password: string) {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Name'), 'Jane')
  await user.type(screen.getByLabelText('Email'), 'jane@example.com')
  await user.type(screen.getByLabelText('Password'), password)
  await user.click(screen.getByRole('button', { name: 'Create account' }))
}

describe('signup', () => {
  it('creates an account and lands on home', async () => {
    mockApi({
      'POST /auth/signup': async (req) => {
        expect(await req.json()).toEqual({ email: 'jane@example.com', name: 'Jane', password: 'hunter22' })
        return sessionResponse()
      },
      'GET /healthz': () => Response.json({ status: 'ok', service: 'api' }),
    })
    renderRoute('/signup')

    await fillSignup('hunter22')

    expect(await screen.findByRole('heading', { name: 'Hello, Jane' })).toBeInTheDocument()
  })

  it('validates password length before calling the api', async () => {
    const fetch = mockApi({})
    renderRoute('/signup')

    await fillSignup('short')

    expect(await screen.findByText('Password must be at least 8 characters')).toBeInTheDocument()
    expect(requestsOf(fetch)).toEqual([])
  })

  it('shows a taken email', async () => {
    mockApi({ 'POST /auth/signup': () => apiError(409, 'email_taken', 'an account with that email already exists') })
    renderRoute('/signup')

    await fillSignup('hunter22')

    expect(await screen.findByText('an account with that email already exists')).toBeInTheDocument()
  })
})

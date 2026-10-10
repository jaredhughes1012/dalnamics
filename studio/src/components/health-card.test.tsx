import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HealthCard } from '@/components/health-card'
import { useHealthStore } from '@/stores/health'

const initialState = useHealthStore.getState()

function mockFetch(...responses: Response[]) {
  const fn = vi.fn<typeof fetch>()
  for (const res of responses) fn.mockResolvedValueOnce(res)
  vi.stubGlobal('fetch', fn)
  return fn
}

const ok = () => Response.json({ status: 'ok', service: 'api' })

describe('HealthCard', () => {
  beforeEach(() => {
    useHealthStore.setState(initialState, true)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows success when the api is healthy', async () => {
    const fetch = mockFetch(ok())
    render(<HealthCard />)

    expect(await screen.findByText('Success: api is ok')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/healthz')
  })

  it('shows an error when the api is unreachable', async () => {
    mockFetch(new Response(null, { status: 503, statusText: 'Service Unavailable' }))
    render(<HealthCard />)

    expect(await screen.findByText(/Unreachable: Health check failed: 503/)).toBeInTheDocument()
  })

  it('re-checks when the button is clicked', async () => {
    const user = userEvent.setup()
    const fetch = mockFetch(new Response(null, { status: 503 }), ok())
    render(<HealthCard />)
    await screen.findByText(/Unreachable/)

    await user.click(screen.getByRole('button', { name: 'Check again' }))

    expect(await screen.findByText('Success: api is ok')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})

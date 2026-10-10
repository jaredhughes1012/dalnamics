import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { HealthCard } from '@/components/health-card'
import { mockApi, requestsOf } from '@/test/api'

const ok = () => Response.json({ status: 'ok', service: 'api' })

describe('HealthCard', () => {
  it('shows success when the api is healthy', async () => {
    const fetch = mockApi({ 'GET /healthz': ok })
    render(<HealthCard />)

    expect(await screen.findByText('Success: api is ok')).toBeInTheDocument()
    expect(requestsOf(fetch)).toEqual(['GET /healthz'])
  })

  it('shows an error when the api is unreachable', async () => {
    mockApi({ 'GET /healthz': () => new Response(null, { status: 503 }) })
    render(<HealthCard />)

    expect(await screen.findByText(/Unreachable: Request failed with status 503/)).toBeInTheDocument()
  })

  it('re-checks when the button is clicked', async () => {
    const user = userEvent.setup()
    let healthy = false
    const fetch = mockApi({ 'GET /healthz': () => (healthy ? ok() : new Response(null, { status: 503 })) })
    render(<HealthCard />)
    await screen.findByText(/Unreachable/)

    healthy = true
    await user.click(screen.getByRole('button', { name: 'Check again' }))

    expect(await screen.findByText('Success: api is ok')).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})

import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Device } from '@/lib/api/client'
import { mockApi, requestsOf, sessionResponse } from '@/test/api'
import { renderRoute } from '@/test/render'
import { useAuthStore } from '@/stores/auth'

const bench: Device = {
  id: '22222222-2222-2222-2222-222222222222',
  type: 'harwood0',
  name: 'bench-rover',
  created_at: '2026-01-02T03:04:05Z',
}
const garage: Device = {
  id: '33333333-3333-3333-3333-333333333333',
  type: 'harwood0',
  name: 'garage-rover',
  created_at: '2026-01-03T03:04:05Z',
}

async function signIn() {
  mockApi({ 'POST /auth/login': () => sessionResponse() })
  await useAuthStore.getState().login('jane@example.com', 'hunter22')
}

const codeResponse = (code = 'AB3D7K') =>
  Response.json({ code, expires_at: new Date(Date.now() + 10 * 60_000).toISOString() }, { status: 201 })

/** Advances fake time, letting pending requests and renders settle. */
const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms))

describe('devices', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('lists the signed-in user’s devices', async () => {
    await signIn()
    mockApi({ 'GET /devices': () => Response.json([garage, bench]) })
    renderRoute('/devices')

    expect(await screen.findByRole('heading', { name: 'Devices' })).toBeInTheDocument()
    const rows = await screen.findAllByRole('row')
    expect(rows.map((r) => within(r).queryAllByRole('cell')[0]?.textContent)).toEqual([
      undefined,
      'garage-rover',
      'bench-rover',
    ])
    expect(rows[1]).toHaveTextContent('harwood0')
    expect(screen.getByRole('link', { name: 'Devices' })).toHaveAttribute('aria-current', 'page')
  })

  it('shows an empty state', async () => {
    await signIn()
    mockApi({ 'GET /devices': () => Response.json([]) })
    renderRoute('/devices')

    expect(await screen.findByText(/No devices yet/)).toBeInTheDocument()
  })

  it('shows a code and reports success when a new device registers', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    await signIn()
    let devices = [bench]
    const spy = mockApi({
      'GET /devices': () => Response.json(devices),
      'POST /devices/registration-codes': () => codeResponse(),
    })
    renderRoute('/devices')
    expect(await screen.findByText('bench-rover')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Register' }))

    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByLabelText('Registration code')).toHaveTextContent('AB3D7K')
    expect(within(dialog).getByRole('timer')).toHaveTextContent('Expires in 10:00')
    await advance(2000)
    expect(within(dialog).getByText('Waiting for the device…')).toBeInTheDocument()
    expect(within(dialog).getByRole('timer')).toHaveTextContent('Expires in 9:58')

    devices = [garage, bench]
    await advance(2000)

    expect(await within(dialog).findByRole('heading', { name: 'Device registered' })).toBeInTheDocument()
    expect(dialog).toHaveTextContent('garage-rover (harwood0) is now linked to your account.')
    expect(screen.getByText('garage-rover')).toBeInTheDocument()
    expect(requestsOf(spy).filter((r) => r === 'POST /devices/registration-codes')).toHaveLength(1)

    await user.click(within(dialog).getByRole('button', { name: 'Done' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('offers a new code when the code expires', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    await signIn()
    let issued = 0
    const spy = mockApi({
      'GET /devices': () => Response.json([]),
      'POST /devices/registration-codes': () => codeResponse(++issued === 1 ? 'AB3D7K' : 'ZX9W8V'),
    })
    renderRoute('/devices')
    await user.click(await screen.findByRole('button', { name: 'Register' }))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByLabelText('Registration code')).toHaveTextContent('AB3D7K')

    await advance(10 * 60_000)

    expect(within(dialog).getByRole('heading', { name: 'Code expired' })).toBeInTheDocument()
    const polls = requestsOf(spy).filter((r) => r === 'GET /devices').length
    await advance(4000)
    expect(requestsOf(spy).filter((r) => r === 'GET /devices')).toHaveLength(polls)

    await user.click(within(dialog).getByRole('button', { name: 'Get a new code' }))

    expect(await within(dialog).findByLabelText('Registration code')).toHaveTextContent('ZX9W8V')
    expect(within(dialog).getByRole('timer')).toHaveTextContent('Expires in 10:00')
    expect(issued).toBe(2)
  })

  it('reports a failure to issue a code', async () => {
    await signIn()
    mockApi({
      'GET /devices': () => Response.json([]),
      'POST /devices/registration-codes': () => Response.json({ code: 'internal', message: 'internal server error' }, { status: 500 }),
    })
    renderRoute('/devices')
    await userEvent.click(await screen.findByRole('button', { name: 'Register' }))

    expect(await screen.findByText('internal server error')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

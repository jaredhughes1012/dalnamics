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
  online: true,
  last_seen_at: '2026-01-04T05:06:07Z',
}
const garage: Device = {
  id: '33333333-3333-3333-3333-333333333333',
  type: 'harwood0',
  name: 'garage-rover',
  created_at: '2026-01-03T03:04:05Z',
  online: false,
  last_seen_at: null,
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

  it('shows whether each device is online next to its name', async () => {
    await signIn()
    mockApi({ 'GET /devices': () => Response.json([garage, bench, { ...bench, id: '44444444-4444-4444-4444-444444444444', name: 'shed-rover', online: false }]) })
    renderRoute('/devices')

    const benchRow = await screen.findByRole('row', { name: /bench-rover/ })
    const online = within(benchRow).getByRole('img', { name: 'Online' })
    expect(online).toHaveClass('bg-green-500')
    expect(online.title).toMatch(/^Last seen /)

    const never = within(screen.getByRole('row', { name: /garage-rover/ })).getByRole('img', { name: 'Offline' })
    expect(never).toHaveClass('bg-muted-foreground/40')
    expect(never).toHaveAttribute('title', 'Never connected')

    const gone = within(screen.getByRole('row', { name: /shed-rover/ })).getByRole('img', { name: 'Offline' })
    expect(gone.title).toMatch(/^Last seen /)
  })

  it('refreshes device status every 15 seconds until the page is left', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await signIn()
    let devices = [garage]
    const spy = mockApi({ 'GET /devices': () => Response.json(devices) })
    const { unmount } = renderRoute('/devices')
    const row = await screen.findByRole('row', { name: /garage-rover/ })
    expect(within(row).getByRole('img', { name: 'Offline' })).toBeInTheDocument()
    const loads = () => requestsOf(spy).filter((r) => r === 'GET /devices').length
    const initial = loads()

    devices = [{ ...garage, online: true, last_seen_at: new Date().toISOString() }]
    await advance(14_000)
    expect(loads()).toBe(initial)
    await advance(1_000)

    expect(loads()).toBe(initial + 1)
    expect(await within(screen.getByRole('row', { name: /garage-rover/ })).findByRole('img', { name: 'Online' })).toBeInTheDocument()

    unmount()
    await advance(30_000)
    expect(loads()).toBe(initial + 1)
  })

  it('waits for a slow refresh before scheduling the next one', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await signIn()
    let slow = false
    const spy = mockApi({
      'GET /devices': async () => {
        if (slow) await new Promise((r) => setTimeout(r, 20_000))
        return Response.json([garage])
      },
    })
    renderRoute('/devices')
    await screen.findByRole('row', { name: /garage-rover/ })
    const loads = () => requestsOf(spy).filter((r) => r === 'GET /devices').length
    const initial = loads()

    slow = true
    await advance(15_000)
    expect(loads()).toBe(initial + 1)
    slow = false
    await advance(19_000)
    expect(loads(), 'no new request while one is in flight').toBe(initial + 1)

    await advance(1_000 + 15_000)
    expect(loads()).toBe(initial + 2)
  })

  describe('while the tab is hidden', () => {
    let hidden = false
    beforeEach(() => {
      hidden = false
      vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden)
    })
    afterEach(() => vi.restoreAllMocks())

    it('skips refreshes and refreshes as soon as it is shown', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      await signIn()
      const spy = mockApi({ 'GET /devices': () => Response.json([garage]) })
      renderRoute('/devices')
      await screen.findByRole('row', { name: /garage-rover/ })
      const loads = () => requestsOf(spy).filter((r) => r === 'GET /devices').length
      const initial = loads()

      hidden = true
      await advance(60_000)
      expect(loads()).toBe(initial)

      hidden = false
      await act(async () => {
        document.dispatchEvent(new Event('visibilitychange'))
      })
      expect(loads()).toBe(initial + 1)
    })
  })

  it('shows status as unknown while refreshes fail', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await signIn()
    let failing = false
    mockApi({
      'GET /devices': () =>
        failing ? Response.json({ code: 'internal', message: 'internal server error' }, { status: 500 }) : Response.json([bench]),
    })
    renderRoute('/devices')
    const row = await screen.findByRole('row', { name: /bench-rover/ })
    expect(within(row).getByRole('img', { name: 'Online' })).toBeInTheDocument()

    failing = true
    await advance(15_000)
    expect(await screen.findByText('internal server error')).toBeInTheDocument()
    const unknown = within(screen.getByRole('row', { name: /bench-rover/ })).getByRole('img', { name: 'Status unknown' })
    expect(unknown).not.toHaveClass('bg-green-500')
    expect(unknown.title).toMatch(/^Couldn’t refresh status\. Last seen /)

    failing = false
    await advance(15_000)
    expect(await within(screen.getByRole('row', { name: /bench-rover/ })).findByRole('img', { name: 'Online' })).toBeInTheDocument()
  })

  it('opens a device when its row is clicked', async () => {
    const user = userEvent.setup()
    await signIn()
    mockApi({ 'GET /devices': () => Response.json([garage, bench]), [`GET /devices/${bench.id}`]: () => Response.json(bench) })
    const { router } = renderRoute('/devices')

    const row = await screen.findByRole('row', { name: /bench-rover/ })
    await user.click(within(row).getByText('harwood0'))

    expect(await screen.findByRole('heading', { name: 'bench-rover' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/devices/${bench.id}`)
  })

  it('links each device name to its page', async () => {
    const user = userEvent.setup()
    await signIn()
    mockApi({ 'GET /devices': () => Response.json([bench]), [`GET /devices/${bench.id}`]: () => Response.json(bench) })
    const { router } = renderRoute('/devices')

    const link = await screen.findByRole('link', { name: 'bench-rover' })
    expect(link).toHaveAttribute('href', `/devices/${bench.id}`)

    await user.click(link)
    expect(await screen.findByRole('heading', { name: 'bench-rover' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/devices/${bench.id}`)
    expect(router.history.length).toBe(2)
  })

  it('marks only Devices active in the nav rail', async () => {
    await signIn()
    mockApi({ 'GET /devices': () => Response.json([]) })
    renderRoute('/devices')

    await screen.findByRole('heading', { name: 'Devices' })
    expect(screen.getByRole('link', { name: 'Dashboard' })).not.toHaveAttribute('aria-current')
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

    await user.click(within(dialog).getByRole('button', { name: 'Copy code' }))
    expect(await navigator.clipboard.readText()).toBe('AB3D7K')
    expect(within(dialog).getByRole('button', { name: 'Copied' })).toBeInTheDocument()

    await advance(2000)
    expect(within(dialog).getByRole('button', { name: 'Copy code' })).toBeInTheDocument()
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

import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Device } from '@/lib/api/client'
import { apiError, mockApi, requestsOf, sessionResponse } from '@/test/api'
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
const path = `/devices/${bench.id}`
const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

async function signIn() {
  mockApi({ 'POST /auth/login': () => sessionResponse() })
  await useAuthStore.getState().login('jane@example.com', 'hunter22')
}

/** The value cell of the info table row labelled label. */
const field = (label: string) => screen.getByRole('rowheader', { name: label }).nextElementSibling as HTMLElement

/** The status dot beside the device's name. */
const statusDot = async (name: string) => within((await screen.findByRole('heading', { name })).parentElement!).getByRole('img')

/** Advances fake time, letting pending requests and renders settle. */
const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms))

describe('device details', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the device’s name, status, and public fields', async () => {
    await signIn()
    mockApi({ [`GET ${path}`]: () => Response.json(bench) })
    renderRoute(path)

    const dot = await statusDot('bench-rover')
    expect(dot).toHaveAccessibleName('Online')
    expect(dot).toHaveClass('bg-green-500')
    expect(field('ID')).toHaveTextContent(bench.id)
    expect(field('Type')).toHaveTextContent('harwood0')
    expect(field('Status')).toHaveTextContent('Online')
    expect(field('Last seen')).toHaveTextContent(dateTime.format(new Date(bench.last_seen_at!)))
    expect(field('Registered')).toHaveTextContent(dateTime.format(new Date(bench.created_at)))
  })

  it('shows a device that never connected as offline and never seen', async () => {
    await signIn()
    mockApi({ [`GET ${path}`]: () => Response.json({ ...bench, online: false, last_seen_at: null }) })
    renderRoute(path)

    const dot = await statusDot('bench-rover')
    expect(dot).toHaveAccessibleName('Offline')
    expect(dot).toHaveAttribute('title', 'Never connected')
    expect(field('Status')).toHaveTextContent('Offline')
    expect(field('Last seen')).toHaveTextContent('Never')
  })

  it('copies the device ID', async () => {
    const user = userEvent.setup()
    await signIn()
    mockApi({ [`GET ${path}`]: () => Response.json(bench) })
    renderRoute(path)

    await user.click(await screen.findByRole('button', { name: 'Copy ID' }))

    expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument()
    expect(await navigator.clipboard.readText()).toBe(bench.id)
  })

  it.each([
    ['an unknown or another user’s device', 404, 'not_found'],
    ['an ID that isn’t a UUID', 400, 'invalid_request'],
  ])('shows not found for %s', async (_, status, code) => {
    const user = userEvent.setup()
    await signIn()
    mockApi({
      [`GET ${path}`]: () => apiError(status, code, 'nope'),
      'GET /devices': () => Response.json([]),
    })
    const { router } = renderRoute(path)

    expect(await screen.findByRole('heading', { name: 'Device not found' })).toBeInTheDocument()
    expect(screen.queryByText('nope')).not.toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: 'Back to devices' }))
    expect(await screen.findByRole('heading', { name: 'Devices' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/devices')
  })

  it('shows other errors', async () => {
    await signIn()
    mockApi({ [`GET ${path}`]: () => apiError(500, 'internal', 'internal server error') })
    renderRoute(path)

    expect(await screen.findByText('internal server error')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Device not found' })).not.toBeInTheDocument()
  })

  it('refreshes the device until the page is left', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await signIn()
    let device: Device = { ...bench, online: false }
    const spy = mockApi({ [`GET ${path}`]: () => Response.json(device) })
    const { unmount } = renderRoute(path)
    expect(await statusDot('bench-rover')).toHaveAccessibleName('Offline')
    const loads = () => requestsOf(spy).filter((r) => r === `GET ${path}`).length
    const initial = loads()

    device = bench
    await advance(14_000)
    expect(loads()).toBe(initial)
    await advance(1_000)

    expect(loads()).toBe(initial + 1)
    await vi.waitFor(async () => expect(await statusDot('bench-rover')).toHaveAccessibleName('Online'))

    unmount()
    await advance(30_000)
    expect(loads()).toBe(initial + 1)
  })

  it('keeps the device and shows status as unknown while refreshes fail', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await signIn()
    let failing = false
    mockApi({ [`GET ${path}`]: () => (failing ? apiError(500, 'internal', 'internal server error') : Response.json(bench)) })
    renderRoute(path)
    await screen.findByRole('heading', { name: 'bench-rover' })

    failing = true
    await advance(15_000)

    expect(await screen.findByText('internal server error')).toBeInTheDocument()
    expect(await statusDot('bench-rover')).toHaveAccessibleName('Status unknown')
    expect(field('Type')).toHaveTextContent('harwood0')
  })

  it('links back to the list and keeps Devices active in the nav rail', async () => {
    const user = userEvent.setup()
    await signIn()
    mockApi({ [`GET ${path}`]: () => Response.json(bench), 'GET /devices': () => Response.json([bench]) })
    const { router } = renderRoute(path)
    await screen.findByRole('heading', { name: 'bench-rover' })

    const nav = screen.getByRole('navigation', { name: 'Main' })
    expect(within(nav).getByRole('link', { name: 'Devices' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Dashboard' })).not.toHaveAttribute('aria-current')

    await user.click(within(screen.getByRole('main')).getByRole('link', { name: 'Devices' }))
    expect(await screen.findByRole('heading', { name: 'Devices' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/devices')
  })
})

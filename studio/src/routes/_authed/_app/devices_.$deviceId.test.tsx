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
    expect(screen.queryByRole('rowheader', { name: 'Status' }), 'the dot shows status').not.toBeInTheDocument()
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

  it('stops refreshing once the device is known not to exist', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await signIn()
    const spy = mockApi({ [`GET ${path}`]: () => apiError(404, 'not_found', 'device not found') })
    renderRoute(path)
    await screen.findByRole('heading', { name: 'Device not found' })
    const loads = () => requestsOf(spy).filter((r) => r === `GET ${path}`).length
    const initial = loads()

    await advance(60_000)

    expect(loads()).toBe(initial)
  })

  it('doesn’t show a device’s old status when the page is opened again', async () => {
    await signIn()
    let deferred = false
    const pending: ((r: Response) => void)[] = []
    mockApi({
      [`GET ${path}`]: () =>
        deferred ? new Promise<Response>((resolve) => pending.push(resolve)) : Response.json(bench),
    })
    const first = renderRoute(path)
    expect(await statusDot('bench-rover')).toHaveAccessibleName('Online')
    first.unmount()

    deferred = true
    renderRoute(path)
    await vi.waitFor(() => expect(pending).toHaveLength(1))
    expect(screen.queryByRole('heading', { name: 'bench-rover' }), 'nothing shows until the device loads').not.toBeInTheDocument()

    await act(async () => pending[0](Response.json({ ...bench, online: false })))
    expect(await statusDot('bench-rover')).toHaveAccessibleName('Offline')
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

describe('renaming a device', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  /** Signs in and opens the page, with PATCH answered by rename (by default, the device with the sent name). */
  async function openPage(rename?: (request: Request) => Response | Promise<Response>) {
    await signIn()
    let device = bench
    const spy = mockApi({
      [`GET ${path}`]: () => Response.json(device),
      'GET /devices': () => Response.json([device]),
      [`PATCH ${path}`]:
        rename ??
        (async (request) => {
          device = { ...bench, name: (await request.json()).name }
          return Response.json(device)
        }),
    })
    renderRoute(path)
    await screen.findByRole('heading', { name: 'bench-rover' })
    return spy
  }

  const patches = (spy: ReturnType<typeof mockApi>) => requestsOf(spy).filter((r) => r === `PATCH ${path}`)

  it('edits the name in place with the current name selected', async () => {
    const user = userEvent.setup()
    await openPage()

    await user.click(screen.getByRole('button', { name: 'Rename device' }))

    const input = screen.getByRole<HTMLInputElement>('textbox', { name: 'Device name' })
    expect(input).toHaveValue('bench-rover')
    expect(input).toHaveFocus()
    expect([input.selectionStart, input.selectionEnd]).toEqual([0, 'bench-rover'.length])
    expect(screen.queryByRole('heading', { name: 'bench-rover' })).not.toBeInTheDocument()
  })

  it('saves the trimmed name on Enter and reloads the devices list', async () => {
    const user = userEvent.setup()
    const sent: unknown[] = []
    const spy = await openPage(async (request) => {
      const body = await request.json()
      sent.push(body)
      return Response.json({ ...bench, name: body.name })
    })

    await user.click(screen.getByRole('button', { name: 'Rename device' }))
    await user.clear(screen.getByRole('textbox', { name: 'Device name' }))
    await user.keyboard('  Bench rover  {Enter}')

    expect(await screen.findByRole('heading', { name: 'Bench rover' })).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Device name' })).not.toBeInTheDocument()
    expect(sent).toEqual([{ name: 'Bench rover' }])
    await vi.waitFor(() => expect(requestsOf(spy)).toContain('GET /devices'))
  })

  it.each([
    ['Escape', async (user: ReturnType<typeof userEvent.setup>) => user.keyboard('{Escape}')],
    ['clicking away', async (user: ReturnType<typeof userEvent.setup>) => user.click(document.body)],
  ])('cancels on %s', async (_, leave) => {
    const user = userEvent.setup()
    const spy = await openPage()

    await user.click(screen.getByRole('button', { name: 'Rename device' }))
    await user.type(screen.getByRole('textbox', { name: 'Device name' }), '-renamed')
    await leave(user)

    expect(screen.getByRole('heading', { name: 'bench-rover' })).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Device name' })).not.toBeInTheDocument()
    expect(patches(spy)).toEqual([])
  })

  it.each([
    ['a blank name', '   ', 'Name is required'],
    ['a name over 100 characters', 'a'.repeat(101), 'Name must be at most 100 characters'],
  ])('rejects %s without saving', async (_, name, message) => {
    const user = userEvent.setup()
    const spy = await openPage()

    await user.click(screen.getByRole('button', { name: 'Rename device' }))
    const input = screen.getByRole('textbox', { name: 'Device name' })
    await user.clear(input)
    await user.type(input, `${name}{Enter}`)

    expect(screen.getByText(message)).toBeInTheDocument()
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(patches(spy)).toEqual([])
  })

  it('exits without saving when the name is unchanged', async () => {
    const user = userEvent.setup()
    const spy = await openPage()

    await user.click(screen.getByRole('button', { name: 'Rename device' }))
    await user.keyboard(' bench-rover {Enter}')

    expect(screen.getByRole('heading', { name: 'bench-rover' })).toBeInTheDocument()
    expect(patches(spy)).toEqual([])
  })

  it('stays in edit mode and shows the error when saving fails', async () => {
    const user = userEvent.setup()
    await openPage(() => apiError(500, 'internal', 'internal server error'))

    await user.click(screen.getByRole('button', { name: 'Rename device' }))
    await user.keyboard('Bench rover{Enter}')

    expect(await screen.findByText('internal server error')).toBeInTheDocument()
    const input = screen.getByRole('textbox', { name: 'Device name' })
    expect(input).toHaveValue('Bench rover')
    expect(input).toBeEnabled()
    expect(screen.queryByRole('heading', { name: 'Bench rover' })).not.toBeInTheDocument()
  })

  it('disables the input while saving, without cancelling', async () => {
    const user = userEvent.setup()
    let respond!: (r: Response) => void
    await openPage(() => new Promise<Response>((resolve) => (respond = resolve)))

    await user.click(screen.getByRole('button', { name: 'Rename device' }))
    await user.keyboard('Bench rover{Enter}')

    const input = screen.getByRole('textbox', { name: 'Device name' })
    await vi.waitFor(() => expect(input).toBeDisabled())
    await act(async () => respond(Response.json({ ...bench, name: 'Bench rover' })))
    expect(await screen.findByRole('heading', { name: 'Bench rover' })).toBeInTheDocument()
  })

  it('keeps the draft when the device refreshes during an edit', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const spy = await openPage()
    const loads = () => requestsOf(spy).filter((r) => r === `GET ${path}`).length

    await user.click(screen.getByRole('button', { name: 'Rename device' }))
    await user.keyboard('Bench rover')
    const before = loads()
    await advance(15_000)

    expect(loads()).toBeGreaterThan(before)
    expect(screen.getByRole('textbox', { name: 'Device name' })).toHaveValue('Bench rover')
  })
})


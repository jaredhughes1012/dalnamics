import type { Device } from '@/lib/api/client'
import { apiError, mockApi } from '@/test/api'
import { useDeviceStore } from './device'

const device = (id: string, online = false): Device => ({
  id,
  type: 'harwood0',
  name: `rover-${id.slice(0, 1)}`,
  created_at: '2026-01-02T03:04:05Z',
  online,
  last_seen_at: null,
})
const a = '22222222-2222-2222-2222-222222222222'
const b = '33333333-3333-3333-3333-333333333333'

/** Stubs GET /devices/{id} with responses the test resolves itself. */
function deferredApi() {
  const responses: Record<string, ((r: Response) => void)[]> = { [a]: [], [b]: [] }
  mockApi({
    [`GET /devices/${a}`]: () => new Promise<Response>((resolve) => responses[a].push(resolve)),
    [`GET /devices/${b}`]: () => new Promise<Response>((resolve) => responses[b].push(resolve)),
  })
  return responses
}

describe('device store', () => {
  it('keeps the device on screen while reloading the same ID', async () => {
    const responses = deferredApi()
    const { load } = useDeviceStore.getState()

    const first = load(a)
    expect(useDeviceStore.getState()).toMatchObject({ id: a, status: 'loading', device: undefined })
    await vi.waitFor(() => expect(responses[a]).toHaveLength(1))
    responses[a][0](Response.json(device(a)))
    await first

    const reload = load(a)
    expect(useDeviceStore.getState()).toMatchObject({ status: 'success', device: device(a) })
    await vi.waitFor(() => expect(responses[a]).toHaveLength(2))
    responses[a][1](Response.json(device(a, true)))
    await reload

    expect(useDeviceStore.getState()).toMatchObject({ status: 'success', device: device(a, true) })
  })

  it('clears the previous device when loading another ID', async () => {
    const responses = deferredApi()
    const { load } = useDeviceStore.getState()
    const first = load(a)
    await vi.waitFor(() => expect(responses[a]).toHaveLength(1))
    responses[a][0](Response.json(device(a)))
    await first

    const other = load(b)

    expect(useDeviceStore.getState()).toMatchObject({ id: b, status: 'loading', device: undefined, notFound: false })
    await vi.waitFor(() => expect(responses[b]).toHaveLength(1))
    responses[b][0](Response.json(device(b)))
    await other
  })

  it('drops a late response for an ID no longer shown', async () => {
    const responses = deferredApi()
    const { load } = useDeviceStore.getState()

    const older = load(a)
    const newer = load(b)
    await vi.waitFor(() => expect(responses[b]).toHaveLength(1))
    responses[b][0](Response.json(device(b)))
    await newer
    await vi.waitFor(() => expect(responses[a]).toHaveLength(1))
    responses[a][0](Response.json(device(a)))
    await older

    expect(useDeviceStore.getState()).toMatchObject({ id: b, device: device(b) })
  })

  it('drops a response that arrives after a newer one', async () => {
    const responses = deferredApi()
    const { load } = useDeviceStore.getState()

    const older = load(a)
    const newer = load(a)
    await vi.waitFor(() => expect(responses[a]).toHaveLength(2))
    responses[a][1](Response.json(device(a, true)))
    await newer
    responses[a][0](Response.json(device(a, false)))
    await older

    expect(useDeviceStore.getState().device).toEqual(device(a, true))
  })

  it('marks a 404 as not found rather than an error', async () => {
    mockApi({ [`GET /devices/${a}`]: () => apiError(404, 'not_found', 'device not found') })

    await useDeviceStore.getState().load(a)

    expect(useDeviceStore.getState()).toMatchObject({ notFound: true, device: undefined, error: undefined })
  })

  it('keeps the device when a reload fails', async () => {
    let failing = false
    mockApi({ [`GET /devices/${a}`]: () => (failing ? apiError(500, 'internal', 'boom') : Response.json(device(a))) })
    const { load } = useDeviceStore.getState()
    await load(a)

    failing = true
    await load(a)

    expect(useDeviceStore.getState()).toMatchObject({ status: 'error', error: 'boom', device: device(a), notFound: false })
  })
})

import type { Device } from '@/lib/api/client'
import { mockApi } from '@/test/api'
import { useDevicesStore } from './devices'

const device = (online: boolean): Device => ({
  id: '22222222-2222-2222-2222-222222222222',
  type: 'harwood0',
  name: 'bench-rover',
  created_at: '2026-01-02T03:04:05Z',
  online,
  last_seen_at: null,
})

describe('devices store', () => {
  it('drops a response that arrives after a newer one', async () => {
    const responses: ((r: Response) => void)[] = []
    mockApi({ 'GET /devices': () => new Promise<Response>((resolve) => responses.push(resolve)) })
    const { load } = useDevicesStore.getState()

    const older = load()
    const newer = load()
    await vi.waitFor(() => expect(responses).toHaveLength(2))
    responses[1](Response.json([device(true)]))
    await newer
    responses[0](Response.json([device(false)]))
    await older

    expect(useDevicesStore.getState().devices).toEqual([device(true)])
  })

  it('drops a failure that arrives after a newer success', async () => {
    const responses: ((r: Response) => void)[] = []
    mockApi({ 'GET /devices': () => new Promise<Response>((resolve) => responses.push(resolve)) })
    const { load } = useDevicesStore.getState()

    const older = load()
    const newer = load()
    await vi.waitFor(() => expect(responses).toHaveLength(2))
    responses[1](Response.json([device(true)]))
    await newer
    responses[0](Response.json({ code: 'internal', message: 'boom' }, { status: 500 }))
    await older

    expect(useDevicesStore.getState()).toMatchObject({ status: 'success', devices: [device(true)], error: undefined })
  })
})

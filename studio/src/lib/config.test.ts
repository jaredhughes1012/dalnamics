import { devicesRefreshMs } from '@/lib/config'

describe('devicesRefreshMs', () => {
  it('defaults to 15 seconds', () => {
    expect(devicesRefreshMs({})).toBe(15_000)
  })

  it('reads VITE_DEVICES_REFRESH_MS', () => {
    expect(devicesRefreshMs({ VITE_DEVICES_REFRESH_MS: '5000' })).toBe(5_000)
  })

  it.each(['', 'soon', '0', '-5'])('falls back to the default for %j', (value) => {
    expect(devicesRefreshMs({ VITE_DEVICES_REFRESH_MS: value })).toBe(15_000)
  })
})

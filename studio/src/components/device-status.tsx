import type { Device } from '@/lib/api/client'
import { cn } from '@/lib/utils'

const lastSeen = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

/** A green (online) or gray (offline) dot, with when the device was last seen as its tooltip. */
export function DeviceStatus({ device }: { device: Pick<Device, 'online' | 'last_seen_at'> }) {
  const label = device.online ? 'Online' : 'Offline'
  return (
    <span
      role="img"
      aria-label={label}
      title={device.last_seen_at ? `Last seen ${lastSeen.format(new Date(device.last_seen_at))}` : 'Never connected'}
      className={cn('inline-block size-2 shrink-0 rounded-full', device.online ? 'bg-green-500' : 'bg-muted-foreground/40')}
    />
  )
}

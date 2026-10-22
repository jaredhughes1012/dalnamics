import type { Device } from '@/lib/api/client'
import { dateTime } from '@/lib/format'
import { cn } from '@/lib/utils'

/**
 * A green (online) or gray (offline) dot, with when the device was last seen as
 * its tooltip. A stale status, from a list that failed to refresh, shows as a
 * hollow dot labelled unknown, so an old status never passes for a current one.
 */
export function DeviceStatus({ device, stale = false }: { device: Pick<Device, 'online' | 'last_seen_at'>; stale?: boolean }) {
  const label = stale ? 'Status unknown' : device.online ? 'Online' : 'Offline'
  const seen = device.last_seen_at ? `Last seen ${dateTime.format(new Date(device.last_seen_at))}` : 'Never connected'
  return (
    <span
      role="img"
      aria-label={label}
      title={stale ? `Couldn’t refresh status. ${seen}` : seen}
      className={cn(
        'inline-block size-2 shrink-0 rounded-full',
        stale ? 'border border-muted-foreground/60' : device.online ? 'bg-green-500' : 'bg-muted-foreground/40',
      )}
    />
  )
}

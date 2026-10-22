import { useCallback } from 'react'
import { createFileRoute, Link } from '@tanstack/react-router'
import { ArrowLeft } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { CopyButton } from '@/components/copy-button'
import { DeviceStatus } from '@/components/device-status'
import { FormError } from '@/components/form-error'
import { useRefresh } from '@/lib/use-refresh'
import { useDeviceStore } from '@/stores/device'

export const Route = createFileRoute('/_authed/_app/devices_/$deviceId')({
  component: DeviceDetails,
})

const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

function DeviceDetails() {
  const { deviceId } = Route.useParams()
  const { status, id, device, notFound, error, load } = useDeviceStore()
  const refresh = useCallback(() => load(deviceId), [load, deviceId])
  useRefresh(refresh)

  // Until the store has switched to this ID, it may still hold another device.
  const current = id === deviceId

  if (current && notFound) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <h1 className="text-2xl font-semibold">Device not found</h1>
        <p className="text-sm text-muted-foreground">It may have been removed, or it belongs to another account.</p>
        <Link to="/devices" className="text-sm font-medium underline underline-offset-4">
          Back to devices
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Link
          to="/devices"
          className="flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Devices
        </Link>
        {current && device && (
          <header className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{device.name}</h1>
            <DeviceStatus device={device} stale={status === 'error'} />
          </header>
        )}
      </div>

      <FormError message={current ? error : undefined} />
      {current && device && (
        <Card className="py-0">
          <CardContent className="px-0">
            <table className="w-full text-sm">
              <tbody>
                <Row label="ID">
                  <span className="flex flex-wrap items-center gap-3">
                    <span className="font-mono">{device.id}</span>
                    <CopyButton text={device.id} label="Copy ID" />
                  </span>
                </Row>
                <Row label="Type">{device.type}</Row>
                <Row label="Status">{device.online ? 'Online' : 'Offline'}</Row>
                <Row label="Last seen">{device.last_seen_at ? dateTime.format(new Date(device.last_seen_at)) : 'Never'}</Row>
                <Row label="Registered">{dateTime.format(new Date(device.created_at))}</Row>
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr className="border-b last:border-0">
      <th scope="row" className="w-40 px-6 py-3 text-left font-medium text-muted-foreground">
        {label}
      </th>
      <td className="px-6 py-3">{children}</td>
    </tr>
  )
}

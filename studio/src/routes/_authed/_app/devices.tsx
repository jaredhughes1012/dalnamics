import { useState } from 'react'
import { createFileRoute, Link, useNavigate, useRouter } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { DeviceStatus } from '@/components/device-status'
import { FormError } from '@/components/form-error'
import { RegisterDeviceDialog } from '@/components/register-device-dialog'
import { dateTime } from '@/lib/format'
import { useRefresh } from '@/lib/use-refresh'
import { useDevicesStore } from '@/stores/devices'

export const Route = createFileRoute('/_authed/_app/devices')({
  component: Devices,
})

function Devices() {
  const { status, devices, error, load } = useDevicesStore()
  const [registering, setRegistering] = useState(false)

  const navigate = useNavigate()
  const router = useRouter()
  // Refreshing keeps each device's status current.
  useRefresh(load)

  // The name link handles its own clicks; the rest of the row is a larger
  // target for mouse users, and acts like the link: a modifier or middle click
  // opens a new tab, and selecting text doesn't navigate.
  function openDevice(e: React.MouseEvent, deviceId: string) {
    if ((e.target as Element).closest('a') || window.getSelection()?.toString()) return
    if (e.button === 1 || (e.button === 0 && (e.metaKey || e.ctrlKey || e.shiftKey))) {
      const { href } = router.buildLocation({ to: '/devices/$deviceId', params: { deviceId } })
      window.open(href, '_blank', 'noopener')
      return
    }
    if (e.button === 0) void navigate({ to: '/devices/$deviceId', params: { deviceId } })
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Devices</h1>
          <p className="text-sm text-muted-foreground">Hardware linked to your account</p>
        </div>
        <Button onClick={() => setRegistering(true)}>
          <Plus />
          Register
        </Button>
      </header>

      <FormError message={error} />
      <Card className="py-0">
        <CardContent className="px-0">
          {status === 'success' && devices.length === 0 ? (
            <p className="p-6 text-center text-sm text-muted-foreground">
              No devices yet. Register one to link it to your account.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b text-left text-muted-foreground">
                <tr>
                  <th className="px-6 py-3 font-medium">Name</th>
                  <th className="px-6 py-3 font-medium">Type</th>
                  <th className="px-6 py-3 font-medium">Registered</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((d) => (
                  <tr
                    key={d.id}
                    className="cursor-pointer border-b last:border-0 hover:bg-muted/50"
                    onClick={(e) => openDevice(e, d.id)}
                    onAuxClick={(e) => openDevice(e, d.id)}
                  >
                    <td className="px-6 py-3 font-medium">
                      <span className="flex items-center gap-2">
                        <DeviceStatus device={d} stale={status === 'error'} />
                        <Link to="/devices/$deviceId" params={{ deviceId: d.id }} className="hover:underline">
                          {d.name}
                        </Link>
                      </span>
                    </td>
                    <td className="px-6 py-3">{d.type}</td>
                    <td className="px-6 py-3 text-muted-foreground">{dateTime.format(new Date(d.created_at))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <RegisterDeviceDialog open={registering} onOpenChange={setRegistering} />
    </div>
  )
}

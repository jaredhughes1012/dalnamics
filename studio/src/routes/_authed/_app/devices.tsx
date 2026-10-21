import { useEffect, useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { DeviceStatus } from '@/components/device-status'
import { FormError } from '@/components/form-error'
import { RegisterDeviceDialog } from '@/components/register-device-dialog'
import { useDevicesStore } from '@/stores/devices'

export const Route = createFileRoute('/_authed/_app/devices')({
  component: Devices,
})

const registeredAt = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

/** How often the page refreshes the list, so each device's status stays current. */
const REFRESH_MS = 15_000

function Devices() {
  const { status, devices, error, load } = useDevicesStore()
  const [registering, setRegistering] = useState(false)

  useEffect(() => {
    void load()
    const refresh = setInterval(() => void load(), REFRESH_MS)
    return () => clearInterval(refresh)
  }, [load])

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
                  <tr key={d.id} className="border-b last:border-0">
                    <td className="px-6 py-3 font-medium">
                      <span className="flex items-center gap-2">
                        <DeviceStatus device={d} />
                        {d.name}
                      </span>
                    </td>
                    <td className="px-6 py-3">{d.type}</td>
                    <td className="px-6 py-3 text-muted-foreground">{registeredAt.format(new Date(d.created_at))}</td>
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

import { useEffect, useRef, useState } from 'react'
import { Check, CircleCheck, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { FormError } from '@/components/form-error'
import { api, unwrap, type Device, type DeviceRegistrationCode } from '@/lib/api/client'
import { errorMessage } from '@/lib/errors'
import { useDevicesStore } from '@/stores/devices'

/** How often the dialog checks whether a device has redeemed the code. */
const POLL_INTERVAL_MS = 2000

/** How long the copy button shows that the code was copied. */
const COPIED_MS = 2000

type Phase =
  | { name: 'issuing' }
  | { name: 'waiting'; code: DeviceRegistrationCode }
  | { name: 'registered'; device: Device }
  | { name: 'expired' }
  | { name: 'error'; message: string }

async function requestCode(): Promise<Phase> {
  try {
    return { name: 'waiting', code: unwrap(await api.POST('/devices/registration-codes')) }
  } catch (err) {
    return { name: 'error', message: errorMessage(err) }
  }
}

function formatRemaining(ms: number) {
  const total = Math.max(0, Math.ceil(ms / 1000))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/**
 * Issues a one-time registration code and waits for a device to redeem it,
 * polling the device list until a device that wasn't there before appears.
 */
export function RegisterDeviceDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>{open && <RegisterDevice onDone={() => onOpenChange(false)} />}</DialogContent>
    </Dialog>
  )
}

function RegisterDevice({ onDone }: { onDone: () => void }) {
  const [phase, setPhase] = useState<Phase>({ name: 'issuing' })
  const [now, setNow] = useState(() => Date.now())
  // Devices that existed before the code was issued; any other device is the new one.
  const known = useRef(new Set<string>())

  async function start(): Promise<Phase> {
    await useDevicesStore.getState().load()
    known.current = new Set(useDevicesStore.getState().devices.map((d) => d.id))
    return requestCode()
  }

  function show(next: Phase) {
    setNow(Date.now())
    setPhase(next)
  }

  function issue() {
    setPhase({ name: 'issuing' })
    void start().then(show)
  }

  useEffect(() => {
    void start().then(show)
  }, [])

  const waitingFor = phase.name === 'waiting' ? phase.code : undefined
  useEffect(() => {
    if (!waitingFor) return
    const expiresAt = Date.parse(waitingFor.expires_at)

    const tick = setInterval(() => {
      setNow(Date.now())
      if (Date.now() >= expiresAt) setPhase({ name: 'expired' })
    }, 1000)
    const poll = setInterval(() => {
      void useDevicesStore
        .getState()
        .load()
        .then(() => {
          const device = useDevicesStore.getState().devices.find((d) => !known.current.has(d.id))
          if (device) setPhase({ name: 'registered', device })
        })
    }, POLL_INTERVAL_MS)
    return () => {
      clearInterval(tick)
      clearInterval(poll)
    }
  }, [waitingFor])

  switch (phase.name) {
    case 'issuing':
      return (
        <DialogHeader>
          <DialogTitle>Register a device</DialogTitle>
          <DialogDescription>Getting a code…</DialogDescription>
        </DialogHeader>
      )
    case 'error':
      return (
        <>
          <DialogHeader>
            <DialogTitle>Register a device</DialogTitle>
            <DialogDescription>Couldn't get a registration code.</DialogDescription>
          </DialogHeader>
          <FormError message={phase.message} />
          <DialogFooter>
            <Button onClick={issue}>Try again</Button>
          </DialogFooter>
        </>
      )
    case 'waiting':
      return (
        <>
          <DialogHeader>
            <DialogTitle>Register a device</DialogTitle>
            <DialogDescription>
              Enter this code on the device. For harwood0, set <code>HARWOOD0_REGISTRATION_CODE</code>.
            </DialogDescription>
          </DialogHeader>
          <p
            aria-label="Registration code"
            className="text-center font-mono text-4xl font-semibold tracking-[0.3em]"
          >
            {phase.code.code}
          </p>
          <CopyButton text={phase.code.code} />
          <p role="timer" className="text-center text-sm text-muted-foreground">
            Expires in {formatRemaining(Date.parse(phase.code.expires_at) - now)}
          </p>
          <p role="status" className="text-center text-sm text-muted-foreground">
            Waiting for the device…
          </p>
        </>
      )
    case 'registered':
      return (
        <>
          <DialogHeader>
            <DialogTitle>Device registered</DialogTitle>
            <DialogDescription>
              {phase.device.name} ({phase.device.type}) is now linked to your account.
            </DialogDescription>
          </DialogHeader>
          <CircleCheck className="mx-auto size-12 text-green-600" aria-hidden />
          <DialogFooter>
            <Button onClick={onDone}>Done</Button>
          </DialogFooter>
        </>
      )
    case 'expired':
      return (
        <>
          <DialogHeader>
            <DialogTitle>Code expired</DialogTitle>
            <DialogDescription>No device used the code in time.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={issue}>Get a new code</Button>
          </DialogFooter>
        </>
      )
  }
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const reset = setTimeout(() => setCopied(false), COPIED_MS)
    return () => clearTimeout(reset)
  }, [copied])

  function copy() {
    navigator.clipboard.writeText(text).then(
      () => setCopied(true),
      () => {},
    )
  }

  return (
    <Button variant="outline" size="sm" className="mx-auto" onClick={copy}>
      {copied ? <Check data-icon="inline-start" aria-hidden /> : <Copy data-icon="inline-start" aria-hidden />}
      {copied ? 'Copied' : 'Copy code'}
    </Button>
  )
}

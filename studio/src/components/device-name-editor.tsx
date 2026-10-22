import { useEffect, useRef, useState } from 'react'
import { Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormError } from '@/components/form-error'
import { errorMessage } from '@/lib/errors'

/** The api's limit on a device name, counted in characters (code points). */
const MAX_NAME_LENGTH = 100

/**
 * A device's name as the page heading, with a pencil that turns it into an
 * input. Enter saves through onRename; Escape or clicking away cancels. Render
 * it inside an element with the `group` class: the pencil shows while that
 * element is hovered or holds focus, and always on screens without hover.
 * The draft is local, so name changing underneath (e.g. from a refresh)
 * doesn't disturb an edit in progress.
 */
export function DeviceNameEditor({ name, onRename }: { name: string; onRename: (name: string) => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string>()
  const input = useRef<HTMLInputElement>(null)
  // Disabling the input while saving blurs it, which mustn't cancel the edit.
  const savingRef = useRef(false)

  // Selects the name on entering edit mode, and refocuses the input after a
  // failed save re-enables it.
  useEffect(() => {
    if (!editing || saving) return
    input.current?.focus()
    input.current?.select()
  }, [editing, saving])

  function start() {
    setDraft(name)
    setError(undefined)
    setEditing(true)
  }

  function cancel() {
    if (savingRef.current) return
    setEditing(false)
    setError(undefined)
  }

  async function save() {
    const value = draft.trim()
    if (!value) return setError('Name is required')
    if (Array.from(value).length > MAX_NAME_LENGTH) return setError(`Name must be at most ${MAX_NAME_LENGTH} characters`)
    if (value === name) return cancel()

    savingRef.current = true
    setSaving(true)
    setError(undefined)
    try {
      await onRename(value)
      setEditing(false)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  if (!editing) {
    return (
      <>
        <h1 className="text-2xl font-semibold">{name}</h1>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Rename device"
          className="-ml-2 opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:opacity-100"
          onClick={start}
        >
          <Pencil aria-hidden />
        </Button>
      </>
    )
  }

  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <Input
        ref={input}
        aria-label="Device name"
        aria-invalid={error ? true : undefined}
        className="h-auto py-0.5 text-2xl font-semibold md:text-2xl"
        value={draft}
        disabled={saving}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={cancel}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            void save()
          } else if (e.key === 'Escape') {
            e.preventDefault()
            cancel()
          }
        }}
      />
      <FormError message={error} />
    </div>
  )
}

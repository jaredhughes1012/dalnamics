import { useEffect, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'

/** How long the button shows that the text was copied. */
const COPIED_MS = 2000

/** Copies text to the clipboard, showing "Copied" for a moment after it succeeds. */
export function CopyButton({ text, label, className }: { text: string; label: string; className?: string }) {
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
    <Button variant="outline" size="sm" className={className} onClick={copy}>
      {copied ? <Check data-icon="inline-start" aria-hidden /> : <Copy data-icon="inline-start" aria-hidden />}
      {copied ? 'Copied' : label}
    </Button>
  )
}

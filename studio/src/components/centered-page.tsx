import type { ReactNode } from 'react'

/** Full-height page with its content centered, for single-card flows like login. */
export function CenteredPage({ children }: { children: ReactNode }) {
  return <main className="flex min-h-svh items-center justify-center p-6">{children}</main>
}

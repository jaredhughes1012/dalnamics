/** Returns path if it is a same-origin path, otherwise "/". Prevents open redirects. */
export function safeRedirect(path: string | undefined): string {
  if (!path || !path.startsWith('/') || path.startsWith('//') || path.startsWith('/\\')) return '/'
  return path
}

/** Reports whether uri is an http loopback URL with a port, where a cli can listen. */
export function isLoopbackRedirect(uri: string): boolean {
  let url: URL
  try {
    url = new URL(uri)
  } catch {
    return false
  }
  const loopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)
  return url.protocol === 'http:' && loopback && url.port !== '' && !url.username && !url.password
}

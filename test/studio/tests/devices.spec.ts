import { randomUUID } from 'node:crypto'
import { expect, test, type Page } from '@playwright/test'
import { connectBroker, handshake, issueCode, registerInStudio, signupToken, uniqueDeviceName } from './device'
import { API_URL, AUTH_FILE } from './env'

test.use({ storageState: AUTH_FILE })

test('a device registers with a code from studio and connects with its credentials', async ({ page }) => {
  const name = uniqueDeviceName()
  await page.goto('/')
  await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Devices' }).click()
  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()

  await page.getByRole('button', { name: 'Register' }).click()
  const dialog = page.getByRole('dialog')
  const codeText = dialog.getByLabel('Registration code')
  await expect(codeText).toHaveText(/^[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}$/)
  await expect(dialog.getByRole('timer')).toContainText(/Expires in (10:00|9:5\d)/)
  const code = (await codeText.textContent())!

  // The device enters the code in lowercase; codes are case-insensitive.
  const reply = await handshake(code.toLowerCase(), name)
  if ('error' in reply) throw new Error(`handshake failed: ${reply.error}`)
  expect(reply.device_id).toMatch(/^[0-9a-f-]{36}$/)
  expect(Buffer.from(reply.secret, 'base64url')).toHaveLength(32)

  // The dialog reports the first new device it sees. Other browsers register
  // devices for the same user in parallel, so the name is checked in the list.
  await expect(dialog.getByRole('heading', { name: 'Device registered' })).toBeVisible()
  await expect(dialog).toContainText('(harwood0) is now linked to your account.')
  await dialog.getByRole('button', { name: 'Done' }).click()
  await expect(page.getByRole('row', { name: new RegExp(`${name} harwood0`) })).toBeVisible()

  // From now on the device connects as itself, and only inside devices/{its id}/.
  const device = await connectBroker({ username: reply.device_id, password: reply.secret, clientId: `e2e-${reply.device_id}` })
  try {
    const [own] = await device.subscribeAsync(`devices/${reply.device_id}/#`, { qos: 1 })
    expect(own.qos).toBe(1)
    await expect(device.subscribeAsync('devices/+/telemetry', { qos: 1 })).rejects.toThrow('Not authorized')
    await expect(device.subscribeAsync('devices/register/#', { qos: 1 })).rejects.toThrow('Not authorized')
    await expect(device.publishAsync('devices/someone-else/telemetry', '{}', { qos: 1 })).rejects.toThrow(/Not authorized/i)
  } finally {
    await device.endAsync()
  }
})

test.describe('connectivity', () => {
  test('a device that has never connected shows as offline', async ({ page }) => {
    const name = uniqueDeviceName()
    await registerInStudio(page, name)

    const status = page.getByRole('row', { name: new RegExp(name) }).getByRole('img')
    await expect(status).toHaveAccessibleName('Offline')
    await expect(status).toHaveAttribute('title', 'Never connected')
  })

  test('a heartbeat from a device shows it as online', async ({ page }) => {
    const name = uniqueDeviceName()
    const reply = await registerInStudio(page, name)

    const device = await connectBroker({ username: reply.device_id, password: reply.secret, clientId: `e2e-${reply.device_id}` })
    try {
      await device.publishAsync(`devices/${reply.device_id}/heartbeat`, '', { qos: 0 })

      const status = page.getByRole('row', { name: new RegExp(name) }).getByRole('img')
      await expect(async () => {
        await page.reload()
        await expect(status).toHaveAccessibleName('Online', { timeout: 1_000 })
      }).toPass({ timeout: 10_000 })
      await expect(status).toHaveAttribute('title', /^Last seen /)

      const [res] = await Promise.all([
        page.waitForResponse(
          (r) => r.request().resourceType() === 'fetch' && r.request().method() === 'GET' && new URL(r.url()).pathname.endsWith('/devices'),
        ),
        page.reload(),
      ])
      const listed = (await res.json()).find((d: { id: string }) => d.id === reply.device_id)
      expect(listed).toMatchObject({ online: true })
      expect(Date.now() - Date.parse(listed.last_seen_at)).toBeLessThan(60_000)
    } finally {
      await device.endAsync()
    }
  })
})

test.describe('details', () => {
  /** The status dot beside the device's name on its details page. */
  const statusDot = (page: Page, name: string) =>
    page.getByRole('main').locator('header', { has: page.getByRole('heading', { name, exact: true }) }).getByRole('img')

  test('opens a device from the list and shows its details', async ({ page }) => {
    const name = uniqueDeviceName()
    const reply = await registerInStudio(page, name)

    await page.getByRole('row', { name: new RegExp(name) }).getByRole('cell', { name: 'harwood0' }).click()

    await expect(page).toHaveURL(`/devices/${reply.device_id}`)
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    await expect(statusDot(page, name)).toHaveAccessibleName('Offline')
    const field = (label: string) => page.getByRole('row', { name: new RegExp(`^${label}`) }).getByRole('cell')
    await expect(field('ID')).toContainText(reply.device_id)
    await expect(field('Type')).toHaveText('harwood0')
    await expect(field('Last seen')).toHaveText('Never')
    await expect(page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Devices' })).toHaveAttribute('aria-current', 'page')

    await page.reload()
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()

    await page.getByRole('main').getByRole('link', { name: 'Devices', exact: true }).click()
    await expect(page).toHaveURL('/devices')
    await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  })

  test('opens a device from the keyboard', async ({ page }) => {
    const name = uniqueDeviceName()
    const reply = await registerInStudio(page, name)

    await page.getByRole('link', { name, exact: true }).focus()
    await page.keyboard.press('Enter')

    await expect(page).toHaveURL(`/devices/${reply.device_id}`)
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  })

  test('shows a device coming online without a reload', async ({ page }) => {
    const name = uniqueDeviceName()
    const reply = await registerInStudio(page, name)
    await page.goto(`/devices/${reply.device_id}`)
    await expect(statusDot(page, name)).toHaveAccessibleName('Offline')

    const device = await connectBroker({ username: reply.device_id, password: reply.secret, clientId: `e2e-${reply.device_id}` })
    try {
      await device.publishAsync(`devices/${reply.device_id}/heartbeat`, '', { qos: 0 })

      // The dev server refreshes every 5 s.
      await expect(statusDot(page, name)).toHaveAccessibleName('Online', { timeout: 15_000 })
      await expect(statusDot(page, name)).toHaveAttribute('title', /^Last seen /)
    } finally {
      await device.endAsync()
    }
  })

  test('another user’s device and an unknown ID are both not found', async ({ page, request }) => {
    const name = uniqueDeviceName('someone-elses-rover')
    const token = await signupToken(request)
    const reply = await handshake(await issueCode(request, token), name)
    if ('error' in reply) throw new Error(`handshake failed: ${reply.error}`)

    for (const id of [reply.device_id, randomUUID()]) {
      await page.goto(`/devices/${id}`)
      await expect(page.getByRole('heading', { name: 'Device not found' })).toBeVisible()
      await expect(page.getByText(name)).toHaveCount(0)
    }

    // The api answers the same for both, so it never confirms that an ID exists.
    const other = await signupToken(request)
    for (const id of [reply.device_id, randomUUID()]) {
      const res = await request.get(`${API_URL}/devices/${id}`, { headers: { Authorization: `Bearer ${other}` } })
      expect(res.status()).toBe(404)
      expect(await res.json()).toEqual({ code: 'not_found', message: 'device not found' })
    }
    const own = await request.get(`${API_URL}/devices/${reply.device_id}`, { headers: { Authorization: `Bearer ${token}` } })
    expect(await own.json()).toMatchObject({ id: reply.device_id, name })

    await page.getByRole('link', { name: 'Back to devices' }).click()
    await expect(page).toHaveURL('/devices')
  })
})

test.describe('broker', () => {
  // These exercise only the broker and devicemgr, so one browser is enough.
  test.skip(({ browserName }) => browserName !== 'chromium', 'runs once, in chromium')

  test('rejects a made-up code', async () => {
    expect(await handshake('ZZZZZZ', uniqueDeviceName())).toEqual({ error: 'invalid_code' })
  })

  test('rejects a code that was already used', async ({ request }) => {
    const code = await issueCode(request, await signupToken(request))

    expect(await handshake(code, uniqueDeviceName())).toHaveProperty('device_id')
    expect(await handshake(code, uniqueDeviceName())).toEqual({ error: 'invalid_code' })
  })

  test('rejects a malformed request', async ({ request }) => {
    const code = await issueCode(request, await signupToken(request))

    expect(await handshake(code, 'x'.repeat(101))).toEqual({ error: 'invalid_request' })
  })

  test('refuses a device with the wrong secret', async ({ request }) => {
    const reply = await handshake(await issueCode(request, await signupToken(request)), uniqueDeviceName())
    if ('error' in reply) throw new Error(`handshake failed: ${reply.error}`)

    await expect(connectBroker({ username: reply.device_id, password: 'not-the-secret', clientId: 'e2e-wrong-secret' })).rejects.toThrow(
      /Bad User Name or Password|Not authorized/i,
    )
  })
})

test('devices registered by another user are not listed', async ({ page, request }) => {
  const name = uniqueDeviceName('someone-elses-rover')
  const reply = await handshake(await issueCode(request, await signupToken(request)), name)
  expect(reply).toHaveProperty('device_id')

  await page.goto('/devices')

  await expect(page.getByRole('heading', { name: 'Devices' })).toBeVisible()
  await expect(page.getByRole('table').or(page.getByText(/No devices yet/))).toBeVisible()
  await expect(page.getByText(name)).toHaveCount(0)
})

import { randomBytes } from 'node:crypto'
import { expect, type APIRequestContext, type Page } from '@playwright/test'
import mqtt, { type IClientOptions, type MqttClient } from 'mqtt'
import { API_URL, MQTT_URL } from './env'
import { uniqueEmail } from './fixtures'

export type HandshakeReply = { device_id: string; secret: string } | { error: string }

/**
 * Connects to the broker over MQTT 5. Retries refused connections for a while,
 * because Playwright only waits for the api to be healthy, not the broker.
 */
export async function connectBroker(options: IClientOptions): Promise<MqttClient> {
  const deadline = Date.now() + 30_000
  for (;;) {
    try {
      return await mqtt.connectAsync(MQTT_URL, { protocolVersion: 5, reconnectPeriod: 0, connectTimeout: 5_000, ...options })
    } catch (err) {
      const refused = (err as NodeJS.ErrnoException).code === 'ECONNREFUSED'
      if (!refused || Date.now() > deadline) throw err
      await new Promise((r) => setTimeout(r, 500))
    }
  }
}

/** Plays a device's side of the registration handshake and returns devicemgr's reply. */
export async function handshake(code: string, name: string): Promise<HandshakeReply> {
  const clientId = `e2e-register-${randomBytes(16).toString('hex')}`
  const requestTopic = `devices/register/${clientId}`
  const client = await connectBroker({ username: 'register', password: 'register', clientId })
  try {
    const reply = new Promise<HandshakeReply>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('no handshake reply within 10 s')), 10_000)
      client.on('message', (topic, payload) => {
        if (topic !== `${requestTopic}/reply`) return
        clearTimeout(timer)
        resolve(JSON.parse(payload.toString()))
      })
    })
    await client.subscribeAsync(`${requestTopic}/reply`, { qos: 1 })
    const request = JSON.stringify({ code, type: 'harwood0', name })
    // The broker acks with "no matching subscribers" (16) until devicemgr has
    // subscribed, which can lag the api's health check that Playwright waits on.
    const deadline = Date.now() + 30_000
    while ((await client.publishAsync(requestTopic, request, { qos: 1 }))?.reasonCode === 16) {
      if (Date.now() > deadline) throw new Error('devicemgr never subscribed to registration requests')
      await new Promise((r) => setTimeout(r, 500))
    }
    return await reply
  } finally {
    await client.endAsync()
  }
}

/**
 * Registers a device named name to the signed-in studio user: gets a code from
 * the Devices page's dialog and plays the device's side of the handshake.
 * Leaves the page on /devices with the dialog closed.
 */
export async function registerInStudio(page: Page, name: string): Promise<{ device_id: string; secret: string }> {
  await page.goto('/devices')
  await page.getByRole('button', { name: 'Register' }).click()
  const dialog = page.getByRole('dialog')
  const codeText = dialog.getByLabel('Registration code')
  await expect(codeText).toHaveText(/^[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}$/)
  const reply = await handshake((await codeText.textContent())!, name)
  if ('error' in reply) throw new Error(`handshake failed: ${reply.error}`)
  await expect(dialog.getByRole('heading', { name: 'Device registered' })).toBeVisible()
  await dialog.getByRole('button', { name: 'Done' }).click()
  return reply
}

/** Signs up a new user through the api and returns its access token. */
export async function signupToken(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API_URL}/auth/signup`, {
    data: { email: uniqueEmail('devices'), name: 'Device Owner', password: 'hunter22hunter22' },
  })
  if (!res.ok()) throw new Error(`signup failed: ${res.status()} ${await res.text()}`)
  return (await res.json()).tokens.access_token
}

/** Issues a registration code for the user holding token. */
export async function issueCode(request: APIRequestContext, token: string): Promise<string> {
  const res = await request.post(`${API_URL}/devices/registration-codes`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (res.status() !== 201) throw new Error(`issuing a code failed: ${res.status()} ${await res.text()}`)
  return (await res.json()).code
}

/** A device name no other test run has used. */
export function uniqueDeviceName(prefix = 'e2e-rover') {
  return `${prefix}-${randomBytes(4).toString('hex')}`
}

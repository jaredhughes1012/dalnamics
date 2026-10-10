import { execFile, execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { promisify } from 'node:util'
import { expect, test } from '@playwright/test'
import { API_URL, AUTH_FILE, E2E_USER, REPO_ROOT, STUDIO_URL } from './env'

const CLI_BIN = path.join(REPO_ROOT, 'bin/cli')

// The browser flow is the same in every engine; the cli side is what's under test.
test.skip(({ browserName }) => browserName !== 'chromium', 'cli login runs once, in chromium')

test.beforeAll(() => {
  execFileSync('go', ['build', '-o', CLI_BIN, './services/cli/cmd'], { cwd: REPO_ROOT, stdio: 'inherit' })
})

/** Environment for a cli with its own throwaway credential file. */
function cliEnv() {
  return {
    ...process.env,
    DALNAMICS_API_URL: API_URL,
    DALNAMICS_STUDIO_URL: STUDIO_URL,
    DALNAMICS_CREDENTIAL_STORE: 'file',
    DALNAMICS_CONFIG_DIR: mkdtempSync(path.join(tmpdir(), 'dalnamics-cli-')),
  }
}

/** Starts `cli auth login --no-browser` and resolves with the URL it prints. */
function startLogin(env: NodeJS.ProcessEnv) {
  const cli = spawn(CLI_BIN, ['auth', 'login', '--no-browser'], { env })
  let stdout = ''
  cli.stdout.on('data', (chunk) => (stdout += chunk))

  const loginURL = new Promise<string>((resolve, reject) => {
    let stderr = ''
    cli.stderr.on('data', (chunk) => {
      stderr += chunk
      const match = stderr.match(/Open this URL to log in: (\S+)/)
      if (match) resolve(match[1])
    })
    cli.on('exit', (code) => reject(new Error(`cli exited (${code}) before printing a URL: ${stderr}`)))
  })
  const exited = new Promise<{ code: number | null; stdout: string }>((resolve) =>
    cli.on('exit', (code) => resolve({ code, stdout })),
  )
  return { cli, loginURL, exited }
}

async function cliStatus(env: NodeJS.ProcessEnv) {
  const { stdout } = await promisify(execFile)(CLI_BIN, ['auth', 'status'], { env })
  return stdout
}

let running: ChildProcess | undefined
test.afterEach(() => running?.kill())

test('cli logs in through a signed-in browser', async ({ browser }) => {
  const env = cliEnv()
  const login = startLogin(env)
  running = login.cli

  const context = await browser.newContext({ storageState: AUTH_FILE })
  const page = await context.newPage()
  await page.goto(await login.loginURL)
  await expect(page.getByText(`signed in as ${E2E_USER.name} (${E2E_USER.email})`)).toBeVisible()
  await page.getByRole('button', { name: 'Authorize' }).click()

  // Studio hands off to the cli's loopback server, which renders the final page.
  await expect(page.getByText('The cli is logged in. You can close this tab.')).toBeVisible()
  const { code, stdout } = await login.exited
  expect(code).toBe(0)
  expect(stdout).toContain(`Logged in to ${API_URL} as ${E2E_USER.name} <${E2E_USER.email}>`)
  expect(await cliStatus(env)).toContain(`as ${E2E_USER.name} <${E2E_USER.email}>`)
  await context.close()
})

test('cli login sends a signed-out browser through login first', async ({ page }) => {
  const env = cliEnv()
  const login = startLogin(env)
  running = login.cli

  await page.goto(await login.loginURL)
  await expect(page).toHaveURL(/\/login\?redirect=/)
  await page.getByRole('button', { name: `Continue as ${E2E_USER.email}` }).click()
  await page.getByRole('button', { name: 'Authorize' }).click()

  await expect(page.getByText('The cli is logged in. You can close this tab.')).toBeVisible()
  expect((await login.exited).code).toBe(0)
  expect(await cliStatus(env)).toContain(E2E_USER.email)
})

test('cancelling in the browser fails the cli login', async ({ browser }) => {
  const login = startLogin(cliEnv())
  running = login.cli

  const context = await browser.newContext({ storageState: AUTH_FILE })
  const page = await context.newPage()
  await page.goto(await login.loginURL)
  await page.getByRole('button', { name: 'Cancel' }).click()

  await expect(page.getByText('Login cancelled')).toBeVisible()
  expect((await login.exited).code).toBe(1)
  await context.close()
})

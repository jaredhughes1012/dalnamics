import { expect, type Page } from '@playwright/test'

/**
 * Signs in through studio's dev login buttons, the same flow a developer uses.
 * Use this instead of the shared AUTH_FILE session in tests that end the
 * session (e.g. logout), since revoking it would sign out every other test.
 */
export async function devLogin(page: Page, email: string) {
  await page.goto('/login')
  await page.getByRole('button', { name: `Continue as ${email}` }).click()
  await expect(page.getByRole('heading', { name: /^Hello, / })).toBeVisible()
}

/** Returns an email no other test run has used. */
export function uniqueEmail(prefix = 'user') {
  return `${prefix}+${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`
}

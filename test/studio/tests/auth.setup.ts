import { test as setup } from '@playwright/test'
import { AUTH_FILE, E2E_USER } from './env'
import { devLogin } from './fixtures'

setup('sign in the e2e dev user', async ({ page }) => {
  await devLogin(page, E2E_USER.email)
  await page.context().storageState({ path: AUTH_FILE })
})

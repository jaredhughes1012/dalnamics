import { expect, test } from '@playwright/test'
import { AUTH_FILE, E2E_USER } from './env'

test.use({ storageState: AUTH_FILE })

test('a saved session opens straight to home', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: `Hello, ${E2E_USER.name}` })).toBeVisible()
  await expect(page.getByText('Success: api is ok')).toBeVisible()
})

test('the account menu shows the user and switches theme', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Account' }).click()
  await expect(page.getByRole('menu').getByText(E2E_USER.email)).toBeVisible()

  await page.getByRole('menuitemradio', { name: 'Dark' }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)

  await page.reload()
  await expect(page.locator('html')).toHaveClass(/dark/)
})

test('the session survives a reload', async ({ page }) => {
  await page.goto('/')
  await page.reload()

  await expect(page.getByRole('heading', { name: `Hello, ${E2E_USER.name}` })).toBeVisible()
})

test('signed-in users skip the login page', async ({ page }) => {
  await page.goto('/login')

  await expect(page).toHaveURL('/')
})

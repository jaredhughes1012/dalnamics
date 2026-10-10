import { expect, test, type APIRequestContext } from '@playwright/test'
import { E2E_USER } from './env'
import { devLogin, uniqueEmail } from './fixtures'

async function createAccount(request: APIRequestContext) {
  const account = { email: uniqueEmail('login'), name: 'Grace Hopper', password: 'compiler-1952' }
  const res = await request.post('/api/auth/signup', { data: account })
  expect(res.status()).toBe(201)
  return account
}

test('log in with email and password, then log out', async ({ page, request }) => {
  const account = await createAccount(request)

  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page.getByRole('heading', { name: 'Hello, Grace Hopper' })).toBeVisible()

  await page.getByRole('button', { name: 'Log out' }).click()
  await expect(page).toHaveURL(/\/login/)

  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)
})

test('a wrong password is rejected', async ({ page, request }) => {
  const account = await createAccount(request)

  await page.goto('/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill('not-the-password')
  await page.getByRole('button', { name: 'Log in' }).click()

  await expect(page.getByText('invalid email or password')).toBeVisible()
  await expect(page).toHaveURL(/\/login/)
})

test('dev users log in with one click', async ({ page }) => {
  await devLogin(page, E2E_USER.email)

  await expect(page.getByRole('heading', { name: `Hello, ${E2E_USER.name}` })).toBeVisible()
})

test('dev users cannot log in with a password', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill(E2E_USER.email)
  await page.getByLabel('Password').fill('anything-at-all')
  await page.getByRole('button', { name: 'Log in' }).click()

  await expect(page.getByText('invalid email or password')).toBeVisible()
})

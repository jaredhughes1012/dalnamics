import { expect, test } from '@playwright/test'
import { uniqueEmail } from './fixtures'

test('create an account', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)
  await page.getByRole('link', { name: 'Create one' }).click()

  await page.getByLabel('Name').fill('Ada Lovelace')
  await page.getByLabel('Email').fill(uniqueEmail('signup'))
  await page.getByLabel('Password').fill('analytical-engine')
  await page.getByRole('button', { name: 'Create account' }).click()

  await expect(page.getByRole('heading', { name: 'Hello, Ada Lovelace' })).toBeVisible()
})

test('an email can only be registered once', async ({ page, request }) => {
  const email = uniqueEmail('dupe')
  const res = await request.post('/api/auth/signup', { data: { email, name: 'First', password: 'password-1' } })
  expect(res.status()).toBe(201)

  await page.goto('/signup')
  await page.getByLabel('Name').fill('Second')
  await page.getByLabel('Email').fill(email.toUpperCase())
  await page.getByLabel('Password').fill('password-2')
  await page.getByRole('button', { name: 'Create account' }).click()

  await expect(page.getByText('an account with that email already exists')).toBeVisible()
})

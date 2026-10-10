import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))

export const REPO_ROOT = path.resolve(here, '../../..')
export const STUDIO_URL = process.env.STUDIO_URL ?? 'http://localhost:5173'
export const API_URL = process.env.API_URL ?? 'http://localhost:8080'

/** Dev user signed in by auth.setup.ts. Must be listed in the api's DEV_EMAILS. */
export const E2E_USER = { email: 'e2e@dalnamics.local', name: 'e2e' }

/** Saved browser state for E2E_USER; use with test.use({ storageState: AUTH_FILE }). */
export const AUTH_FILE = path.join(here, '../playwright/.auth/e2e.json')

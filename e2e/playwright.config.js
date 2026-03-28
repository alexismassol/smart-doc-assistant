/**
 * playwright.config.js — Configuration Playwright pour les tests E2E
 * Uses: Playwright Test (chromium headless), serveurs backend + frontend locaux
 *
 * Les tests E2E requièrent que backend (port 8000) et frontend (port 5173)
 * soient démarrés. Ils sont exécutés avec `npm run test:e2e`.
 */
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  retries: 1,
  workers: 1,
  reporter: 'list',
  timeout: 30_000,

  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'off',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Pas de webServer ici — on suppose que dev.sh est déjà lancé
  // Pour les tests CI : `npm run dev &` puis `npm run test:e2e`
})

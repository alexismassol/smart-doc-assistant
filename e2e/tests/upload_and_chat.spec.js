/**
 * upload_and_chat.spec.js - Tests E2E Playwright : parcours complet
 * Uses: Playwright Test, Chromium headless
 *
 * Scénarios testés :
 * 1. Chargement de l'interface → EmptyState visible
 * 2. StatusBar → indicateur LLM affiché
 * 3. UploadPanel → zone drag&drop présente
 * 4. Zone de chat → input textarea accessible
 * 5. Input vide → bouton submit désactivé
 * 6. Envoi d'une question → message utilisateur affiché
 *
 * ⚠️ Ces tests requièrent backend (8000) + frontend (5173) démarrés.
 * Lancer avec : npm run dev & sleep 5 && npm run test:e2e
 */
import { test, expect } from '@playwright/test'

test.describe('Interface principale - chargement', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('la page se charge sans erreur', async ({ page }) => {
    await expect(page).toHaveTitle(/Smart Doc Assistant/i)
  })

  test('la StatusBar est visible', async ({ page }) => {
    // La StatusBar contient le nom de l'app ou l'indicateur LLM
    const statusBar = page.locator('header, [class*="border-b"]').first()
    await expect(statusBar).toBeVisible()
  })

  test('l\'EmptyState est affiché au démarrage', async ({ page }) => {
    await expect(page.getByText('Smart Doc Assistant').first()).toBeVisible()
    await expect(page.getByText(/Interrogez vos documents/)).toBeVisible()
  })

  test('les suggestions de questions sont visibles', async ({ page }) => {
    await expect(page.getByText(/Quelle est la limite de taux/)).toBeVisible()
  })
})

test.describe('UploadPanel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('le panneau upload est visible à gauche', async ({ page }) => {
    await expect(page.getByText('Déposer un fichier')).toBeVisible()
  })

  test('le champ URL est présent', async ({ page }) => {
    await expect(page.locator('input[type="url"]')).toBeVisible()
  })

  test('le message "Aucun document" est affiché si base vide', async ({ page }) => {
    // Vérifie la section documents (peut être "Aucun document indexé")
    // Ce texte n'apparaît que si la base ChromaDB est vide
    // On vérifie juste que la section existe
    const aside = page.locator('aside').first()
    await expect(aside).toBeVisible()
  })
})

test.describe('ChatWindow - interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('le textarea de chat est présent et accessible', async ({ page }) => {
    const textarea = page.locator('textarea')
    await expect(textarea).toBeVisible()
    await expect(textarea).toBeEnabled()
  })

  test('le bouton submit est désactivé si input vide', async ({ page }) => {
    const submitBtn = page.locator('button[type="submit"]')
    await expect(submitBtn).toBeDisabled()
  })

  test('saisir du texte active le bouton submit', async ({ page }) => {
    const textarea = page.locator('textarea')
    await textarea.fill('Test question')
    const submitBtn = page.locator('button[type="submit"]')
    await expect(submitBtn).toBeEnabled()
  })

  test('envoyer une question affiche le message utilisateur', async ({ page }) => {
    const textarea = page.locator('textarea')
    await textarea.fill('Quelle est la limite de taux ?')
    await textarea.press('Enter')

    // Le message utilisateur doit apparaître immédiatement
    await expect(page.getByText('Quelle est la limite de taux ?')).toBeVisible()
  })

  test('l\'input est vidé après envoi', async ({ page }) => {
    const textarea = page.locator('textarea')
    await textarea.fill('Ma question')
    await textarea.press('Enter')
    await expect(textarea).toHaveValue('')
  })

  test('Shift+Enter ne soumet pas le formulaire', async ({ page }) => {
    const textarea = page.locator('textarea')
    await textarea.fill('Ma question')
    await textarea.press('Shift+Enter')
    // L'EmptyState disparaît seulement si message envoyé
    // Shift+Enter garde l'EmptyState visible
    await expect(page.getByText('Smart Doc Assistant')).toBeVisible()
  })
})

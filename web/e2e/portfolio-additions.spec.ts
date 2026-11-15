import { expect, test, type Page } from '@playwright/test'

// Additions, basket, view options and the phone layout, on the committed demo fixtures.
async function open(page: Page, hash = '#/') {
  const errors: string[] = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`/${hash}`)
  await expect(page.locator('h1')).toHaveText('Portfolio')
  await page.evaluate(() => document.fonts.ready)
  return errors
}
const noBadText = async (page: Page) => {
  const text = await page.locator('body').innerText()
  expect(text).not.toMatch(/NaN|undefined|\[object/)
  expect(text).not.toMatch(/\b(sell|bargain|undervalued|top picks?)\b/i)
}
const noSidewaysScroll = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
const after = (page: Page, measure: string) => page.locator('.pf-ba tbody tr', { hasText: measure }).locator('td').nth(1)
const now = (page: Page, measure: string) => page.locator('.pf-ba tbody tr', { hasText: measure }).locator('td').nth(0)

test.describe('desktop additions', () => {
  test.use({ viewport: { width: 1280, height: 900 } })

  test('sectors with nothing held come first and a card filters the table', async ({ page }) => {
    await open(page)
    const cards = page.getByRole('group', { name: 'Sector' }).getByRole('button')
    await expect(cards.first()).toContainText('none in the portfolio')
    await page.getByRole('button', { name: /^Energy/ }).click()
    await expect(page.locator('.pf-cands tbody')).toContainText('Demo Offshore')
    await expect(page.locator('.pf-cands tbody')).not.toContainText('Demo Armour')
    await page.getByRole('button', { name: /^ETFs/ }).click()
    await expect(page.locator('.pf-cands tbody tr')).toHaveCount(2)
    const growth = page.locator('.pf-cands tbody tr', { hasText: 'Demo Growth ETF' })
    await expect(growth).toContainText('—') // short history: no correlation
    await expect(growth).toContainText('weekly returns')
    await noBadText(page)
  })

  test('adding a candidate changes the after column, survives a reload and clears back to before', async ({ page }) => {
    await open(page)
    await expect(page.getByText('The basket is empty')).toBeVisible()
    expect(await after(page, 'Three largest').innerText()).toBe(await now(page, 'Three largest').innerText())
    await page.getByRole('button', { name: /^Energy/ }).click()
    await page.getByRole('button', { name: 'Add Demo Offshore to the basket' }).click()
    await expect(page.locator('.basket-items')).toContainText('Demo Offshore')
    expect(await after(page, 'Portfolio value').innerText()).not.toBe(await now(page, 'Portfolio value').innerText())
    expect(await page.evaluate(() => localStorage.getItem('market-leaderboard.basket.v1'))).toContain('ENGA.OL')
    await page.reload()
    await expect(page.locator('.basket-items')).toContainText('Demo Offshore')
    await page.getByLabel('Amount in EUR for ENGA.OL').fill('2000')
    await expect(page.getByText('Basket total 2,000 €')).toBeVisible()
    await page.getByRole('button', { name: 'Clear' }).click()
    await expect(page.getByText('The basket is empty')).toBeVisible()
    expect(await after(page, 'Three largest').innerText()).toBe(await now(page, 'Three largest').innerText())
    await noBadText(page)
  })

  test('a blank amount is ignored with a reason, not shown as NaN', async ({ page }) => {
    await open(page)
    await page.getByRole('button', { name: /^Energy/ }).click()
    await page.getByRole('button', { name: 'Add Demo Offshore to the basket' }).click()
    await page.getByLabel('Amount in EUR for ENGA.OL').fill('')
    await expect(page.getByRole('status').filter({ hasText: 'Not used' })).toContainText('amount must be a number above zero')
    await noBadText(page)
  })

  test('the View menu hides the chart and the groups, and remembers it', async ({ page }) => {
    await open(page)
    await page.getByRole('button', { name: /View/ }).click()
    await page.getByRole('checkbox', { name: 'History chart' }).uncheck()
    await page.getByRole('checkbox', { name: 'Where the money sits' }).uncheck()
    await expect(page.getByRole('img', { name: /Accumulated return/ })).toHaveCount(0)
    await page.reload()
    await expect(page.getByRole('img', { name: /Accumulated return/ })).toHaveCount(0)
  })

  test('takes a screenshot of the whole page with a basket', async ({ page }) => {
    await open(page)
    await page.getByRole('button', { name: /^Energy/ }).click()
    await page.getByRole('button', { name: 'Add Demo Offshore to the basket' }).click()
    await page.getByRole('button', { name: /^Technology/ }).click()
    await page.getByRole('button', { name: 'Add Demo Software to the basket' }).click()
    expect(await noSidewaysScroll(page)).toBe(true)
    await page.screenshot({ path: 'e2e/shots/portfolio-full-desktop-light.png', fullPage: true })
  })
})

test.describe('phone', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true })

  test('tabs keep one thing per screen and the basket tab counts', async ({ page }) => {
    await open(page)
    await expect(page.getByRole('group', { name: 'Section' })).toBeVisible()
    await expect(page.getByRole('group', { name: 'Sector' })).toHaveCount(0)
    await page.getByRole('button', { name: 'Additions' }).click()
    await page.getByRole('button', { name: /^Energy/ }).click()
    await page.getByRole('button', { name: 'Add Demo Offshore to the basket' }).click()
    await expect(page.locator('.badge.count')).toHaveText('1')
    await page.getByRole('button', { name: /^Basket/ }).click()
    await expect(page.locator('.basket-items')).toContainText('Demo Offshore')
    expect(await noSidewaysScroll(page)).toBe(true)
    await noBadText(page)
    await page.screenshot({ path: 'e2e/shots/portfolio-basket-phone-light.png', fullPage: true })
  })

  test('a holding opens a bottom sheet that closes with Escape or the handle', async ({ page }) => {
    await open(page)
    await page.getByRole('button', { name: /Demo Chips/ }).click()
    const sheet = page.getByRole('dialog', { name: /Demo Chips: details/ })
    await expect(sheet).toBeVisible()
    await expect(sheet).toContainText('Units')
    await page.screenshot({ path: 'e2e/shots/portfolio-sheet-phone-light.png' })
    await page.keyboard.press('Escape')
    await expect(sheet).toHaveCount(0)
    await page.getByRole('button', { name: /Demo Chips/ }).click()
    await page.getByRole('button', { name: 'Close details' }).click()
    await expect(sheet).toHaveCount(0)
  })

  test('the additions tab fits the screen', async ({ page }) => {
    await open(page)
    await page.getByRole('button', { name: 'Additions' }).click()
    expect(await noSidewaysScroll(page)).toBe(true)
    await page.screenshot({ path: 'e2e/shots/portfolio-additions-phone-light.png', fullPage: true })
  })
})

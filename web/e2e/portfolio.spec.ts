import { expect, test, type Page } from '@playwright/test'

// The Portfolio view on the committed demo fixtures (invented holdings; see config/portfolio.example.toml).
const SIZES = [
  { name: 'desktop', width: 1280, height: 900 },
  { name: 'phone', width: 390, height: 844 },
] as const
const SCHEMES = ['light', 'dark'] as const

async function open(page: Page, hash = '#/') {
  const errors: string[] = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`/${hash}`)
  await expect(page.locator('h1')).toHaveText('Portfolio')
  await page.evaluate(() => document.fonts.ready)
  return errors
}

const noSidewaysScroll = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)

for (const size of SIZES) {
  for (const scheme of SCHEMES) {
    test.describe(`portfolio ${size.name} ${scheme}`, () => {
      test.use({ viewport: { width: size.width, height: size.height }, colorScheme: scheme, deviceScaleFactor: 1 })

      test('renders without errors, sideways scroll, NaN or undefined', async ({ page }) => {
        const errors = await open(page)
        expect(await noSidewaysScroll(page)).toBe(true)
        const text = await page.locator('body').innerText()
        expect(text).not.toMatch(/NaN|undefined|\[object/)
        expect(text).not.toMatch(/\b(sell|bargain|undervalued|top picks?)\b/i)
        await page.screenshot({ path: `e2e/shots/portfolio-${size.name}-${scheme}.png`, fullPage: true })
        expect(errors).toEqual([])
      })
    })
  }
}

test.describe('portfolio headlines', () => {
  test('shows upbeat counts, hides downbeat stories until asked, and lists discovered names', async ({ page }) => {
    await open(page)
    const news = page.locator('section[aria-labelledby="news-h"]')
    await expect(news.getByRole('heading', { name: 'Headlines, last 30 days' })).toBeVisible()
    await expect(news).toContainText('of 100+ stories')
    await expect(news).toContainText('0 upbeat · 0 downbeat')
    await expect(news).toContainText('no upbeat or downbeat story')
    await expect(news).toContainText('more downbeat than upbeat')
    await expect(news).toContainText('it is weak evidence')
    await news.getByText('Acme Corp').click()
    await expect(news.getByRole('link', { name: 'Acme opens a second plant in Oulu' })).toBeVisible()
    await expect(news.getByRole('link', { name: 'Acme shares fall after a production delay' })).toHaveCount(0)
    await news.getByRole('button', { name: 'All stories' }).click()
    await expect(news.getByRole('link', { name: 'Acme shares fall after a production delay' })).toBeVisible()
    await news.getByRole('button', { name: 'Upbeat only' }).click()
    await expect(news.getByRole('heading', { name: 'Research candidates' })).toBeVisible()
    await news.getByText('NewCo Oyj').click()
    await expect(news.getByRole('link', { name: 'Show HN: NewCo publishes its sensor design' })).toBeVisible()
    await expect(news).toContainText('not a recommendation')
    await expect(news.getByRole('heading', { name: 'Unusually upbeat this week' })).toBeVisible()
    await news.locator('summary', { hasText: 'Spark Energy' }).click()
    await expect(news.getByRole('link', { name: 'Spark Energy raises its outlook after record orders' })).toBeVisible()
    await expect(news).toContainText('not a reason to act')
  })
})

test.describe('portfolio behaviour', () => {
  test.use({ viewport: { width: 1280, height: 900 } })

  test('lists every demo position, with the unpriced one left out of the weights', async ({ page }) => {
    await open(page)
    const rows = page.locator('[aria-labelledby="holdings-h"] .pf-table tbody tr:not(.detail)')
    await expect(rows).toHaveCount(5)
    const unpriced = rows.filter({ hasText: 'Demo Delisted' })
    await expect(unpriced).toContainText('no price')
    await expect(unpriced.locator('td').last()).toHaveText('—')
  })

  test('a row opens its details and the research panel link for a share in the universe', async ({ page }) => {
    await open(page)
    await page.getByRole('button', { name: /Demo Chips/ }).click()
    const detail = page.locator('[aria-labelledby="holdings-h"] .pf-table tr.detail')
    await expect(detail).toContainText('Cost')
    await detail.getByRole('link', { name: 'Open research panel' }).click()
    await expect(page.getByRole('complementary', { name: /Research: Demo Chips/ })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('complementary')).toHaveCount(0)
  })

  test('the View menu adds price, units and cost', async ({ page }) => {
    await open(page)
    await expect(page.getByRole('columnheader', { name: 'Units' })).toHaveCount(0)
    await page.getByRole('button', { name: /View/ }).click()
    await page.getByLabel('Extra columns (price, units, cost)').check()
    await expect(page.getByRole('columnheader', { name: 'Units' })).toBeVisible()
  })

  test('the chart has a text summary and a range switch', async ({ page }) => {
    await open(page)
    const chart = page.getByRole('img', { name: /Accumulated return, weekly points/ })
    await expect(chart).toBeVisible()
    const before = await chart.getAttribute('aria-label')
    await page.getByRole('group', { name: 'Range' }).getByRole('button', { name: '3M' }).click()
    expect(await chart.getAttribute('aria-label')).not.toBe(before)
    await page.getByText('Weekly points as a table').click()
    await expect(page.locator('details.how table tbody tr').first()).toBeVisible()
  })

  test('the command field opens a view or a company and says when nothing matches', async ({ page }) => {
    await open(page)
    await page.getByLabel('Go to a ticker or view').fill('nonsense')
    await page.keyboard.press('Enter')
    await expect(page.getByRole('status')).toContainText('Nothing matches')
    await page.getByLabel('Go to a ticker or view').fill('screener')
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/#\/screener$/)
  })
})

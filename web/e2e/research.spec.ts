import { expect, test, type Page } from '@playwright/test'

async function open(page: Page, hash: string) {
  const errors: string[] = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`/${hash}`)
  await expect(page.locator('h1, .rpanel h2').first()).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  return errors
}
const noSidewaysScroll = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)

for (const size of [{ name: 'desktop', width: 1440, height: 900 }, { name: 'phone', width: 390, height: 844 }] as const) {
  for (const scheme of ['light', 'dark'] as const) {
    test.describe(`${size.name} ${scheme}`, () => {
      test.use({ viewport: { width: size.width, height: size.height }, colorScheme: scheme, deviceScaleFactor: 1 })
      for (const [name, hash] of [
        ['candidates', '#/'],
        ['screener', '#/screener'],
        ['screener-panel', '#/screener?c=DEMA'],
        ['candidates-panel', '#/?c=ENGA.OL'],
        ['data', '#/data'],
      ] as const) {
        test(`${name}: renders without errors or sideways scroll`, async ({ page }) => {
          const errors = await open(page, hash)
          expect(await noSidewaysScroll(page)).toBe(true)
          await expect(page.locator('body')).not.toContainText(/NaN|undefined|Infinity/)
          await page.screenshot({ path: `e2e/shots/${name}-${size.name}-${scheme}.png`, fullPage: true })
          expect(errors).toEqual([])
        })
      }
    })
  }
}

test.describe('candidates', () => {
  test('cards give the case for and against, and the evidence is one click away', async ({ page }) => {
    await open(page, '#/')
    const cards = page.locator('article.cand')
    await expect(cards).toHaveCount(2)
    await expect(cards.first().getByText('Why look closer')).toBeVisible()
    await expect(cards.first().getByText('What argues against')).toBeVisible()
    await expect(page.getByText(/Not advice/).first()).toBeVisible()
    await page.getByText('How these are picked, and what has been tested').click()
    await expect(page.getByText(/free data has today's fundamentals only/).first()).toBeVisible()
  })

  test('a filter narrows the cards and lives in the address', async ({ page }) => {
    await open(page, '#/')
    await page.getByLabel('Watchlist').selectOption('us_big_tech')
    expect(page.url()).toContain('list=us_big_tech')
    await expect(page.getByText('No candidate matches these filters')).toBeVisible()
    await page.getByLabel('Watchlist').selectOption('')
    await expect(page.locator('article.cand')).toHaveCount(2)
  })
})

test.describe('research panel', () => {
  test.use({ viewport: { width: 1440, height: 900 } })

  test('opens beside the table from a company name, by keyboard, and Esc closes it', async ({ page }) => {
    await open(page, '#/screener')
    const link = page.getByRole('link', { name: 'Demo Chips', exact: true })
    await link.focus()
    await page.keyboard.press('Enter')
    const panel = page.getByRole('complementary', { name: 'Research: Demo Chips' })
    await expect(panel).toBeVisible()
    await expect(page.getByRole('table')).toBeVisible() // the table stays next to it
    expect(page.url()).toContain('c=DEMA')
    await expect(panel.getByRole('link', { name: 'Close research panel' })).toBeFocused()
    for (const text of ['Four measures', 'What this cannot tell you', 'Cheap or expensive?', 'The usual numbers', 'Headlines']) {
      await expect(panel.getByRole('heading', { name: text })).toBeVisible()
    }
    await expect(panel.getByText(/grew \d+-fold/)).toBeVisible() // the caveat for a P/E that fell because profit rose
    await expect(panel.getByText('Price divided by last year’s profit per share', { exact: false })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(panel).toHaveCount(0)
    expect(page.url()).not.toContain('c=')
  })

  test('shows converted figures, an inconsistent figure and headlines as plain text links', async ({ page }) => {
    await open(page, '#/screener?c=ENGA.OL')
    await expect(page.getByText(/reports in USD and trades in NOK/)).toBeVisible()
    await page.goto('/#/screener?c=FINA.HE')
    await expect(page.getByText('Some valuation figures look inconsistent with each other', { exact: false })).toBeVisible()
    await page.goto('/#/screener?c=DEMD')
    const headline = page.getByRole('link', { name: 'Demo Search shares fall after its quarterly report' })
    await expect(headline).toHaveAttribute('rel', 'noopener noreferrer')
    await expect(page.getByText('Yahoo’s text, shown as received').first()).toBeVisible()
    await page.goto('/#/screener?c=NRDA.HE')
    await expect(page.getByText(/Not a candidate: profitable in \d of its last 4 fiscal years/)).toBeVisible()
  })

  test('an unknown company in the address is ignored', async ({ page }) => {
    await open(page, '#/screener?c=NOPE')
    await expect(page.locator('.rpanel')).toHaveCount(0)
    await expect(page.getByRole('table')).toBeVisible()
  })
})

test.describe('screener', () => {
  test('sorts by keyboard and counts match the table', async ({ page }) => {
    await open(page, '#/screener')
    const rows = page.locator('tbody tr')
    await expect(rows).toHaveCount(15)
    await expect(page.locator('.kpis dd').first()).toHaveText('15')
    await page.locator('thead').getByRole('button', { name: 'P/E', exact: true }).focus()
    await page.keyboard.press('Enter')
    const sorted = page.locator('thead th[aria-sort]')
    await expect(sorted).toHaveCount(1)
    await expect(sorted).toHaveAttribute('aria-sort', 'ascending')
    await expect(sorted).toContainText('P/E')
    const values = (await page.locator('tbody tr td:nth-child(4)').allTextContents()).filter((v) => v !== '—').map(Number)
    expect(values).toEqual([...values].sort((a, b) => a - b))
    await page.getByLabel('Sector').selectOption('Energy')
    await expect(rows).toHaveCount(3)
  })
})

test('on a phone the panel is the page and closing returns to the list', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page, '#/')
  await page.locator('article.cand h2 a').first().click()
  await expect(page.locator('.rpanel')).toBeVisible()
  await expect(page.locator('article.cand')).toHaveCount(0)
  expect(await noSidewaysScroll(page)).toBe(true)
  await page.getByRole('link', { name: 'Close research panel' }).click()
  await expect(page.locator('article.cand')).toHaveCount(2)
})

test('mix: the slider changes the weight and the map shows weight and share of risk', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.addInitScript(() => localStorage.setItem('market-leaderboard.mixes.v1', JSON.stringify({
    a: { name: 'Mix A', items: [{ ticker: 'DEMA', weight: 50 }, { ticker: 'DEMB', weight: 30 }, { ticker: 'ENGA.OL', weight: 20 }] }, b: null })))
  await open(page, '#/mix')
  const map = page.getByRole('img', { name: /Map of the mix/ })
  await expect(map).toBeVisible()
  await expect(map.locator('.maptile')).toHaveCount(3)
  await expect(map.getByText(/50 % · risk \d+ %/)).toBeVisible()
  await page.getByLabel('Weight slider for Demo Chips').fill('80')
  await expect(page.getByLabel('Weight of Demo Chips')).toHaveValue('80')
  await expect(map.getByText(/62 % · risk/)).toBeVisible() // 80 of 130
})

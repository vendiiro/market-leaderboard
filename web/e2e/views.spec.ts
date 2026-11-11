import { expect, test, type Page } from '@playwright/test'

const SIZES = [
  { name: 'desktop', width: 1280, height: 900 },
  { name: 'phone', width: 390, height: 844 },
] as const
const SCHEMES = ['light', 'dark'] as const
const PAGES = [
  { name: 'overview', hash: '#/' },
  { name: 'leaderboard', hash: '#/list/fi_small' },
  { name: 'leaderboard-us', hash: '#/list/us_big_tech?period=1d' },
]

async function open(page: Page, hash: string) {
  const errors: string[] = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`/${hash}`)
  await expect(page.locator('h1')).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  return errors
}

const noSidewaysScroll = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)

for (const size of SIZES) {
  for (const scheme of SCHEMES) {
    test.describe(`${size.name} ${scheme}`, () => {
      test.use({ viewport: { width: size.width, height: size.height }, colorScheme: scheme, deviceScaleFactor: 1 })
      for (const p of PAGES) {
        test(`${p.name}: renders without errors or sideways scroll`, async ({ page }) => {
          const errors = await open(page, p.hash)
          expect(await noSidewaysScroll(page)).toBe(true)
          await page.screenshot({ path: `e2e/shots/${p.name}-${size.name}-${scheme}.png`, fullPage: true })
          expect(errors).toEqual([])
        })
      }
    })
  }
}

test.describe('leaderboard behaviour', () => {
  test('default order is the engine rank and stale rows have none', async ({ page }) => {
    await open(page, '#/list/fi_small')
    const ranks = await page.locator('tbody td.rank').allTextContents()
    expect(ranks).toEqual(['1', '2', '—'])
    await expect(page.getByText('No data tonight:')).toBeVisible()
    await expect(page.getByText('Demo Housing (FIND.HE)')).toBeVisible()
  })

  test('columns sort with the keyboard and the state is in the address', async ({ page }) => {
    await open(page, '#/list/us_big_tech')
    const header = page.getByRole('columnheader', { name: 'Company' })
    await header.getByRole('button').focus()
    await page.keyboard.press('Enter')
    await expect(header).toHaveAttribute('aria-sort', 'ascending')
    expect(page.url()).toContain('sort=name:asc')
    const names = await page.locator('tbody th[scope=row] b').allTextContents()
    expect(names).toEqual([...names].sort())
    await page.keyboard.press('Enter')
    await expect(header).toHaveAttribute('aria-sort', 'descending')
  })

  test('the period picker changes the ranking column and survives a reload', async ({ page }) => {
    await open(page, '#/list/us_big_tech')
    await page.getByRole('group', { name: 'Return period' }).getByRole('button', { name: '1d' }).click()
    expect(page.url()).toContain('period=1d')
    await page.reload()
    await expect(page.getByRole('group', { name: 'Return period' }).getByRole('button', { name: '1d' })).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('tbody tr').last().locator('th[scope=row] b')).toHaveText('Demo Search') // the flagged 6% fall
  })

  test('the dip flag explains itself', async ({ page }) => {
    await open(page, '#/list/us_big_tech')
    await page.getByRole('button', { name: 'Dip' }).click()
    await expect(page.getByText('Flagged because:')).toBeVisible()
    await expect(page.getByText(/Untested screen rule: a description/)).toBeVisible()
  })

  test('on a phone a row expands to show every number, one row at a time', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await open(page, '#/list/us_big_tech')
    const rows = page.locator('tbody button.rowbtn')
    await rows.nth(0).click()
    await expect(rows.nth(0)).toHaveAttribute('aria-expanded', 'true')
    const detail = page.locator('tr.detail')
    for (const label of ['1d return', '1w return', 'YTD return', '1y return', 'From 52-week high', 'Volatility 1y', 'Checks passed']) {
      await expect(detail.getByText(label, { exact: true })).toBeVisible()
    }
    await rows.nth(1).focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('tr.detail')).toHaveCount(1)
    await expect(rows.nth(0)).toHaveAttribute('aria-expanded', 'false')
    expect(await noSidewaysScroll(page)).toBe(true)
  })
})

test('overview links to a list and shows the data state', async ({ page }) => {
  await open(page, '#/')
  await expect(page.getByText('15 of 16 companies have prices')).toBeVisible()
  await expect(page.getByText('Demo data')).toBeVisible()
  await page.getByRole('link', { name: 'Nordic energy' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Nordic energy')
})

test('a schema mismatch is an error message, not a blank page', async ({ page }) => {
  await page.route('**/fixtures/meta.json*', (r) => r.fulfill({ contentType: 'text/javascript', body: 'export default {"schema_version": 99}' }))
  await page.goto('/#/')
  await expect(page.getByRole('alert')).toContainText('meta.json has schema version 99')
})

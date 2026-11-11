import { readFileSync } from 'node:fs'
import { expect, test, type Page } from '@playwright/test'

const KEY = 'market-leaderboard.mixes.v1'
const MIX_A = { name: 'Mix A', items: [{ ticker: 'DEMA', weight: 40 }, { ticker: 'DEMB', weight: 20 }, { ticker: 'ENGA.OL', weight: 20 }, { ticker: 'DEFC.PA', weight: 20 }] }
const MIX_B = { name: 'Mix B', items: [...MIX_A.items, { ticker: 'NRDA.HE', weight: 30 }, { ticker: 'DEFB.L', weight: 30 }] }

async function open(page: Page, hash: string, saved?: object) {
  const errors: string[] = []
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))
  page.on('pageerror', (e) => errors.push(e.message))
  if (saved) await page.addInitScript(([k, v]) => localStorage.setItem(k, v), [KEY, JSON.stringify(saved)] as const)
  await page.goto(`/${hash}`)
  await expect(page.locator('h1')).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
  return errors
}
const noSidewaysScroll = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)

for (const size of [{ name: 'desktop', width: 1280, height: 900 }, { name: 'phone', width: 390, height: 844 }] as const) {
  for (const scheme of ['light', 'dark'] as const) {
    test.describe(`${size.name} ${scheme}`, () => {
      test.use({ viewport: { width: size.width, height: size.height }, colorScheme: scheme, deviceScaleFactor: 1 })
      for (const [name, hash, saved] of [
        ['mix-empty', '#/mix', undefined],
        ['mix-one', '#/mix', { a: MIX_A, b: null }],
        ['mix-compare', '#/mix', { a: MIX_A, b: MIX_B }],
        ['movers', '#/movers', undefined],
      ] as const) {
        test(`${name}: renders without errors or sideways scroll`, async ({ page }) => {
          const errors = await open(page, hash, saved)
          expect(await noSidewaysScroll(page)).toBe(true)
          await expect(page.locator('body')).not.toContainText('NaN')
          await page.screenshot({ path: `e2e/shots/${name}-${size.name}-${scheme}.png`, fullPage: true })
          expect(errors).toEqual([])
        })
      }
    })
  }
}

test.describe('mix', () => {
  test('build a mix by keyboard, see the numbers, and find it again after a reload', async ({ page }) => {
    await open(page, '#/mix')
    await expect(page.getByText('No companies yet')).toBeVisible()
    const input = page.getByPlaceholder('Add a company or ticker')
    for (const t of ['DEMA', 'demo software']) { // by ticker and by name, any case
      await input.fill(t)
      await input.press('Enter')
    }
    await expect(page.getByText('Mix volatility')).toBeVisible()
    await expect(page.locator('.tiles dd').nth(1)).toHaveText('2.0') // two equal weights
    await page.getByLabel('Weight of Demo Chips').fill('30')
    await expect(page.locator('.tiles dd').nth(1)).toHaveText('1.6') // 1 / (0.75² + 0.25²)
    await expect(page.getByText('Weights add up to 40')).toBeVisible()
    await page.reload()
    await expect(page.getByLabel('Weight of Demo Chips')).toHaveValue('30')
  })

  test('problems are named: unknown company, duplicate, company without risk data', async ({ page }) => {
    await open(page, '#/mix', { a: { name: 'Mix A', items: [{ ticker: 'DEMA', weight: 50 }, { ticker: 'DEFC.PA', weight: 50 }, { ticker: 'GONE.XX', weight: 10 }] }, b: null })
    await expect(page.getByText('Left out, no data tonight: GONE.XX')).toBeVisible()
    await expect(page.getByText(/The risk numbers cover 50 % of the mix\. Without risk data: DEFC\.PA/)).toBeVisible()
    const input = page.getByPlaceholder('Add a company or ticker')
    await input.fill('Nokia')
    await input.press('Enter')
    await expect(page.getByRole('alert')).toContainText('is not in tonight’s data'.replace('’', "'"))
    await input.fill('DEMA')
    await input.press('Enter')
    await expect(page.getByRole('alert')).toContainText('already in the mix')
  })

  test('compare with a copy, change the copy, and the first mix stays as it was', async ({ page }) => {
    await open(page, '#/mix', { a: MIX_A, b: null })
    await page.getByRole('button', { name: 'Compare with a copy' }).click()
    const b = page.getByRole('region', { name: 'Mix B' })
    const a = page.getByRole('region', { name: 'Mix A' })
    const before = await a.locator('.tiles dd').allTextContents()
    await b.getByPlaceholder('Add a company or ticker').fill('NRDA.HE')
    await b.getByRole('button', { name: 'Add', exact: true }).click()
    await expect(b.getByLabel('Weight of Demo Refining')).toBeVisible()
    expect(await a.locator('.tiles dd').allTextContents()).toEqual(before)
    expect(await b.locator('.tiles dd').allTextContents()).not.toEqual(before)
    await expect(b.getByRole('table', { name: /Correlation/ })).toBeVisible()
  })

  test('export gives a file that import reads back; a wrong file is refused', async ({ page }) => {
    await open(page, '#/mix', { a: MIX_A, b: null })
    const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Export' }).click()])
    const path = await download.path()
    expect(JSON.parse(readFileSync(path, 'utf8')).items).toEqual(MIX_A.items)
    await page.getByRole('button', { name: 'Clear' }).click()
    await expect(page.getByText('No companies yet')).toBeVisible()
    await page.getByLabel('Import a file into Mix A').setInputFiles(path)
    await expect(page.getByLabel('Weight of Demo Chips')).toHaveValue('40')
    await page.getByLabel('Import a file into Mix A').setInputFiles({ name: 'x.json', mimeType: 'application/json', buffer: Buffer.from('{"hello":1}') })
    await expect(page.getByRole('alert')).toContainText('not a mix file')
    await expect(page.getByLabel('Weight of Demo Chips')).toHaveValue('40') // the mix is unchanged
  })

  test('corrupt saved data starts an empty mix instead of failing', async ({ page }) => {
    await page.addInitScript((k) => localStorage.setItem(k, '{broken'), KEY)
    await page.goto('/#/mix')
    await expect(page.getByText('No companies yet')).toBeVisible()
  })
})

test.describe('movers and page states', () => {
  test('movers list each company once and the flag explains itself', async ({ page }) => {
    await open(page, '#/movers')
    const falls = page.getByRole('region', { name: 'Largest falls' })
    await expect(falls.locator('tbody tr').first()).toContainText('Demo Search')
    const names = await page.locator('.board.plain tbody th b').allTextContents()
    expect(new Set(names).size).toBe(names.length)
    const flags = page.getByRole('region', { name: 'Dip flags' })
    await expect(flags).toContainText('Flagged because: 1-day')
    await expect(flags).toContainText('untested screen rule')
    await expect(page.locator('body')).not.toContainText('FINB.HE') // the stale row is never a mover
  })

  test('old data shows a banner with its date', async ({ page }) => {
    const meta = JSON.parse(readFileSync('src/fixtures/meta.json', 'utf8'))
    await page.route('**/fixtures/meta.json*', (r) =>
      r.fulfill({ contentType: 'text/javascript', body: `export default ${JSON.stringify({ ...meta, demo: false, asof: '2026-01-05' })}` }))
    await page.goto('/#/')
    await expect(page.getByText('The data is from 2026-01-05.')).toBeVisible()
    await expect(page.getByText('Demo data')).toHaveCount(0)
  })

  test('every view can be reached and used with the keyboard alone', async ({ page }) => {
    await open(page, '#/')
    for (const name of ['Leaderboards', 'Mix', 'Movers', 'Overview']) {
      await page.getByRole('link', { name, exact: true }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('link', { name, exact: true })).toHaveAttribute('aria-current', 'page')
      await expect(page.locator('h1')).toBeVisible()
    }
  })
})

// Contrast of the colour pairs the page uses for text, in both themes (WCAG 2 contrast ratio).
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const css = readFileSync(new URL('./tokens.css', import.meta.url), 'utf8')
const [lightPart, ...darkParts] = css.split('@media (prefers-color-scheme:dark)')
const tokens = (text: string) => Object.fromEntries([...text.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]]))
const light = tokens(lightPart + css.slice(css.lastIndexOf(':root{--bar'), css.lastIndexOf('@media')))
const dark = { ...light, ...tokens(darkParts.join(' ')) }

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}
function mix(a: string, b: string, share: number): string {
  const ch = (h: string, i: number) => parseInt(h.slice(i, i + 2), 16)
  return '#' + [1, 3, 5].map((i) => Math.round(ch(a, i) * share + ch(b, i) * (1 - share)).toString(16).padStart(2, '0')).join('')
}

// [text, background, minimum ratio]: 4.5 for text, 3 for large text and marks
const PAIRS: [string, string, number][] = [
  ['ink', 'surface', 4.5], ['ink', 'bg', 4.5], ['ink', 'sunken', 4.5],
  ['ink-2', 'surface', 4.5], ['ink-2', 'bg', 4.5], ['ink-2', 'sunken', 4.5],
  ['ink-3', 'surface', 4.5], ['ink-3', 'sunken', 3],
  ['up', 'surface', 4.5], ['up', 'sunken', 4.5], ['down', 'surface', 4.5], ['down', 'sunken', 4.5],
  ['accent', 'surface', 4.5], ['accent', 'accent-soft', 4.5], ['accent', 'bg', 4.5],
  ['warn', 'warn-bg', 4.5], ['crit', 'crit-bg', 4.5], ['demo-ink', 'demo-bg', 4.5],
  ['bar', 'sunken', 3], ['surface', 'accent', 4.5],
  ['good', 'good-bg', 4.5], ['serious', 'serious-bg', 4.5], ['ink-2', 'accent-soft', 4.5], ['ink', 'neutral-bar', 4.5],
]

describe.each([['light', light], ['dark', dark]] as const)('%s theme', (_name, t) => {
  it.each(PAIRS)('%s on %s is at least %s:1', (fg, bg, min) => {
    expect(t[fg], `token --${fg}`).toBeDefined()
    expect(t[bg], `token --${bg}`).toBeDefined()
    expect(contrast(t[fg], t[bg])).toBeGreaterThanOrEqual(min)
  })

  it('heatmap cells keep readable text at the strongest tint (50 %)', () => {
    for (const pole of ['corr-pos', 'corr-neg']) expect(contrast(t.ink, mix(t[pole], t.surface, 0.5))).toBeGreaterThanOrEqual(4.5)
  })

  it('mix map tiles keep readable text at the strongest tint (40 %)', () => {
    for (const pole of ['risk-less', 'risk-more']) expect(contrast(t.ink, mix(t[pole], t['neutral-bar'], 0.4))).toBeGreaterThanOrEqual(4.5)
  })
})

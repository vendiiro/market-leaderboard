// Display formatting only. Every number shown comes from the engine's JSON.

const MINUS = '−'
const NBSP = ' '
export const DASH = '—'

/** 0.1234 -> "+12.3 %", -0.05 -> "−5.0 %", null -> "—". A value that rounds to zero has no sign. */
export function pct(x: number | null | undefined, digits = 1, sign = true): string {
  if (x == null || !Number.isFinite(x)) return DASH
  const body = Math.abs(x * 100).toFixed(digits)
  const zero = Number(body) === 0
  const lead = zero ? '' : x < 0 ? MINUS : sign ? '+' : ''
  return `${lead}${body}${NBSP}%`
}

/** Direction of a value for colour and arrows; zero and missing are 'flat'. */
export function direction(x: number | null | undefined): 'up' | 'down' | 'flat' {
  if (x == null || !Number.isFinite(x) || x === 0) return 'flat'
  return x > 0 ? 'up' : 'down'
}

/** Rank change: +2 -> "▲2", -1 -> "▼1", 0 -> "–", null -> "". */
export function rankChange(delta: number | null | undefined): string {
  if (delta == null) return ''
  if (delta === 0) return '–'
  return delta > 0 ? `▲${delta}` : `▼${-delta}`
}

/** Weekdays after `from` up to and including `to` (ISO dates); holidays are not modelled. */
export function weekdaysBetween(from: string, to: string): number {
  let n = 0
  const d = new Date(`${from}T00:00:00Z`)
  const end = new Date(`${to}T00:00:00Z`)
  while (d < end) {
    d.setUTCDate(d.getUTCDate() + 1)
    const day = d.getUTCDay()
    if (day !== 0 && day !== 6) n++
  }
  return n
}

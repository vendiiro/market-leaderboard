// Small shared pieces. Direction is always text (sign, arrow) as well as colour.
import { useId, useSyncExternalStore, type ReactNode } from 'react'
import type { Period } from '../data/load'
import { direction, pct, rankChange } from '../lib/format'

export const PERIODS: { key: Period; label: string; long: string }[] = [
  { key: '1d', label: '1d', long: '1 day' },
  { key: '1w', label: '1w', long: '1 week (5 sessions)' },
  { key: '1m', label: '1m', long: '1 month (21 sessions)' },
  { key: 'ytd', label: 'YTD', long: 'year to date' },
  { key: '1y', label: '1y', long: '1 year (252 sessions)' },
]
export const DEFAULT_PERIOD: Period = '1m'
export const asPeriod = (x: string | undefined): Period => PERIODS.find((p) => p.key === x)?.key ?? DEFAULT_PERIOD

export function Pct({ value, digits }: { value: number | null; digits?: number }) {
  return <span className={`num ${direction(value)}`}>{pct(value, digits)}</span>
}

export function RankChange({ delta }: { delta: number | null | undefined }) {
  if (delta == null) return null
  const text = delta === 0 ? 'no change in rank' : `${delta > 0 ? 'up' : 'down'} ${Math.abs(delta)} since the previous close`
  return (
    <span className={`num ${direction(delta)}`} title={text}>
      <span aria-hidden="true">{rankChange(delta)}</span>
      <span className="sr-only">{text}</span>
    </span>
  )
}

/** Last 60 closes rebased to 100, as an inline SVG path (no chart library per row). */
export function Sparkline({ values, width = 96, height = 28 }: { values: number[]; width?: number; height?: number }) {
  if (values.length < 2) return null
  const min = Math.min(...values)
  const span = Math.max(...values) - min || 1
  const step = (width - 2) / (values.length - 1)
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${(1 + i * step).toFixed(1)} ${(height - 2 - ((v - min) / span) * (height - 4)).toFixed(1)}`).join('')
  const change = values[values.length - 1] / values[0] - 1
  return (
    <svg className={`spark ${direction(change)}`} width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img"
      aria-label={`Price path over the last ${values.length} sessions: ${pct(change)}`}>
      <path d={d} />
    </svg>
  )
}

export function PeriodPicker({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  return (
    <div className="seg" role="group" aria-label="Return period">
      {PERIODS.map((p) => (
        <button key={p.key} type="button" aria-pressed={p.key === value} title={p.long} onClick={() => onChange(p.key)}>
          {p.label}
        </button>
      ))}
    </div>
  )
}

/** A term with its definition behind a small "?" button (native popover: keyboard and Esc work without script). */
export function InfoTip({ label, children }: { label: string; children: ReactNode }) {
  const id = useId()
  return (
    <>
      <button type="button" className="tipbtn" popoverTarget={id} aria-label={`What is ${label}?`}>?</button>
      <div id={id} popover="auto">{children}</div>
    </>
  )
}

export function Flag({ reasons }: { reasons: string[] }) {
  const id = useId()
  return (
    <>
      <button type="button" className="badge" popoverTarget={id}>Dip</button>
      <div id={id} popover="auto">
        <p>Flagged because:</p>
        <ul>{reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        <p className="muted">Untested screen rule: a description of the price move, not advice.</p>
      </div>
    </>
  )
}

export function State({ title, children, role }: { title: string; children?: ReactNode; role?: 'alert' | 'status' }) {
  return (
    <div className="state" role={role}>
      <h2>{title}</h2>
      {children}
    </div>
  )
}

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (cb) => {
      const m = window.matchMedia(query)
      m.addEventListener('change', cb)
      return () => m.removeEventListener('change', cb)
    },
    () => window.matchMedia(query).matches,
  )
}

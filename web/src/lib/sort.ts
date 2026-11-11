export type Dir = 'asc' | 'desc'

/** Stable sort by a number or string; rows without a value always go last, whatever the direction. */
export function sortBy<T>(rows: readonly T[], value: (row: T) => number | string | null | undefined, dir: Dir): T[] {
  const sign = dir === 'asc' ? 1 : -1
  return rows
    .map((row, i) => ({ row, i, v: value(row) }))
    .sort((a, b) => {
      if (a.v == null || b.v == null) return a.v == null ? (b.v == null ? a.i - b.i : 1) : -1
      const c = typeof a.v === 'string' || typeof b.v === 'string' ? String(a.v).localeCompare(String(b.v)) : a.v - b.v
      return c === 0 ? a.i - b.i : sign * c
    })
    .map((x) => x.row)
}

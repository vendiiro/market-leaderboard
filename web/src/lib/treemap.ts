// Layout only (no financial arithmetic): rectangles whose areas are proportional to the given values.
export interface Rect {
  key: string
  x: number
  y: number
  w: number
  h: number
}

/** Split the items into two groups of near-equal total, cut the rectangle along its longer side in that
 *  proportion, and repeat. Returns rectangles inside (x, y, w, h); items with a value of zero or less are left out. */
export function treemap(items: { key: string; value: number }[], x = 0, y = 0, w = 100, h = 100): Rect[] {
  const list = items.filter((i) => i.value > 0).sort((a, b) => b.value - a.value || a.key.localeCompare(b.key))
  if (list.length === 0) return []
  if (list.length === 1) return [{ key: list[0].key, x, y, w, h }]
  const total = list.reduce((s, i) => s + i.value, 0)
  let cut = 1
  let sum = list[0].value
  while (cut < list.length - 1 && Math.abs(sum + list[cut].value - total / 2) < Math.abs(sum - total / 2)) sum += list[cut++].value
  const share = sum / total
  const [a, b] = [list.slice(0, cut), list.slice(cut)]
  return w >= h
    ? [...treemap(a, x, y, w * share, h), ...treemap(b, x + w * share, y, w * (1 - share), h)]
    : [...treemap(a, x, y, w, h * share), ...treemap(b, x, y + h * share, w, h * (1 - share))]
}

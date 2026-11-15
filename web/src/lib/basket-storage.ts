// The research basket lives in the browser only (localStorage). It is separate from the saved test mixes of the Mix view.
import type { BasketItem } from './basket'

const KEY = 'market-leaderboard.basket.v1'
const MAX_ITEMS = 200

/** A valid basket, or null. Stored text is untrusted: every field is checked. */
export function asBasket(x: unknown): BasketItem[] | null {
  if (!Array.isArray(x) || x.length > MAX_ITEMS) return null
  const out: BasketItem[] = []
  for (const it of x) {
    const { ticker, amountEur } = (it ?? {}) as { ticker?: unknown; amountEur?: unknown }
    if (typeof ticker !== 'string' || !ticker || ticker.length > 20) return null
    if (typeof amountEur !== 'number' || !Number.isFinite(amountEur) || amountEur < 0) return null
    out.push({ ticker, amountEur })
  }
  return out
}

export function loadBasket(storage: Pick<Storage, 'getItem'> | undefined = globalThis.localStorage): BasketItem[] {
  try {
    return asBasket(JSON.parse(storage?.getItem(KEY) ?? 'null')) ?? []
  } catch {
    return [] // corrupt or blocked storage: start empty rather than fail
  }
}

export function saveBasket(items: BasketItem[], storage: Pick<Storage, 'setItem'> | undefined = globalThis.localStorage): void {
  try {
    storage?.setItem(KEY, JSON.stringify(items))
  } catch {
    // storage full or blocked: the basket still works for this visit
  }
}

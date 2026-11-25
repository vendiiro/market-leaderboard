// Hash routes, so the static build needs no server rewrites:  #/ (candidates)  #/screener  #/list  #/list/:id  #/mix  #/movers  #/data
// ?c=TICKER on any route opens that company's research panel, so a company can be bookmarked.
// View state that should survive a reload or a bookmark (period, sort) lives in the query part.
import { useSyncExternalStore } from 'react'

export type View = 'candidates' | 'screener' | 'list' | 'mix' | 'movers' | 'data' | 'notfound'
export interface Route {
  view: View
  id?: string
  params: Record<string, string>
}

export function parseHash(hash: string): Route {
  const [path, query = ''] = hash.replace(/^#/, '').split('?')
  const params = Object.fromEntries(new URLSearchParams(query))
  const parts = path.split('/').filter(Boolean).map(decodeURIComponent)
  if (parts.length === 0) return { view: 'candidates', params }
  if (parts[0] === 'list' && parts.length <= 2) return { view: 'list', id: parts[1], params }
  const simple = ['screener', 'mix', 'movers', 'data'] as const
  const view = simple.find((v) => v === parts[0])
  if (view && parts.length === 1) return { view, params }
  return { view: 'notfound', params }
}

export function formatHash(route: Pick<Route, 'view' | 'id'> & { params?: Record<string, string | undefined> }): string {
  const path = route.view === 'candidates' ? '' : route.view === 'list' && route.id ? `list/${encodeURIComponent(route.id)}` : route.view
  const entries = Object.entries(route.params ?? {}).filter((e): e is [string, string] => !!e[1])
  const query = entries.map(([k, v]) => `${k}=${encodeURIComponent(v).replace(/%3A/g, ':')}`).join('&')
  return `#/${path}${query ? `?${query}` : ''}`
}

const subscribe = (cb: () => void) => {
  window.addEventListener('hashchange', cb)
  return () => window.removeEventListener('hashchange', cb)
}

export function useRoute(): Route {
  return parseHash(useSyncExternalStore(subscribe, () => window.location.hash))
}

/** Change view state without adding a history entry (period and sort changes should not fill the back button). */
export function replaceRoute(route: Parameters<typeof formatHash>[0]): void {
  window.history.replaceState(null, '', formatHash(route))
  window.dispatchEvent(new HashChangeEvent('hashchange'))
}

/** Address of the same view with a company's research panel open (or closed when ticker is undefined). */
export function withCompany(route: Route, ticker: string | undefined): string {
  return formatHash({ view: route.view, id: route.id, params: { ...route.params, c: ticker } })
}

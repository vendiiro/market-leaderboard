/* Generated from schemas/ by npm run gen:types. Do not edit. */

export type Day = string;

/**
 * Largest 1-day moves across all watchlists (each ticker once, stale rows never listed) and the rows the dip rule flags. The dip rule is an untested screen rule.
 */
export interface Movers {
  schema_version: 2;
  asof: Day;
  gainers: Mover[];
  losers: Mover[];
  alerts: Alert[];
}
export interface Mover {
  ticker: string;
  name: string;
  lists: string[];
  currency: string | null;
  last_bar: Day;
  ret_1d: number | null;
}
export interface Alert {
  ticker: string;
  name: string;
  lists: string[];
  currency: string | null;
  last_bar: Day;
  ret_1d: number | null;
  reasons: string[];
  label: string;
  q_passed: number;
  q_scored: number;
}

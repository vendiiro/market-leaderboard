/* Generated from schemas/ by npm run gen:types. Do not edit. */

export type Day = string;
export type Period = "1d" | "1w" | "1m" | "ytd" | "1y";
export type Num = number | null;
export type Text = string | null;

/**
 * One table per watchlist. Returns and vol_1y are in each stock's own currency. The dip flag and quality score are untested screen rules.
 */
export interface Leaderboard {
  schema_version: 2;
  asof: Day;
  periods: Period[];
  lists: Watchlist[];
}
export interface Watchlist {
  key: string;
  name: string;
  summary: Summary;
  rows: Row[];
}
export interface Summary {
  periods: {
    "1d": PeriodSummary;
    "1w": PeriodSummary;
    "1m": PeriodSummary;
    ytd: PeriodSummary;
    "1y": PeriodSummary;
  };
  count: number;
  stale: number;
  flags: number;
}
/**
 * Equal-weight mean return of the list's fresh rows, each in its own currency.
 */
export interface PeriodSummary {
  mean: Num;
  n: number;
  top: Text;
  bottom: Text;
}
export interface Row {
  ticker: string;
  name: string;
  lists: string[];
  currency: Text;
  sector: Text;
  country: Text;
  last_bar: Day;
  stale: boolean;
  stale_reason: Text;
  price: Num;
  ret_1d: Num;
  ret_1w: Num;
  ret_1m: Num;
  ret_ytd: Num;
  ret_1y: Num;
  vol_1y: Num;
  dd52: Num;
  q_score: number | null;
  q_passed: number;
  q_scored: number;
  pe: Num;
  fwd_pe: Num;
  dip: boolean;
  dip_reasons: string[];
  spark: number[];
  /**
   * null for a stale row.
   */
  rank: null | {
    "1d": Rank;
    "1w": Rank;
    "1m": Rank;
    ytd: Rank;
    "1y": Rank;
  };
}
/**
 * rank 1 = highest return in the list for the period; rank_delta = rank_prev - rank (positive = moved up).
 */
export interface Rank {
  rank: number | null;
  rank_prev: number | null;
  rank_delta: number | null;
}

/* Generated from schemas/ by npm run gen:types. Do not edit. */

export type Texts = string[];
export type Text = string | null;
export type Num = number | null;
/**
 * Figures that failed a consistency check and are left out of the measures.
 */
export type Texts1 = string[];
export type Rank = number | null;

/**
 * Valuation facts, four measures and the candidate shortlist. Measures are ranks 0-100 within the universe (100 = best). The measures are not shown to work on these companies: see evidence. Sentences are fixed templates filled with facts; headlines are third-party text.
 */
export interface Research {
  schema_version: 2;
  asof: string;
  /**
   * Tickers of tonight's candidates, best average rank first.
   */
  shortlist: string[];
  gate_passed: number;
  labels: ByMeasureText;
  /**
   * Per measure: what a pre-registered test on this universe found, or absent when untested.
   */
  evidence: {
    [k: string]: {
      status: "supported" | "not supported" | "untested";
      text: string;
    };
  };
  companies: Company[];
}
export interface ByMeasureText {
  value: string;
  quality: string;
  trend: string;
  steady: string;
}
export interface Company {
  ticker: string;
  name: string;
  lists: Texts;
  sector: Text;
  country: Text;
  currency: Text;
  last_bar: string;
  stale: boolean;
  price: Num;
  ret_1d: Num;
  ret_1y: Num;
  dd52: Num;
  vol_1y: Num;
  spark: number[];
  pe: Num;
  fwd_pe: Num;
  ev_ebitda: Num;
  pb: Num;
  margin: Num;
  op_margin: Num;
  roe: Num;
  debt_equity: Num;
  revenue_growth: Num;
  earnings_growth: Num;
  /**
   * P/E at each past fiscal year-end, newest first, in the trading currency.
   */
  own_pes: {
    year: number;
    pe: number;
  }[];
  own_mid: Num;
  /**
   * P/E now divided by the middle of own_pes, minus 1.
   */
  vs_own: number | null;
  inconsistent: Texts1;
  momentum: Num;
  big_days: number | null;
  report_currency: Text;
  vs_sector: Num;
  sector_mid: Num;
  /**
   * Forward P/E of the comparable companies, ascending.
   */
  sector_marks: number[];
  gate: {
    status: "pass" | "fail" | "short";
    profit_years: number;
    years: number;
  };
  measures: {
    value: Rank;
    quality: Rank;
    trend: Rank;
    steady: Rank;
  };
  /**
   * Position on tonight's shortlist, or null.
   */
  place: number | null;
  valuation: "low for it" | "typical" | "high for it" | "no data";
  why: Texts;
  against: Texts;
  caveats: Texts;
  events: Texts;
  headlines: Headline[];
}
export interface Headline {
  title: string;
  source: string;
  url: Text;
  date: string;
  days_old: number | null;
}

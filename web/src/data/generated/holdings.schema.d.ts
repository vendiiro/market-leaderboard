/* Generated from schemas/ by npm run gen:types. Do not edit. */

/**
 * The owner's own holdings (private; the file is generated into a gitignored folder), the ETF candidates and the broker's weekly history. Value and result are in EUR from Yahoo closes and may differ slightly from the broker's report. Estimates, not advice.
 */
export interface Holdings {
  schema_version: 3;
  asof: string;
  label: string;
  positions: Position[];
  totals: Totals;
  /**
   * Weekly points from the broker's export, or null when there is no history file or it could not be read (see history_note).
   */
  history: null | History;
  history_note: string | null;
  etfs: EtfRow[];
}
/**
 * One holding. value_eur is null for a holding without a price tonight (note says why); it is then left out of weights and totals. A fund without a Yahoo ticker has a hand-typed value and no cost, result, return or risk data.
 */
export interface Position {
  key: string;
  ticker: string | null;
  name: string;
  kind: "stock" | "etf" | "etn" | "fund";
  group: string | null;
  currency: string | null;
  sector: string | null;
  quantity: number | null;
  price: number | null;
  value_eur: number | null;
  cost_eur: number | null;
  cost_approx: boolean;
  result_eur: number | null;
  return_local: number | null;
  weight: number | null;
  has_risk: boolean;
  note: string | null;
}
export interface Totals {
  value_eur: number;
  result_eur: number | null;
  result_complete: boolean;
  top3_share: number;
  tech_share: number;
  risk_covered: number;
  unpriced: number;
}
export interface History {
  points: {
    date: string;
    value: number;
    /**
     * Accumulated time-weighted return as a fraction.
     */
    cum: number;
    net_deposits: number;
  }[];
  summary: {
    since_start: number;
    month: number | null;
    ytd: number | null;
    max_drawdown: number;
    drawdown_from: string;
    drawdown_to: string;
    lowest: Extreme;
    highest: Extreme;
  };
}
export interface Extreme {
  date: string;
  cum: number;
}
export interface EtfRow {
  ticker: string;
  name: string;
  list: string;
  group: string | null;
  currency: string | null;
  price: number | null;
  ret_1y: number | null;
  dd52: number | null;
  vol_1y: number | null;
}

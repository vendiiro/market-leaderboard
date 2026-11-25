/* Generated from schemas/ by npm run gen:types. Do not edit. */

export type Matrix = number[][];

/**
 * Inputs for the mix view. cov and corr are square matrices in the order of risk_tickers: annualised covariance and correlation of weekly EUR returns over one shared window. Estimates, not forecasts.
 */
export interface Portfolio {
  schema_version: 2;
  asof: string;
  window: {
    start: string | null;
    end: string | null;
    weeks: number;
  };
  /**
   * Every ticker with data tonight, once. vol_eur is null for a ticker without risk data.
   */
  tickers: {
    ticker: string;
    name: string;
    lists: string[];
    sector: string | null;
    country: string | null;
    currency: string | null;
    vol_eur: number | null;
  }[];
  risk_tickers: string[];
  cov: Matrix;
  corr: Matrix;
  no_risk_data: {
    ticker: string;
    reason: string;
  }[];
}

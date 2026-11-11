/* Generated from schemas/ by npm run gen:types. Do not edit. */

/**
 * State of the build: data date, counts, tickers without data and the data limits shown on the page.
 */
export interface Meta {
  schema_version: 1;
  asof: string;
  built_at: string;
  demo: boolean;
  tickers: number;
  usable: number;
  lists: {
    key: string;
    name: string;
    count: number;
    usable: number;
  }[];
  failures: {
    ticker: string;
    name: string;
    lists: string[];
    reason: string;
  }[];
  notes: string[];
}

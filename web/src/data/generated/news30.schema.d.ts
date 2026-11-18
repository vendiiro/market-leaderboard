/* Generated from schemas/ by npm run gen:types. Do not edit. */

/**
 * Headlines from the last 30 days for the shares the owner holds, and tonight's research candidates, from Google News RSS and Hacker News (scripts/news30.py). Private (names the holdings) and git-ignored. News flow, not sentiment; headlines are third-party text.
 */
export interface News30 {
  schema_version: 2;
  asof: string;
  source: string;
  companies: Company[];
  failed: {
    ticker: string;
    reason: string;
  }[];
}
export interface Company {
  /**
   * A share the owner holds, or one of tonight's research candidates.
   */
  group: "holding" | "candidate";
  ticker: string;
  name: string;
  asof: string;
  count: number;
  /**
   * The feed was full (100 items): counts and the weekly split lean to recent days.
   */
  capped: boolean;
  /**
   * Headlines per week, oldest week first; the last entry is the most recent 7 days.
   *
   * @minItems 4
   * @maxItems 4
   */
  per_week: [number, number, number, number];
  items: Item[];
}
export interface Item {
  title: string;
  source: string;
  url: string | null;
  date: string;
}

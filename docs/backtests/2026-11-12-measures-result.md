# Test of the trend and steadiness measures: result

Run on 2026-11-12 with 58 tickers. Spec: `2026-11-12-measures-spec.json` (written before the run).

| Measure | Month-ends | Period | Top third minus bottom third, next 12 months | 90% interval | Verdict |
|---|---|---|---|---|---|
| long-term trend | 279 | 2002-09 to 2025-11 | +4.4% | −2.6% to +11.6% | not supported |
| steadiness | 279 | 2002-09 to 2025-11 | −18.8% | −27.6% to −11.1% | not supported |

Read with the limits in the spec: today's survivors only, few independent observations, hand-picked companies.
The page shows the sentences in `config/measure_evidence.json`.

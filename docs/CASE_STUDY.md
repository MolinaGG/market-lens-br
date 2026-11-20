# Case study: comparable return definitions

[Português](CASE_STUDY.pt-BR.md) · [Demo](https://market-lens-br-web.onrender.com/) · [Project](../README.md)

## Problem

Price changes alone omit coupon payments received by a bondholder. Comparing two analyses with different dates or factors would confound the effect of changing the return definition with changes in the sample.

## Method

Market Lens builds price-only and coupon-adjusted returns from the same observations. Coupons are allocated to the interval between consecutive quotes. Missing factor observations remove the interval from both models. OLS models use identical factor matrices and chronological training/holdout periods.

For consecutive prices P0 and P1 and coupons C in the interval:

```text
price_return = P1 / P0 - 1
coupon_adjusted_return = (P1 + C) / P0 - 1
```

This is gross one-period return, not a net reinvested investor return. The interface shows coefficients, 95% confidence intervals, R² and error, helping the reader inspect the effect of changing the definition.

## Observable output

The deliverable is a comparison that a reviewer can reproduce and inspect. The portfolio does not assert a fixed investment performance result: coefficients and errors depend on the selected instrument, factors and period. The methodological result is comparability under a common sample, not proof of forecasting skill.

## Evidence

- [Return implementation](../backend/app/analysis/returns.py).
- [Regression and chronological holdout](../backend/app/analysis/regression.py).
- [Tests covering coupon allocation and identical samples](../backend/tests/test_returns_regression.py).
- [Full methodology](METODOLOGIA.md) and [source provenance](FONTES.md), in Portuguese.

## Boundaries and contribution discussion

No coupon reinvestment, taxes, custody, spread, liquidity or inflation adjustment is included. Daily factor observations are not a guarantee of contemporaneous publication; holdout results are not an operational trading backtest. Event-window differences are descriptive associations, not causal effects. Equity prices remain in local imports rather than the public demo.

For an interview, walk through source selection, interval alignment, missing observations, holdout construction and uncertainty. Use repository history to discuss implementation contribution and AI assistance accurately; the existence of a demo is not evidence of independent authorship of every component.

# Deriv trend basket — backtest

Markets (17): gold, silver, oil, brent, spx, nasdaq, dow, dax, ftse, nikkei, eurusd, gbpusd, audusd, usdchf, usdcad, usdjpy, bitcoin. Daily closes, 2001-10-01 → 2026-10-23.
Weekly rebalance, equal risk per market, portfolio scaled to 10% yearly volatility, Deriv-like spread + swap charged.

## Design years 2003–2017 (rules chosen here)
| label                        |   CAGR % |   vol % |   Sharpe |   max DD % |   worst year % | years up   |     t |   $10k → |
|:-----------------------------|---------:|--------:|---------:|-----------:|---------------:|:-----------|------:|---------:|
| 12-month trend               |      1.5 |    10.3 |     0.2  |      -31   |          -13.6 | 10/15      |  0.75 |    12584 |
| Blend 1/3/6/12-month trend   |      1.5 |    10.6 |     0.19 |      -24.4 |           -9.5 | 8/15       |  0.74 |    12555 |
| EMA 20/100 cross (daily)     |     -1.7 |    10.3 |    -0.12 |      -37.2 |          -15.2 | 5/15       | -0.44 |     7622 |
| EMA 50/200 cross (daily)     |      1   |    10.3 |     0.15 |      -39   |          -25.2 | 9/15       |  0.57 |    11676 |
| 100-day breakout             |      0   |    10.3 |     0.05 |      -36.9 |          -24.1 | 6/15       |  0.22 |    10051 |
| Buy & hold, same risk sizing |      2.4 |    10.3 |     0.28 |      -38.6 |          -24.5 | 10/15      |  1.11 |    14416 |

**Chosen on design years: 12-month trend**

## Hold-out years 2018–2026 (never used for choosing)
| label                        |   CAGR % |   vol % |   Sharpe |   max DD % |   worst year % | years up   |     t |   $10k → |
|:-----------------------------|---------:|--------:|---------:|-----------:|---------------:|:-----------|------:|---------:|
| 12-month trend               |     -4   |    10.5 |    -0.33 |      -50.2 |          -17.1 | 4/9        | -0.78 |     6906 |
| Blend 1/3/6/12-month trend   |     -5.4 |    10.8 |    -0.46 |      -48   |          -13.1 | 2/9        | -1.26 |     6013 |
| EMA 20/100 cross (daily)     |     -5.9 |    10.5 |    -0.53 |      -49.2 |          -17.5 | 1/9        | -1.36 |     5743 |
| EMA 50/200 cross (daily)     |     -7.1 |    10.5 |    -0.65 |      -56.1 |          -18.1 | 2/9        | -1.92 |     5091 |
| 100-day breakout             |     -7.5 |    10.4 |    -0.7  |      -54.6 |          -24.1 | 2/9        | -1.97 |     4900 |
| Buy & hold, same risk sizing |     -0   |    10.9 |     0.05 |      -38.9 |          -20   | 6/9        |  0.18 |     9976 |

## Luck check (hold-out)
200 runs with random long/short signals that switch as often as the chosen rule, same sizing and costs.
Random Sharpe: median -1.06, 95th percentile -0.49.
**Chosen rule's hold-out Sharpe -0.33 beats 98% of random runs.**

## 12-month trend: every year
| Year | Return |
|---|---|
| 2003 | +3.5% |
| 2004 | +4.5% |
| 2005 | +0.1% |
| 2006 | +4.5% |
| 2007 | +1.4% |
| 2008 | +4.3% |
| 2009 | -11.0% |
| 2010 | +5.0% |
| 2011 | -10.1% |
| 2012 | -9.3% |
| 2013 | +21.0% |
| 2014 | +7.6% |
| 2015 | -0.0% |
| 2016 | -13.6% |
| 2017 | +22.5% |
| 2018 | -17.1% |
| 2019 | -12.5% |
| 2020 | +1.3% |
| 2021 | -1.9% |
| 2022 | +0.2% |
| 2023 | -13.2% |
| 2024 | +4.8% |
| 2025 | +11.8% |
| 2026 | -5.8% |

## Hold-out contribution by market (% of account, summed)
| Market | % |
|---|---|
| nikkei | +4.5 |
| nasdaq | +4.2 |
| bitcoin | +3.3 |
| gold | +2.7 |
| spx | +2.4 |
| brent | +0.7 |
| eurusd | -0.1 |
| silver | -1.1 |
| audusd | -1.4 |
| oil | -3.4 |
| gbpusd | -3.9 |
| dax | -4.5 |
| dow | -4.6 |
| usdchf | -5.4 |
| ftse | -7.4 |
| usdcad | -8.8 |
| usdjpy | -9.1 |

## Re-run 2026-10-23 evening (fresh Yahoo prices, ^NDX for Nasdaq, rebalance anchored to the latest close)
No-FX Blend: design Sharpe 0.21, hold-out **−1.3%/yr** (Sharpe −0.07, max DD −41%); 12-month: hold-out −1.5%/yr;
buy & hold +2.9%/yr. Small data/timing changes move the result by ~2%/yr: the edge after costs is not robust.
`weekly_signals.py` prints the weekly buy/sell/close list (output/signals/).

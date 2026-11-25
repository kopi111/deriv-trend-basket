"""Runs every trend variant on the design years, picks one there, then reports it on the hold-out years.

Run: python3 run_basket.py  →  prints tables and writes output/REPORT.md
"""
import numpy as np
import pandas as pd

from basket import (DESIGN, HERE, HOLD_OUT, VARIANTS, daily_returns, load_prices, period,
                    signal_buy_and_hold, summary, target_weights)

LUCK_RUNS = 200


def table(rows):
    frame = pd.DataFrame(rows).set_index("label")
    return frame.to_markdown()


def flip_rate(signal):
    weekly_signal = np.sign(signal.iloc[::5])
    flips = (weekly_signal.diff().abs() > 0).sum().sum()
    return flips / weekly_signal.notna().sum().sum()


def random_signal(prices, rate, generator):
    weeks = prices.iloc[::5]
    flips = generator.random(weeks.shape) < rate
    start = generator.choice([-1.0, 1.0], size=(1, weeks.shape[1]))
    signs = start * np.where(np.cumsum(flips, axis=0) % 2 == 0, 1.0, -1.0)
    frame = pd.DataFrame(signs, index=weeks.index, columns=prices.columns)
    return frame.reindex(prices.index).ffill().where(prices.notna())


def luck_check(prices, signal, generator):
    rate = flip_rate(signal)
    sharpes = []
    for _ in range(LUCK_RUNS):
        daily, _ = daily_returns(prices, target_weights(prices, random_signal(prices, rate, generator)))
        sharpes.append(summary(period(daily, HOLD_OUT), "random")["Sharpe"])
    return np.array(sharpes)


def main():
    prices = load_prices()
    results = {}
    for name, make_signal in {**VARIANTS, "Buy & hold, same risk sizing": signal_buy_and_hold}.items():
        signal = make_signal(prices)
        daily, contributions = daily_returns(prices, target_weights(prices, signal))
        results[name] = (signal, daily, contributions)

    design_rows = [summary(period(daily, DESIGN), name) for name, (_, daily, _) in results.items()]
    chosen = max((row for row in design_rows if row["label"] in VARIANTS), key=lambda row: row["Sharpe"])["label"]
    hold_rows = [summary(period(daily, HOLD_OUT), name) for name, (_, daily, _) in results.items()]

    signal, daily, contributions = results[chosen]
    sharpes = luck_check(prices, signal, np.random.default_rng(11))
    chosen_hold = summary(period(daily, HOLD_OUT), chosen)
    beaten = (sharpes < chosen_hold["Sharpe"]).mean()

    yearly = ((1 + daily).resample("YE").prod() - 1).loc["2003":]
    yearly_rows = "\n".join(f"| {when.year} | {100 * value:+.1f}% |" for when, value in yearly.items())
    per_asset = (period(contributions, HOLD_OUT).sum() * 100).sort_values(ascending=False).round(1)
    asset_rows = "\n".join(f"| {name} | {value:+.1f} |" for name, value in per_asset.items())

    report = f"""# Deriv trend basket — backtest

Markets ({len(prices.columns)}): {", ".join(prices.columns)}. Daily closes, {prices.index[0].date()} → {prices.index[-1].date()}.
Weekly rebalance, equal risk per market, portfolio scaled to 10% yearly volatility, Deriv-like spread + swap charged.

## Design years {DESIGN[0][:4]}–{DESIGN[1][:4]} (rules chosen here)
{table(design_rows)}

**Chosen on design years: {chosen}**

## Hold-out years {HOLD_OUT[0][:4]}–2026 (never used for choosing)
{table(hold_rows)}

## Luck check (hold-out)
{LUCK_RUNS} runs with random long/short signals that switch as often as the chosen rule, same sizing and costs.
Random Sharpe: median {np.median(sharpes):.2f}, 95th percentile {np.percentile(sharpes, 95):.2f}.
**Chosen rule's hold-out Sharpe {chosen_hold['Sharpe']} beats {beaten:.0%} of random runs.**

## {chosen}: every year
| Year | Return |
|---|---|
{yearly_rows}

## Hold-out contribution by market (% of account, summed)
| Market | % |
|---|---|
{asset_rows}
"""
    (HERE / "output").mkdir(exist_ok=True)
    (HERE / "output" / "REPORT.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()

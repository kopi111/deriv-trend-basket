"""Weekly buy/sell/close list for the trend basket (Blend 1/3/6/12-month rule, no FX).

Run after Friday's close. Downloads fresh daily prices, scores every market, compares with last week's
saved positions and writes the message to output/signals/<date>.md (plus history.csv).
Prints the message so a notifier can send it.

    python3 weekly_signals.py            # account size from config.json (default $10,000)
"""
import json
from datetime import date

import numpy as np
import pandas as pd
import yfinance as yf

from basket import ASSET_CLASS, HERE, load_prices, signal_tsm_blend, target_weights

TICKERS = {
    "gold": "GC=F", "silver": "SI=F", "oil": "CL=F", "brent": "BZ=F",
    "spx": "^GSPC", "nasdaq": "^NDX", "dow": "^DJI", "dax": "^GDAXI", "ftse": "^FTSE", "nikkei": "^N225",
    "bitcoin": "BTC-USD",
}
DERIV_NAME = {
    "gold": "Gold (XAUUSD)", "silver": "Silver (XAGUSD)", "oil": "US Oil (WTI)", "brent": "UK Brent Oil",
    "spx": "US 500", "nasdaq": "US Tech 100", "dow": "Wall Street 30", "dax": "Germany 40",
    "ftse": "UK 100", "nikkei": "Japan 225", "bitcoin": "BTCUSD",
}
LOOKBACKS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}
SIGNALS = HERE / "output" / "signals"
STATE = SIGNALS / "last_week.json"
HISTORY = SIGNALS / "history.csv"


def refresh_prices():
    for name, ticker in TICKERS.items():
        frame = yf.Ticker(ticker).history(start="2001-10-01", interval="1d").dropna()
        if frame.empty:
            raise RuntimeError(f"Yahoo returned no prices for {name} ({ticker})")
        closes = frame[["Close"]].rename(columns={"Close": "close"})
        closes.index = closes.index.tz_localize(None).date
        closes.index.name = "date"
        closes.to_csv(HERE / "data" / f"{name}.csv")


def account_size():
    config = HERE / "config.json"
    return json.loads(config.read_text())["account_usd"] if config.exists() else 10_000


def direction(weight):
    if weight > 0:
        return "BUY"
    if weight < 0:
        return "SELL"
    return "NONE"


def action(previous, current):
    if direction(previous) == direction(current):
        changed = abs(current - previous) > 0.25 * max(abs(previous), 1e-9)
        return "RESIZE" if direction(current) != "NONE" and changed else "HOLD"
    if direction(current) == "NONE":
        return "CLOSE"
    return f"{'FLIP TO ' if direction(previous) != 'NONE' else ''}{direction(current)}"


def this_week():
    prices = load_prices()
    prices = prices[[name for name in TICKERS if name in prices.columns]]
    signal = signal_tsm_blend(prices)
    weights = target_weights(prices, signal).iloc[-1]
    rows = []
    for name in prices.columns:
        closes = prices[name].dropna()
        moves = {label: closes.iloc[-1] / closes.iloc[-1 - days] - 1 for label, days in LOOKBACKS.items()}
        rows.append({"market": name, "price": closes.iloc[-1], "score": signal[name].iloc[-1],
                     "weight": float(weights[name]), **moves})
    return prices.index[-1].date(), pd.DataFrame(rows).set_index("market")


def message(as_of, table, previous, account):
    lines = [f"Trend basket — week after {as_of} close", ""]
    changes = []
    for name, row in table.iterrows():
        step = action(previous.get(name, 0.0), row.weight)
        if step != "HOLD":
            size = abs(row.weight) * account
            detail = f"position about ${size:,.0f}" if direction(row.weight) != "NONE" else "close it"
            changes.append(f"• {step} {DERIV_NAME[name]} — {detail} (score {row.score:+.2f})")
    lines += ["CHANGES THIS WEEK:"] + (changes or ["• none — keep what you hold"]) + ["", "ALL MARKETS:"]
    for name, row in table.iterrows():
        moves = " ".join(f"{label} {row[label] * 100:+.0f}%" for label in LOOKBACKS)
        held = f"{direction(row.weight)} ${abs(row.weight) * account:,.0f}" if row.weight else "none"
        lines.append(f"• {DERIV_NAME[name]}: {held} | score {row.score:+.2f} | {moves}")
    lines += ["", f"Sizes are position value for a ${account:,.0f} account (not risk). Paper-trade first."]
    return "\n".join(lines)


def save(as_of, table, text):
    SIGNALS.mkdir(parents=True, exist_ok=True)
    (SIGNALS / f"{as_of}.md").write_text(text + "\n")
    STATE.write_text(json.dumps({"as_of": str(as_of), "weights": table.weight.to_dict()}, indent=2))
    record = table[["price", "score", "weight"]].assign(as_of=str(as_of))
    record.to_csv(HISTORY, mode="a", header=not HISTORY.exists())


def main():
    refresh_prices()
    as_of, table = this_week()
    previous = json.loads(STATE.read_text())["weights"] if STATE.exists() else {}
    text = message(as_of, table, previous, account_size())
    save(as_of, table, text)
    print(text)


if __name__ == "__main__":
    main()

"""Slow trend-following on a basket of real markets that Deriv offers on MT5.

Rules are chosen on DESIGN years only, then judged on HOLD-OUT years they never saw.

Each week (Friday close) every market gets a trend signal; the position is sized so each market carries
the same risk (inverse of its recent volatility), and the whole portfolio is scaled to a 10% yearly
volatility target. The next week's returns are earned on those positions.

Costs charged (Deriv-like, conservative assumptions, not Deriv's published numbers):
  spread   per unit of position changed, by asset class (see SPREAD);
  swap     overnight financing on every open position, long or short (see SWAP_PER_YEAR).
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DESIGN = ("2003-01-01", "2017-12-31")
HOLD_OUT = ("2018-01-01", "2026-12-31")
TRADING_DAYS = 252
TARGET_VOL = 0.10
MAX_GROSS_LEVERAGE = 4.0
ASSET_VOL_DAYS = 60
PORTFOLIO_VOL_DAYS = 126
REBALANCE_EVERY = 5

ASSET_CLASS = {
    "gold": "metal", "silver": "metal", "oil": "energy", "brent": "energy",
    "spx": "index", "nasdaq": "index", "dow": "index", "dax": "index", "ftse": "index", "nikkei": "index",
    "eurusd": "fx", "gbpusd": "fx", "audusd": "fx", "usdchf": "fx", "usdcad": "fx", "usdjpy": "fx",
    "bitcoin": "crypto",
}
SPREAD = {"metal": 0.0004, "energy": 0.0006, "index": 0.0003, "fx": 0.00015, "crypto": 0.0020}
SWAP_PER_YEAR = {"metal": 0.04, "energy": 0.04, "index": 0.04, "fx": 0.02, "crypto": 0.15}


def load_prices():
    columns = {}
    for name in ASSET_CLASS:
        frame = pd.read_csv(HERE / "data" / f"{name}.csv", parse_dates=["date"]).set_index("date")
        columns[name] = frame["close"].groupby(level=0).last()
    prices = pd.DataFrame(columns).sort_index()
    prices = prices.where(prices > 0)  # WTI futures settled below zero in April 2020; CFDs never did
    weekdays = prices.index.dayofweek < 5
    return prices[weekdays].ffill(limit=5)


def sign_of_return(prices, days):
    return np.sign(prices / prices.shift(days) - 1.0)


def signal_tsm_12m(prices):
    return sign_of_return(prices, 252)


def signal_tsm_blend(prices):
    return sum(sign_of_return(prices, days) for days in (21, 63, 126, 252)) / 4


def signal_ema(prices, fast, slow):
    return np.sign(prices.ewm(span=fast).mean() - prices.ewm(span=slow).mean())


def signal_donchian(prices, days=100):
    high, low = prices.rolling(days).max(), prices.rolling(days).min()
    state = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    state[prices >= high] = 1.0
    state[prices <= low] = -1.0
    return state.ffill()


def signal_buy_and_hold(prices):
    return prices.notna().astype(float)


VARIANTS = {
    "12-month trend": signal_tsm_12m,
    "Blend 1/3/6/12-month trend": signal_tsm_blend,
    "EMA 20/100 cross (daily)": lambda prices: signal_ema(prices, 20, 100),
    "EMA 50/200 cross (daily)": lambda prices: signal_ema(prices, 50, 200),
    "100-day breakout": signal_donchian,
}


def weekly(frame):
    """Holds each rebalance day's values for the week; rebalance days are counted back from the latest row."""
    rebalance_days = frame.index[::-1][::REBALANCE_EVERY][::-1]
    return frame.loc[rebalance_days].reindex(frame.index).ffill()


def target_weights(prices, signal):
    returns = prices.pct_change(fill_method=None)
    asset_vol = returns.rolling(ASSET_VOL_DAYS).std() * np.sqrt(TRADING_DAYS)
    active = signal.notna() & asset_vol.notna()
    raw = (signal / asset_vol).where(active)
    raw = raw.div(active.sum(axis=1).replace(0, np.nan), axis=0)
    raw_portfolio = (weekly(raw).shift(1) * returns).sum(axis=1)
    portfolio_vol = raw_portfolio.rolling(PORTFOLIO_VOL_DAYS).std() * np.sqrt(TRADING_DAYS)
    scale = (TARGET_VOL / portfolio_vol).replace(np.inf, np.nan)
    weights = raw.mul(scale, axis=0)
    gross = weights.abs().sum(axis=1)
    weights = weights.mul((MAX_GROSS_LEVERAGE / gross).clip(upper=1.0), axis=0)
    return weekly(weights.fillna(0.0))


def cost_rates():
    spread = pd.Series({name: SPREAD[kind] for name, kind in ASSET_CLASS.items()})
    swap = pd.Series({name: SWAP_PER_YEAR[kind] / TRADING_DAYS for name, kind in ASSET_CLASS.items()})
    return spread, swap


def daily_returns(prices, weights):
    """Net daily portfolio return and per-asset net contributions."""
    returns = prices.pct_change(fill_method=None).fillna(0.0)
    held = weights.shift(1).fillna(0.0)
    spread, swap = cost_rates()
    trading = held.diff().abs().fillna(0.0) * spread
    financing = held.abs() * swap
    contributions = held * returns - trading - financing
    return contributions.sum(axis=1), contributions


def summary(daily, label):
    daily = daily[daily.index >= daily.ne(0).idxmax()]
    curve = (1 + daily).cumprod()
    years = len(daily) / TRADING_DAYS
    cagr = curve.iloc[-1] ** (1 / years) - 1
    vol = daily.std() * np.sqrt(TRADING_DAYS)
    monthly = (1 + daily).resample("ME").prod() - 1
    yearly = (1 + daily).resample("YE").prod() - 1
    return {
        "label": label,
        "CAGR %": round(100 * cagr, 1),
        "vol %": round(100 * vol, 1),
        "Sharpe": round(daily.mean() / daily.std() * np.sqrt(TRADING_DAYS), 2),
        "max DD %": round(100 * (curve / curve.cummax() - 1).min(), 1),
        "worst year %": round(100 * yearly.min(), 1),
        "years up": f"{int((yearly > 0).sum())}/{len(yearly)}",
        "t": round(monthly.mean() / monthly.std() * np.sqrt(len(monthly)), 2),
        "$10k →": int(10_000 * curve.iloc[-1]),
    }


def period(series, span):
    return series.loc[span[0]: span[1]]

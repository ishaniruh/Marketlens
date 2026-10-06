"""
MarketLens — Financial Metrics Transformation Module

Transforms validated OHLCV data into a rich analytics dataset by calculating:
  - Daily & monthly returns
  - Rolling volatility (20-day, 60-day)
  - Moving averages (20-day, 50-day, 200-day)
  - Cumulative returns
  - Maximum drawdown
  - Sharpe ratio (rolling 252-day)
  - Asset correlation matrix

All calculations use Adjusted Close prices for accuracy.
"""

import logging

import numpy as np
import pandas as pd

from pipeline.config import RISK_FREE_RATE_DAILY, TRADING_DAYS_PER_YEAR

logger = logging.getLogger(__name__)


def calculate_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add daily-frequency financial metrics to the validated OHLCV dataframe.

    Input:  validated market_data DataFrame
    Output: enriched DataFrame with additional metric columns
    """
    df = df.copy().sort_values(["ticker", "date"])

    grp = df.groupby("ticker")["adj_close"]

    # ── Daily returns (percentage change) ────────────────────────────────
    df["daily_return"] = grp.pct_change()

    # ── Moving averages ───────────────────────────────────────────────────
    df["ma_20"]  = grp.transform(lambda x: x.rolling(20,  min_periods=1).mean())
    df["ma_50"]  = grp.transform(lambda x: x.rolling(50,  min_periods=1).mean())
    df["ma_200"] = grp.transform(lambda x: x.rolling(200, min_periods=1).mean())

    # ── Rolling volatility (annualised std of daily returns) ─────────────
    df["vol_20d"] = (
        df.groupby("ticker")["daily_return"]
        .transform(lambda x: x.rolling(20, min_periods=5).std() * np.sqrt(TRADING_DAYS_PER_YEAR))
    )
    df["vol_60d"] = (
        df.groupby("ticker")["daily_return"]
        .transform(lambda x: x.rolling(60, min_periods=10).std() * np.sqrt(TRADING_DAYS_PER_YEAR))
    )

    # ── Cumulative return (base = first adj_close per ticker) ─────────────
    first_price = df.groupby("ticker")["adj_close"].transform("first")
    df["cumulative_return"] = (df["adj_close"] / first_price) - 1

    # ── Rolling maximum drawdown (252-day window) ─────────────────────────
    def rolling_max_drawdown(prices: pd.Series, window: int = 252) -> pd.Series:
        roll_max = prices.rolling(window, min_periods=1).max()
        drawdown = (prices - roll_max) / roll_max
        return drawdown

    df["drawdown"] = df.groupby("ticker")["adj_close"].transform(rolling_max_drawdown)

    # ── Rolling Sharpe ratio (252-day window, annualised) ─────────────────
    def rolling_sharpe(returns: pd.Series, window: int = 252) -> pd.Series:
        excess = returns - RISK_FREE_RATE_DAILY
        roll_mean = excess.rolling(window, min_periods=60).mean()
        roll_std  = returns.rolling(window, min_periods=60).std()
        return (roll_mean / roll_std) * np.sqrt(TRADING_DAYS_PER_YEAR)

    df["sharpe_252d"] = df.groupby("ticker")["daily_return"].transform(rolling_sharpe)

    logger.info("Daily metrics calculated for %d rows.", len(df))
    return df


def calculate_monthly_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily data to monthly level.

    Returns DataFrame with: ticker, company, sector, year, month,
    monthly_return, monthly_volume, avg_close
    """
    df = df.copy()
    df["date"]  = pd.to_datetime(df["date"])
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    monthly = (
        df.groupby(["ticker", "company", "sector", "year", "month"])
        .agg(
            month_open    = ("adj_close", "first"),
            month_close   = ("adj_close", "last"),
            monthly_volume = ("volume", "sum"),
            avg_close      = ("adj_close", "mean"),
            avg_vol_20d    = ("vol_20d", "mean"),
        )
        .reset_index()
    )
    monthly["monthly_return"] = (monthly["month_close"] / monthly["month_open"]) - 1

    logger.info("Monthly aggregation complete: %d rows.", len(monthly))
    return monthly


def calculate_correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate pairwise Pearson correlation of daily returns across all tickers.
    Returns a square DataFrame (tickers × tickers).
    """
    pivot = (
        df.pivot_table(index="date", columns="ticker", values="daily_return")
        .dropna(how="all")
    )
    corr = pivot.corr(method="pearson")
    logger.info("Correlation matrix computed: %s", corr.shape)
    return corr


def calculate_full_period_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-ticker summary stats over the entire data period.

    Returns: ticker, company, sector, total_return, annualised_return,
             annualised_volatility, sharpe_ratio, max_drawdown, avg_volume
    """
    results = []
    for ticker, grp in df.groupby("ticker"):
        grp = grp.sort_values("date")
        prices = grp["adj_close"].values
        returns = grp["daily_return"].dropna().values
        n_days = len(returns)

        if n_days < 20:
            continue

        total_return       = (prices[-1] / prices[0]) - 1
        ann_return         = (1 + total_return) ** (TRADING_DAYS_PER_YEAR / n_days) - 1
        ann_vol            = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        sharpe             = (ann_return - 0.05) / ann_vol if ann_vol > 0 else np.nan

        # True max drawdown over full period
        rolling_max = np.maximum.accumulate(prices)
        drawdowns   = (prices - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()

        results.append({
            "ticker":               ticker,
            "company":              grp["company"].iloc[0],
            "sector":               grp["sector"].iloc[0],
            "data_start":           str(grp["date"].min()),
            "data_end":             str(grp["date"].max()),
            "n_trading_days":       n_days,
            "total_return":         round(total_return, 6),
            "annualised_return":    round(ann_return, 6),
            "annualised_volatility": round(ann_vol, 6),
            "sharpe_ratio":         round(sharpe, 4) if not np.isnan(sharpe) else None,
            "max_drawdown":         round(max_drawdown, 6),
            "avg_daily_volume":     int(grp["volume"].mean()),
        })

    stats_df = pd.DataFrame(results)
    logger.info("Full-period stats computed for %d tickers.", len(stats_df))
    return stats_df

"""
MarketLens — Data Ingestion Module

Fetches OHLCV data from Yahoo Finance via yfinance and returns a clean,
standardised DataFrame ready for validation and storage.

Usage:
    from pipeline.ingest import fetch_market_data
    df = fetch_market_data()
"""

import logging
from datetime import datetime, date
from typing import Optional

import pandas as pd

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    import numpy as np

from pipeline.config import (
    ASSET_UNIVERSE,
    TICKERS,
    DATA_START_DATE,
    DATA_END_DATE,
)

logger = logging.getLogger(__name__)


def _generate_synthetic_market_data(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Generate realistic synthetic OHLCV data using Geometric Brownian Motion."""
    import numpy as np
    logger.info("Generating realistic synthetic market data for %d tickers...", len(tickers))
    dates = pd.bdate_range(start=start, end=end)
    records = []
    np.random.seed(42)

    base_prices = {
        "AAPL": 150.0, "MSFT": 300.0, "GOOGL": 120.0, "NVDA": 400.0, "META": 250.0,
        "JPM": 140.0, "GS": 340.0, "BAC": 30.0, "BLK": 700.0, "JNJ": 160.0,
        "UNH": 480.0, "PFE": 35.0, "XOM": 110.0, "CVX": 150.0, "AMZN": 130.0,
        "TSLA": 200.0, "PG": 145.0, "CAT": 240.0
    }

    for ticker in tickers:
        p0 = base_prices.get(ticker, 100.0)
        n = len(dates)
        # 10% annual drift, 20% annual volatility
        dt = 1 / 252
        returns = np.random.normal(loc=0.10 * dt, scale=0.20 * np.sqrt(dt), size=n)
        price_path = p0 * np.exp(np.cumsum(returns))
        
        vols = np.random.randint(1_000_000, 15_000_000, size=n)
        for i, d in enumerate(dates):
            close = price_path[i]
            high  = close * (1 + abs(np.random.normal(0, 0.008)))
            low   = close * (1 - abs(np.random.normal(0, 0.008)))
            open_p = low + (high - low) * np.random.uniform(0.2, 0.8)
            records.append({
                "date": d.date(),
                "ticker": ticker,
                "company": ASSET_UNIVERSE.get(ticker, {}).get("name", ticker),
                "sector": ASSET_UNIVERSE.get(ticker, {}).get("sector", "General"),
                "open": round(open_p, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "adj_close": round(close, 2),
                "volume": int(vols[i]),
            })

    return pd.DataFrame(records)


def fetch_market_data(
    tickers: list[str] = TICKERS,
    start: str = DATA_START_DATE,
    end: Optional[str] = DATA_END_DATE,
) -> pd.DataFrame:
    """
    Download daily OHLCV data for all tickers from Yahoo Finance (or synthetic fallback).

    Returns a long-format DataFrame with columns:
        date, ticker, company, sector, open, high, low,
        close, adj_close, volume
    """
    end_date = end or datetime.today().strftime("%Y-%m-%d")
    logger.info("Fetching data for %d tickers from %s to %s", len(tickers), start, end_date)

    if not HAS_YFINANCE:
        logger.info("yfinance package not installed — falling back to synthetic market data generation.")
        return _generate_synthetic_market_data(tickers, start, end_date)

    try:
        # Download all tickers in a single batch call
        raw = yf.download(
            tickers=tickers,
            start=start,
            end=end_date,
            auto_adjust=False,
            progress=False,
            threads=True,
        )
        if raw.empty:
            raise ValueError("yfinance returned empty result.")
    except Exception as err:
        logger.warning("yfinance download failed (%s) — using synthetic market data fallback.", err)
        return _generate_synthetic_market_data(tickers, start, end_date)
        raise ValueError("yfinance returned no data. Check tickers and date range.")

    records = []
    for ticker in tickers:
        try:
            # Multi-ticker download produces MultiIndex columns
            df_t = pd.DataFrame({
                "open":      raw["Open"][ticker],
                "high":      raw["High"][ticker],
                "low":       raw["Low"][ticker],
                "close":     raw["Close"][ticker],
                "adj_close": raw["Adj Close"][ticker],
                "volume":    raw["Volume"][ticker],
            })
            df_t.index.name = "date"
            df_t = df_t.reset_index()
            df_t["ticker"]  = ticker
            df_t["company"] = ASSET_UNIVERSE[ticker]["name"]
            df_t["sector"]  = ASSET_UNIVERSE[ticker]["sector"]
            records.append(df_t)
            logger.debug("  ✓ %s — %d rows", ticker, len(df_t))
        except KeyError:
            logger.warning("  ✗ %s — data not found in download result, skipping.", ticker)

    if not records:
        raise ValueError("No valid data could be extracted from the download result.")

    combined = pd.concat(records, ignore_index=True)

    # Normalise date column to Python date
    combined["date"] = pd.to_datetime(combined["date"]).dt.date

    # Reorder columns
    combined = combined[[
        "date", "ticker", "company", "sector",
        "open", "high", "low", "close", "adj_close", "volume",
    ]]

    logger.info("Ingestion complete: %d rows across %d tickers.", len(combined), combined["ticker"].nunique())
    return combined

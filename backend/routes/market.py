"""
MarketLens — Market Data Routes

Provides endpoints for:
  - Asset universe listing
  - Historical price data
  - Market overview (top performers, sector breakdown)
  - Asset comparison
  - Correlation matrix
"""

import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from backend.db import get_db_engine
from pipeline.config import ASSET_UNIVERSE, TICKERS

router = APIRouter()
logger = logging.getLogger(__name__)


def _execute(sql: str, params: dict = {}) -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@router.get("/assets")
def list_assets():
    """Return the full asset universe with metadata."""
    assets = [
        {"ticker": k, "company": v["name"], "sector": v["sector"]}
        for k, v in ASSET_UNIVERSE.items()
    ]
    return {"assets": assets, "count": len(assets)}


@router.get("/overview")
def market_overview():
    """
    Market overview: top performers, worst performers, sector summary,
    aggregate trading volume.
    """
    try:
        stats = _execute("""
            SELECT ticker, company, sector,
                   ROUND(annualised_return * 100, 2)     AS ann_return_pct,
                   ROUND(annualised_volatility * 100, 2) AS ann_vol_pct,
                   ROUND(sharpe_ratio, 2)                AS sharpe,
                   ROUND(max_drawdown * 100, 2)          AS max_drawdown_pct,
                   avg_daily_volume
            FROM asset_stats
            ORDER BY annualised_return DESC
        """)

        sector_perf = _execute("""
            SELECT sector,
                   COUNT(DISTINCT ticker)                    AS num_stocks,
                   ROUND(AVG(annualised_return) * 100, 2)   AS avg_return_pct,
                   ROUND(AVG(annualised_volatility)*100, 2) AS avg_vol_pct,
                   ROUND(AVG(sharpe_ratio), 2)              AS avg_sharpe
            FROM asset_stats
            GROUP BY sector
            ORDER BY avg_return_pct DESC
        """)

        return {
            "top_performers":   stats.head(5).to_dict(orient="records"),
            "worst_performers": stats.tail(5).to_dict(orient="records"),
            "all_assets":       stats.to_dict(orient="records"),
            "sector_breakdown": sector_perf.to_dict(orient="records"),
            "total_assets":     len(stats),
        }
    except Exception as e:
        logger.exception("market_overview failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices/{ticker}")
def get_price_history(
    ticker: str,
    days: int = Query(default=365, ge=30, le=2000, description="Number of trading days"),
):
    """Return price history with moving averages and volume for a single ticker."""
    ticker = ticker.upper()
    if ticker not in ASSET_UNIVERSE:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not in asset universe.")
    try:
        df = _execute("""
            SELECT date, ticker, company, sector,
                   ROUND(open, 2)      AS open,
                   ROUND(high, 2)      AS high,
                   ROUND(low, 2)       AS low,
                   ROUND(close, 2)     AS close,
                   ROUND(adj_close, 2) AS adj_close,
                   volume,
                   ROUND(daily_return * 100, 4)    AS daily_return_pct,
                   ROUND(ma_20, 2)    AS ma_20,
                   ROUND(ma_50, 2)    AS ma_50,
                   ROUND(ma_200, 2)   AS ma_200,
                   ROUND(vol_20d * 100, 2)  AS vol_20d_pct,
                   ROUND(cumulative_return * 100, 2) AS cumulative_return_pct,
                   ROUND(drawdown * 100, 2)    AS drawdown_pct,
                   ROUND(sharpe_252d, 2)       AS sharpe_rolling
            FROM market_data
            WHERE ticker = :ticker
            ORDER BY date DESC
            LIMIT :days
        """, {"ticker": ticker, "days": days})
        df = df.sort_values("date")
        return {
            "ticker": ticker,
            "company": ASSET_UNIVERSE[ticker]["name"],
            "sector":  ASSET_UNIVERSE[ticker]["sector"],
            "data":    df.to_dict(orient="records"),
            "count":   len(df),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sector/{sector}")
def get_sector_performance(sector: str):
    """Return all assets in a sector with performance metrics."""
    try:
        df = _execute("""
            SELECT ticker, company, sector,
                   ROUND(annualised_return * 100, 2)     AS ann_return_pct,
                   ROUND(annualised_volatility * 100, 2) AS ann_vol_pct,
                   ROUND(sharpe_ratio, 2)                AS sharpe,
                   ROUND(max_drawdown * 100, 2)          AS max_drawdown_pct,
                   avg_daily_volume,
                   data_start, data_end, n_trading_days
            FROM asset_stats
            WHERE LOWER(sector) = LOWER(:sector)
            ORDER BY annualised_return DESC
        """, {"sector": sector})
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for sector '{sector}'.")
        return {"sector": sector, "assets": df.to_dict(orient="records")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correlation")
def get_correlation_matrix(days: int = Query(default=504, ge=60, le=2000)):
    """Return pairwise correlation of daily returns."""
    try:
        df = _execute("""
            SELECT date, ticker, daily_return
            FROM market_data
            WHERE daily_return IS NOT NULL
            ORDER BY date DESC
            LIMIT :limit
        """, {"limit": days * len(TICKERS)})

        pivot = df.pivot_table(index="date", columns="ticker", values="daily_return")
        corr  = pivot.corr().round(4)
        return {
            "tickers": list(corr.columns),
            "matrix":  corr.values.tolist(),
            "labels":  [ASSET_UNIVERSE.get(t, {}).get("name", t) for t in corr.columns],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly-returns/{ticker}")
def get_monthly_returns(ticker: str):
    """Return monthly return calendar for a ticker."""
    ticker = ticker.upper()
    try:
        df = _execute("""
            SELECT year, month,
                   ROUND(monthly_return * 100, 2) AS monthly_return_pct,
                   monthly_volume, ROUND(avg_close, 2) AS avg_close
            FROM monthly_returns
            WHERE ticker = :ticker
            ORDER BY year, month
        """, {"ticker": ticker})
        return {"ticker": ticker, "monthly_returns": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

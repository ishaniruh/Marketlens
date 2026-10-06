"""MarketLens — Forecasting Routes"""

import logging
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from backend.db import get_db_engine
from models.forecaster import forecast_price_trend
from pipeline.config import ASSET_UNIVERSE

router = APIRouter()
logger = logging.getLogger(__name__)


def _load_price_data() -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT date, ticker, adj_close FROM market_data ORDER BY ticker, date
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@router.get("/{ticker}")
def get_forecast(
    ticker: str,
    horizon: int = Query(default=30, ge=5, le=90, description="Trading days ahead"),
):
    """
    Generate a price trend forecast for the given ticker.

    Uses Holt-Winters Exponential Smoothing on historical Adjusted Close prices.
    Returns historical data, forecast, and confidence interval.

    ⚠ Forecasts are illustrative trend estimates only — not investment advice.
    """
    ticker = ticker.upper()
    if ticker not in ASSET_UNIVERSE:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found.")
    try:
        df     = _load_price_data()
        result = forecast_price_trend(df, ticker, horizon=horizon)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Forecast failed for %s", ticker)
        raise HTTPException(status_code=500, detail=str(e))

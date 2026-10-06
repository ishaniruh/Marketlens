"""
MarketLens — Portfolio Analytics Routes
"""

import logging
from typing import Dict

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
try:
    from pydantic import field_validator
    USE_FIELD_VALIDATOR = True
except ImportError:
    from pydantic import validator
    USE_FIELD_VALIDATOR = False
from sqlalchemy import text

from backend.db import get_db_engine
from pipeline.portfolio import compute_portfolio_metrics
from pipeline.config import ASSET_UNIVERSE

router = APIRouter()
logger = logging.getLogger(__name__)


class PortfolioRequest(BaseModel):
    weights: Dict[str, float]   # {ticker: weight_as_decimal}
    portfolio_name: str = "My Portfolio"

    if USE_FIELD_VALIDATOR:
        @field_validator("weights")
        @classmethod
        def validate_weights(cls, v):
            if not v:
                raise ValueError("weights must not be empty.")
            if any(w < 0 for w in v.values()):
                raise ValueError("All weights must be non-negative.")
            total = sum(v.values())
            if abs(total - 1.0) > 0.001:
                raise ValueError(
                    f"Weights must sum to 1.0 (100%). Currently sum to {total:.4f}."
                )
            for ticker in v:
                if ticker not in ASSET_UNIVERSE:
                    raise ValueError(f"Ticker '{ticker}' is not in the supported asset universe.")
            return v
    else:
        @validator("weights")
        def validate_weights(cls, v):
            if not v:
                raise ValueError("weights must not be empty.")
            if any(w < 0 for w in v.values()):
                raise ValueError("All weights must be non-negative.")
            total = sum(v.values())
            if abs(total - 1.0) > 0.001:
                raise ValueError(
                    f"Weights must sum to 1.0 (100%). Currently sum to {total:.4f}."
                )
            for ticker in v:
                if ticker not in ASSET_UNIVERSE:
                    raise ValueError(f"Ticker '{ticker}' is not in the supported asset universe.")
            return v


def _load_market_data() -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT date, ticker, adj_close, daily_return, volume
            FROM market_data
            WHERE daily_return IS NOT NULL
            ORDER BY ticker, date
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@router.post("/analyse")
def analyse_portfolio(req: PortfolioRequest):
    """
    Compute full portfolio analytics for a given set of weighted assets.

    Body:
        weights: {"AAPL": 0.30, "MSFT": 0.25, "GOOGL": 0.20, "JPM": 0.25}
        portfolio_name: "My Tech Portfolio"
    """
    try:
        df       = _load_market_data()
        sector_map = {t: info["sector"] for t, info in ASSET_UNIVERSE.items()}
        result   = compute_portfolio_metrics(df, req.weights, sector_map)

        # Store snapshot in DB
        engine = get_db_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO portfolio_snapshots (
                    portfolio_name, tickers, weights,
                    total_return, annualised_return, annualised_volatility,
                    sharpe_ratio, max_drawdown, sector_allocation, risk_contribution
                ) VALUES (
                    :name, :tickers, :weights::jsonb,
                    :total_return, :ann_return, :ann_vol,
                    :sharpe, :max_dd, :sector_alloc::jsonb, :risk_contrib::jsonb
                )
            """), {
                "name":        req.portfolio_name,
                "tickers":     result["tickers"],
                "weights":     str(result["weights"]).replace("'", '"'),
                "total_return": result["total_portfolio_return"],
                "ann_return":  result["annualised_return"],
                "ann_vol":     result["annualised_volatility"],
                "sharpe":      result["sharpe_ratio"],
                "max_dd":      result["max_drawdown"],
                "sector_alloc": str(result["sector_allocation"]).replace("'", '"'),
                "risk_contrib": str(result["risk_contribution"]).replace("'", '"'),
            })

        # Remove large arrays from API response (use separate endpoint for chart data)
        response = {k: v for k, v in result.items()
                    if k not in ("portfolio_daily_returns", "equity_curve", "dates")}
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Portfolio analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/equity-curve")
def portfolio_equity_curve(req: PortfolioRequest):
    """Return equity curve data for charting."""
    try:
        df         = _load_market_data()
        sector_map = {t: info["sector"] for t, info in ASSET_UNIVERSE.items()}
        result     = compute_portfolio_metrics(df, req.weights, sector_map)
        return {
            "dates":        result["dates"],
            "equity_curve": result["equity_curve"],
            "disclaimer":   result["disclaimer"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

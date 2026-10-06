"""
MarketLens — Portfolio Analytics Module

Allows a user to define a weighted portfolio of assets and computes:
  - Weighted portfolio return
  - Portfolio volatility (using covariance matrix)
  - Sharpe ratio
  - Maximum drawdown
  - Asset-level contribution to return and risk
  - Sector allocation
  - Risk contribution (marginal contribution to portfolio variance)

DISCLAIMER: All calculations are based on historical data.
This is NOT financial advice.
"""

import logging
from typing import Dict

import numpy as np
import pandas as pd

from pipeline.config import TRADING_DAYS_PER_YEAR, RISK_FREE_RATE_ANNUAL

logger = logging.getLogger(__name__)


def validate_weights(weights: Dict[str, float]) -> None:
    """Ensure weights are positive and sum to 1.0 (±0.001 tolerance)."""
    if not weights:
        raise ValueError("Portfolio weights cannot be empty.")
    if any(w < 0 for w in weights.values()):
        raise ValueError("All portfolio weights must be non-negative.")
    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        raise ValueError(
            f"Portfolio weights must sum to 1.0 (100%). Current sum: {total:.4f}"
        )


def build_returns_matrix(df: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """
    Pivot daily returns into a (date × ticker) matrix.
    Drops any dates where any ticker has a missing return.
    """
    pivot = (
        df[df["ticker"].isin(tickers)]
        .pivot_table(index="date", columns="ticker", values="daily_return")
        .dropna()
    )
    return pivot


def compute_portfolio_metrics(
    df: pd.DataFrame,
    weights: Dict[str, float],
    sector_map: Dict[str, str],
) -> dict:
    """
    Compute full suite of portfolio metrics.

    Parameters
    ----------
    df       : enriched daily market_data DataFrame
    weights  : {ticker: weight} dict (weights must sum to 1.0)
    sector_map : {ticker: sector} for sector allocation breakdown

    Returns
    -------
    dict with all portfolio analytics
    """
    validate_weights(weights)

    tickers = list(weights.keys())
    w_array = np.array([weights[t] for t in tickers])

    returns_matrix = build_returns_matrix(df, tickers)

    # Align weights to columns
    available = [t for t in tickers if t in returns_matrix.columns]
    if len(available) < len(tickers):
        missing = set(tickers) - set(available)
        logger.warning("Missing return data for: %s", missing)

    returns_matrix = returns_matrix[available]
    w_array = np.array([weights[t] for t in available])
    w_array = w_array / w_array.sum()   # re-normalise after any exclusions

    # ── Portfolio daily returns ───────────────────────────────────────────
    portfolio_daily_returns = returns_matrix.values @ w_array

    # ── Annualised metrics ────────────────────────────────────────────────
    n_days = len(portfolio_daily_returns)
    total_portfolio_return  = np.prod(1 + portfolio_daily_returns) - 1
    ann_portfolio_return    = (1 + total_portfolio_return) ** (TRADING_DAYS_PER_YEAR / n_days) - 1
    ann_portfolio_volatility = portfolio_daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe_ratio = (
        (ann_portfolio_return - RISK_FREE_RATE_ANNUAL) / ann_portfolio_volatility
        if ann_portfolio_volatility > 0 else np.nan
    )

    # ── Maximum drawdown (portfolio equity curve) ─────────────────────────
    equity_curve = np.cumprod(1 + portfolio_daily_returns)
    rolling_max  = np.maximum.accumulate(equity_curve)
    drawdowns    = (equity_curve - rolling_max) / rolling_max
    max_drawdown = drawdowns.min()

    # ── Covariance matrix & risk contribution ────────────────────────────
    cov_matrix   = returns_matrix.cov() * TRADING_DAYS_PER_YEAR
    portfolio_var = w_array @ cov_matrix.values @ w_array
    # Marginal Contribution to Risk (MCR)
    marginal_contrib = cov_matrix.values @ w_array
    risk_contrib     = w_array * marginal_contrib / (portfolio_var ** 0.5)

    # ── Asset-level contribution to return ───────────────────────────────
    asset_total_returns = (1 + returns_matrix).prod() - 1
    return_contrib = {t: round(weights.get(t, 0) * float(r), 6)
                      for t, r in asset_total_returns.items()}

    # ── Sector allocation ─────────────────────────────────────────────────
    sector_alloc: Dict[str, float] = {}
    for t, w in zip(available, w_array):
        sector = sector_map.get(t, "Unknown")
        sector_alloc[sector] = sector_alloc.get(sector, 0.0) + float(w)

    # ── Build response ────────────────────────────────────────────────────
    result = {
        "tickers":                  available,
        "weights":                  {t: round(float(w), 6) for t, w in zip(available, w_array)},
        "n_trading_days":           n_days,
        "total_portfolio_return":   round(float(total_portfolio_return),    6),
        "annualised_return":        round(float(ann_portfolio_return),       6),
        "annualised_volatility":    round(float(ann_portfolio_volatility),   6),
        "sharpe_ratio":             round(float(sharpe_ratio), 4) if not np.isnan(sharpe_ratio) else None,
        "max_drawdown":             round(float(max_drawdown), 6),
        "sector_allocation":        {k: round(v, 6) for k, v in sector_alloc.items()},
        "return_contribution":      return_contrib,
        "risk_contribution":        {t: round(float(rc), 6) for t, rc in zip(available, risk_contrib)},
        "portfolio_daily_returns":  portfolio_daily_returns.tolist(),
        "equity_curve":             equity_curve.tolist(),
        "dates":                    [str(d) for d in returns_matrix.index],
        "disclaimer":               (
            "All metrics are derived from historical market data. "
            "Past performance is not indicative of future results. "
            "This is not financial advice."
        ),
    }

    logger.info(
        "Portfolio: return=%.2f%%, vol=%.2f%%, Sharpe=%.2f, MaxDD=%.2f%%",
        ann_portfolio_return * 100,
        ann_portfolio_volatility * 100,
        sharpe_ratio or 0,
        max_drawdown * 100,
    )
    return result

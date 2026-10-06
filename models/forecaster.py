"""
MarketLens — Price Trend Forecasting Module

Uses Exponential Smoothing (Holt-Winters / ETS) from statsmodels to generate
short-term price trend estimates.

Why Exponential Smoothing:
  - Transparent and interpretable
  - Industry-standard baseline for time-series analysis
  - Appropriate for non-stationary financial price series
  - Does NOT claim to "predict" stock prices — provides trend estimates
    with uncertainty quantification

⚠️  DISCLAIMER:
Stock prices are not reliably predictable. This component demonstrates
analytical thinking and time-series methodology.
Forecasts are illustrative trend estimates, NOT investment advice.
The model's confidence intervals widen significantly at longer horizons,
reflecting genuine uncertainty.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

logger = logging.getLogger(__name__)

FORECAST_HORIZON_DAYS = 30   # Default: 30 trading days (~6 weeks)


def forecast_price_trend(
    df: pd.DataFrame,
    ticker: str,
    horizon: int = FORECAST_HORIZON_DAYS,
    confidence_level: float = 0.90,
) -> dict:
    """
    Fit an Exponential Smoothing model to the adj_close price series
    for a given ticker and generate a forward trend estimate.

    Parameters
    ----------
    df         : enriched daily market_data DataFrame
    ticker     : ticker symbol to forecast
    horizon    : number of trading days to forecast ahead
    confidence_level : width of prediction interval

    Returns
    -------
    dict with:
        historical_dates, historical_prices,
        forecast_dates, forecast_values,
        lower_bound, upper_bound,
        model_params, disclaimer
    """
    # ── Prepare series ───────────────────────────────────────────────────
    ts = (
        df[df["ticker"] == ticker]
        .sort_values("date")[["date", "adj_close"]]
        .dropna()
    )
    if len(ts) < 60:
        raise ValueError(f"Insufficient data for {ticker}. Need at least 60 observations.")

    prices = ts["adj_close"].values.astype(float)
    dates  = pd.to_datetime(ts["date"])

    # ── Fit model ─────────────────────────────────────────────────────────
    smoothing_level = 0.3
    smoothing_trend = 0.1
    resid_std = float(np.std(np.diff(prices))) if len(prices) > 1 else 1.0

    if HAS_STATSMODELS:
        try:
            model = ExponentialSmoothing(
                prices,
                trend="add",
                damped_trend=True,
                initialization_method="estimated",
            )
            fitted = model.fit(optimized=True, use_brute=False)
            forecast_vals = fitted.forecast(horizon)
            smoothing_level = float(fitted.params.get("smoothing_level", 0.3))
            smoothing_trend = float(fitted.params.get("smoothing_trend", 0.1))
            resid_std = float(fitted.resid.std())
        except Exception as exc:
            logger.warning("ETS with trend failed (%s), falling back to simple smoothing.", exc)
            model  = ExponentialSmoothing(prices, initialization_method="estimated")
            fitted = model.fit(optimized=True)
            forecast_vals = fitted.forecast(horizon)
            smoothing_level = float(fitted.params.get("smoothing_level", 0.3))
            resid_std = float(fitted.resid.std())
    else:
        # Fallback: Holt's linear exponential smoothing in pure numpy
        logger.info("statsmodels not installed; using numpy Holt's exponential smoothing fallback.")
        alpha, beta = 0.3, 0.1
        level, trend = prices[0], prices[1] - prices[0]
        for p in prices[1:]:
            prev_level = level
            level = alpha * p + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend
        forecast_vals = np.array([level + (h + 1) * trend for h in range(horizon)])

    # Simulate prediction intervals via residual bootstrap
    z_score   = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}.get(confidence_level, 1.645)

    # Uncertainty grows proportionally with horizon (random-walk assumption)
    interval_width = resid_std * z_score * np.sqrt(np.arange(1, horizon + 1))
    lower_bound    = forecast_vals - interval_width
    upper_bound    = forecast_vals + interval_width

    # ── Future dates (business days) ─────────────────────────────────────
    last_date    = dates.iloc[-1]
    future_dates = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=horizon)

    logger.info(
        "Forecast for %s: %d-day horizon, last_price=%.2f, forecast_end=%.2f",
        ticker, horizon, prices[-1], forecast_vals[-1],
    )

    return {
        "ticker":             ticker,
        "historical_dates":   [str(d.date()) for d in dates[-252:]],  # Last year of history
        "historical_prices":  prices[-252:].tolist(),
        "forecast_dates":     [str(d.date()) for d in future_dates],
        "forecast_values":    forecast_vals.tolist(),
        "lower_bound":        np.maximum(lower_bound, 0).tolist(),     # Prices can't be negative
        "upper_bound":        upper_bound.tolist(),
        "model_name":         "Exponential Smoothing (Holt-Winters ETS)" if HAS_STATSMODELS else "Holt Exponential Smoothing (Numpy)",
        "smoothing_level":    round(smoothing_level, 4),
        "smoothing_trend":    round(smoothing_trend, 4),
        "residual_std":       round(resid_std, 4),
        "horizon_days":       horizon,
        "confidence_level":   confidence_level,
        "disclaimer": (
            f"IMPORTANT: This {horizon}-day trend estimate uses Exponential Smoothing "
            "on historical prices. Stock prices are not reliably predictable. "
            "Confidence intervals widen significantly over the forecast horizon. "
            "This output is illustrative of time-series methodology only. "
            "It is NOT financial advice or an investment recommendation."
        ),
    }

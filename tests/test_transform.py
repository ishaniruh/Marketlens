"""
Tests for financial metric calculations (transform module).
"""

import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta

from pipeline.transform import (
    calculate_daily_metrics,
    calculate_monthly_returns,
    calculate_full_period_stats,
)


def _make_price_series(start_price=100.0, n=300, ticker="TEST"):
    """Generate synthetic price series for testing."""
    rng   = np.random.default_rng(42)
    daily = rng.normal(0.0005, 0.015, n)   # ~12% ann return, ~24% ann vol
    prices = start_price * np.cumprod(1 + daily)

    dates = [date(2020, 1, 2) + timedelta(days=i) for i in range(n)]

    return pd.DataFrame({
        "date":      dates,
        "ticker":    ticker,
        "company":   "Test Corp",
        "sector":    "Technology",
        "open":      prices * 0.99,
        "high":      prices * 1.01,
        "low":       prices * 0.98,
        "close":     prices,
        "adj_close": prices,
        "volume":    1_000_000,
    })


class TestDailyMetrics:

    def setup_method(self):
        self.df = _make_price_series()

    def test_daily_return_computed(self):
        enriched = calculate_daily_metrics(self.df)
        # First row should be NaN, rest should be numeric
        assert enriched["daily_return"].iloc[0] is np.nan or pd.isna(enriched["daily_return"].iloc[0])
        assert enriched["daily_return"].iloc[1:].notna().all()

    def test_daily_return_range(self):
        enriched = calculate_daily_metrics(self.df)
        rets = enriched["daily_return"].dropna()
        # No individual daily return should exceed ±50% for a normal stock
        assert (rets.abs() < 0.5).all(), "Unrealistic daily returns detected"

    def test_moving_averages_exist(self):
        enriched = calculate_daily_metrics(self.df)
        for col in ["ma_20", "ma_50", "ma_200"]:
            assert col in enriched.columns
            assert enriched[col].notna().any()

    def test_ma20_is_rolling_mean(self):
        enriched = calculate_daily_metrics(self.df)
        # MA20 at row 25 should equal the mean of prices 6..25
        idx = 25
        expected = self.df["adj_close"].iloc[idx - 19: idx + 1].mean()
        actual   = enriched["ma_20"].iloc[idx]
        assert abs(actual - expected) < 0.01

    def test_cumulative_return_starts_at_zero(self):
        enriched = calculate_daily_metrics(self.df)
        assert enriched["cumulative_return"].iloc[0] == pytest.approx(0.0, abs=1e-6)

    def test_drawdown_is_non_positive(self):
        enriched = calculate_daily_metrics(self.df)
        dd = enriched["drawdown"].dropna()
        assert (dd <= 0.001).all(), "Drawdown values should be ≤ 0"

    def test_volatility_positive(self):
        enriched = calculate_daily_metrics(self.df)
        vol = enriched["vol_20d"].dropna()
        assert (vol > 0).all()


class TestMonthlyReturns:

    def test_monthly_returns_aggregated(self):
        df       = _make_price_series()
        enriched = calculate_daily_metrics(df)
        monthly  = calculate_monthly_returns(enriched)
        assert "monthly_return" in monthly.columns
        assert len(monthly) > 0

    def test_monthly_volume_positive(self):
        df       = _make_price_series()
        enriched = calculate_daily_metrics(df)
        monthly  = calculate_monthly_returns(enriched)
        assert (monthly["monthly_volume"] > 0).all()


class TestFullPeriodStats:

    def test_stats_computed_for_all_tickers(self):
        df  = pd.concat([_make_price_series(ticker="AAPL"), _make_price_series(ticker="MSFT")])
        enriched = calculate_daily_metrics(df)
        stats = calculate_full_period_stats(enriched)
        assert set(stats["ticker"]) == {"AAPL", "MSFT"}

    def test_annualised_return_reasonable(self):
        df       = _make_price_series()
        enriched = calculate_daily_metrics(df)
        stats    = calculate_full_period_stats(enriched)
        ann_ret  = stats["annualised_return"].iloc[0]
        # For our synthetic series it should be between -100% and +200%
        assert -1.0 < ann_ret < 2.0

    def test_max_drawdown_negative(self):
        df       = _make_price_series()
        enriched = calculate_daily_metrics(df)
        stats    = calculate_full_period_stats(enriched)
        assert stats["max_drawdown"].iloc[0] <= 0

    def test_sharpe_ratio_is_float(self):
        df       = _make_price_series()
        enriched = calculate_daily_metrics(df)
        stats    = calculate_full_period_stats(enriched)
        sharpe   = stats["sharpe_ratio"].iloc[0]
        assert sharpe is not None
        assert isinstance(float(sharpe), float)

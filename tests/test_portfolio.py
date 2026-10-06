"""
Tests for portfolio analytics (weight validation, risk metrics).
"""

import pytest
import numpy as np
import pandas as pd
from datetime import date, timedelta

from pipeline.portfolio import validate_weights, compute_portfolio_metrics


def _make_multi_asset_df(tickers=("AAPL", "MSFT", "JPM"), n=252):
    """Generate synthetic multi-asset daily return data."""
    rng = np.random.default_rng(42)
    rows = []
    for ticker in tickers:
        drift = rng.uniform(0.0003, 0.0008)
        vol   = rng.uniform(0.010, 0.020)
        daily = rng.normal(drift, vol, n)
        prices = 100.0 * np.cumprod(1 + daily)
        for i in range(n):
            rows.append({
                "date":        date(2022, 1, 3) + timedelta(days=i),
                "ticker":      ticker,
                "adj_close":   prices[i],
                "daily_return": daily[i],
                "volume":      1_000_000,
            })
    return pd.DataFrame(rows)


class TestValidateWeights:

    def test_valid_weights_pass(self):
        validate_weights({"AAPL": 0.5, "MSFT": 0.5})  # Should not raise

    def test_weights_not_summing_to_one_raises(self):
        with pytest.raises(ValueError, match="sum to 1.0"):
            validate_weights({"AAPL": 0.4, "MSFT": 0.4})   # sum = 0.8

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            validate_weights({"AAPL": 1.2, "MSFT": -0.2})

    def test_empty_weights_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_weights({})

    def test_tolerance_accepted(self):
        # 0.9999 should pass (within tolerance)
        validate_weights({"AAPL": 0.3333, "MSFT": 0.3333, "JPM": 0.3334})


class TestPortfolioMetrics:

    def setup_method(self):
        self.df = _make_multi_asset_df()
        self.weights    = {"AAPL": 0.4, "MSFT": 0.35, "JPM": 0.25}
        self.sector_map = {"AAPL": "Technology", "MSFT": "Technology", "JPM": "Financial Services"}

    def test_metrics_keys_present(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        required_keys = [
            "annualised_return", "annualised_volatility", "sharpe_ratio",
            "max_drawdown", "sector_allocation", "risk_contribution", "return_contribution",
        ]
        for k in required_keys:
            assert k in result, f"Missing key: {k}"

    def test_volatility_positive(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        assert result["annualised_volatility"] > 0

    def test_max_drawdown_non_positive(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        assert result["max_drawdown"] <= 0

    def test_sector_allocation_sums_to_one(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        total  = sum(result["sector_allocation"].values())
        assert abs(total - 1.0) < 0.001

    def test_sharpe_is_numeric(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        sharpe = result["sharpe_ratio"]
        assert sharpe is None or isinstance(sharpe, (int, float))

    def test_risk_contrib_tickers_match_weights(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        assert set(result["risk_contribution"].keys()) == set(self.weights.keys())

    def test_disclaimer_present(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        assert "disclaimer" in result
        assert "not financial advice" in result["disclaimer"].lower()

    def test_equity_curve_starts_at_one(self):
        result = compute_portfolio_metrics(self.df, self.weights, self.sector_map)
        assert result["equity_curve"][0] == pytest.approx(1.0, rel=0.01)

    def test_invalid_weights_raises(self):
        bad_weights = {"AAPL": 0.6, "MSFT": 0.6}   # sum = 1.2
        with pytest.raises(ValueError):
            compute_portfolio_metrics(self.df, bad_weights, self.sector_map)

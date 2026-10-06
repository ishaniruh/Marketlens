"""
Tests for the data validation module.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import date

from pipeline.validate import validate_market_data


def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Helper: create a minimal valid OHLCV DataFrame from row dicts."""
    defaults = {
        "date": date(2023, 1, 3),
        "ticker": "TEST",
        "company": "Test Corp",
        "sector": "Technology",
        "open": 100.0,
        "high": 105.0,
        "low": 98.0,
        "close": 102.0,
        "adj_close": 102.0,
        "volume": 1_000_000,
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


class TestValidateMarketData:

    def test_valid_data_passes_unchanged(self):
        df = _make_df([
            {"date": date(2023, 1, 3), "ticker": "AAPL"},
            {"date": date(2023, 1, 4), "ticker": "AAPL"},
        ])
        clean, report = validate_market_data(df)
        assert len(clean) == 2
        assert report["duplicates_removed"] == 0
        assert report["negative_price_rows"] == 0

    def test_duplicate_removal(self):
        df = _make_df([
            {"date": date(2023, 1, 3), "ticker": "AAPL"},
            {"date": date(2023, 1, 3), "ticker": "AAPL"},  # duplicate
        ])
        clean, report = validate_market_data(df)
        assert len(clean) == 1
        assert report["duplicates_removed"] == 1

    def test_negative_price_rows_removed(self):
        df = _make_df([
            {"date": date(2023, 1, 3), "ticker": "AAPL", "adj_close": 100.0},
            {"date": date(2023, 1, 4), "ticker": "AAPL", "adj_close": -5.0},  # bad
        ])
        clean, report = validate_market_data(df)
        assert len(clean) == 1
        assert report["negative_price_rows"] == 1

    def test_missing_required_column_raises(self):
        df = pd.DataFrame([{"date": date(2023, 1, 3), "ticker": "AAPL"}])
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_market_data(df)

    def test_missing_price_filled_by_forward_fill(self):
        df = _make_df([
            {"date": date(2023, 1, 3), "ticker": "AAPL", "adj_close": 100.0},
            {"date": date(2023, 1, 4), "ticker": "AAPL", "adj_close": np.nan},
        ])
        clean, report = validate_market_data(df)
        # NaN row is filled, not dropped
        assert len(clean) == 2
        assert clean[clean["date"] == date(2023, 1, 4)]["adj_close"].iloc[0] == 100.0

    def test_negative_volume_removed(self):
        df = _make_df([
            {"date": date(2023, 1, 3), "ticker": "AAPL", "volume": 1_000_000},
            {"date": date(2023, 1, 4), "ticker": "AAPL", "volume": -500},  # bad
        ])
        clean, report = validate_market_data(df)
        assert report["negative_volume_rows"] == 1
        assert len(clean) == 1

    def test_multiple_tickers(self):
        df = _make_df([
            {"date": date(2023, 1, 3), "ticker": "AAPL"},
            {"date": date(2023, 1, 3), "ticker": "MSFT"},
            {"date": date(2023, 1, 4), "ticker": "AAPL"},
            {"date": date(2023, 1, 4), "ticker": "MSFT"},
        ])
        clean, report = validate_market_data(df)
        assert report["tickers_present"] == 2
        assert len(clean) == 4

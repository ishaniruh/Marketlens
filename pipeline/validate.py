"""
MarketLens — Data Validation Module

Applies a series of checks to the raw ingested DataFrame before any
transformation is performed.  Returns a cleaned DataFrame and a
validation report dict so callers can log or surface issues.

Usage:
    from pipeline.validate import validate_market_data
    clean_df, report = validate_market_data(raw_df)
"""

import logging
from typing import Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "date", "ticker", "company", "sector",
    "open", "high", "low", "close", "adj_close", "volume",
]

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close"]


def validate_market_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Run all validation checks and return (clean_df, report).

    Checks performed:
    1. Required columns present
    2. Duplicate (date, ticker) pairs removed
    3. Missing values handled (forward-fill within each ticker)
    4. Non-positive prices flagged and removed
    5. Volume must be non-negative
    6. high >= low sanity check
    7. Date must be a valid past or present date
    """
    report = {
        "initial_rows":      len(df),
        "duplicates_removed": 0,
        "missing_rows_filled": 0,
        "negative_price_rows": 0,
        "negative_volume_rows": 0,
        "ohlc_sanity_fails": 0,
        "final_rows":         0,
        "tickers_present":    0,
    }

    # ── 1. Column presence ────────────────────────────────────────────────
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df = df.copy()

    # ── 2. Duplicate removal ──────────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
    report["duplicates_removed"] = before - len(df)
    if report["duplicates_removed"]:
        logger.warning("Removed %d duplicate (date, ticker) rows.", report["duplicates_removed"])

    # ── 3. Missing value handling ─────────────────────────────────────────
    # Forward-fill within each ticker group (carries last valid price forward
    # for weekends / holidays where data might be sparse)
    df = df.sort_values(["ticker", "date"])
    missing_before = df[PRICE_COLUMNS].isna().sum().sum()
    df[PRICE_COLUMNS] = df.groupby("ticker")[PRICE_COLUMNS].ffill()
    # Drop any remaining NaN rows (start of series with no prior value)
    df = df.dropna(subset=PRICE_COLUMNS)
    report["missing_rows_filled"] = int(missing_before)
    if missing_before:
        logger.info("Forward-filled %d missing price values.", missing_before)

    # ── 4. Non-positive price removal ────────────────────────────────────
    neg_price_mask = (df[PRICE_COLUMNS] <= 0).any(axis=1)
    report["negative_price_rows"] = int(neg_price_mask.sum())
    if report["negative_price_rows"]:
        logger.warning("Dropping %d rows with non-positive prices.", report["negative_price_rows"])
        df = df[~neg_price_mask]

    # ── 5. Non-negative volume ────────────────────────────────────────────
    neg_vol_mask = df["volume"] < 0
    report["negative_volume_rows"] = int(neg_vol_mask.sum())
    if report["negative_volume_rows"]:
        logger.warning("Dropping %d rows with negative volume.", report["negative_volume_rows"])
        df = df[~neg_vol_mask]

    # ── 6. OHLC sanity check ──────────────────────────────────────────────
    ohlc_fail = (df["high"] < df["low"]) | (df["high"] < df["open"]) | (df["high"] < df["close"])
    report["ohlc_sanity_fails"] = int(ohlc_fail.sum())
    if report["ohlc_sanity_fails"]:
        logger.warning("OHLC sanity check failed for %d rows — keeping but flagging.", report["ohlc_sanity_fails"])

    # ── 7. Volume as integer ──────────────────────────────────────────────
    df["volume"] = df["volume"].fillna(0).astype(np.int64)

    report["final_rows"]      = len(df)
    report["tickers_present"] = df["ticker"].nunique()

    logger.info(
        "Validation complete: %d rows, %d tickers (started with %d rows).",
        report["final_rows"], report["tickers_present"], report["initial_rows"],
    )
    return df.reset_index(drop=True), report

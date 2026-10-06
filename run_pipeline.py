"""
MarketLens — Pipeline Runner

Executes the complete data engineering & analytics workflow:
  1. Ingestion: Download OHLCV market data from Yahoo Finance (or synthetic fallback)
  2. Validation: Clean duplicates, handle missing values & anomalies
  3. Transformation: Compute returns, rolling volatility, Sharpe, MAs
  4. CSV Persistence: Save raw & processed datasets locally
  5. DB Loading: Push to PostgreSQL database if running
  6. Forecasting & Analytics Summary: Output key asset metrics

Usage:
    python run_pipeline.py
"""

import os
import sys
import logging
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MarketLensRunner")

from pipeline.config import TICKERS, RAW_DATA_PATH, PROCESSED_DATA_PATH
from pipeline.ingest import fetch_market_data
from pipeline.validate import validate_market_data
from pipeline.transform import (
    calculate_daily_metrics,
    calculate_monthly_returns,
    calculate_full_period_stats,
)
from models.regime_classifier import train_regime_classifier, predict_regimes
from models.forecaster import forecast_price_trend


def main():
    print("=" * 65)
    print(" MarketLens -- Financial Intelligence Pipeline Execution")
    print("=" * 65)

    # Step 1: Ingestion
    print("\n[1/5] Ingesting historical market data via Yahoo Finance...")
    raw_df = fetch_market_data()
    os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
    raw_df.to_csv(RAW_DATA_PATH, index=False)
    print(f"      [+] Ingested {len(raw_df)} records for {raw_df['ticker'].nunique()} assets.")
    print(f"      [+] Saved raw dataset to: {RAW_DATA_PATH}")

    # Step 2: Validation
    print("\n[2/5] Running data quality & validation checks...")
    clean_df, report = validate_market_data(raw_df)
    print(f"      [+] Validated data: {len(clean_df)} clean records passed validation.")

    # Step 3: Transformation
    print("\n[3/5] Computing financial metrics (returns, MAs, rolling volatility, Sharpe)...")
    daily_df   = calculate_daily_metrics(clean_df)
    monthly_df = calculate_monthly_returns(daily_df)
    stats_df   = calculate_full_period_stats(daily_df)

    os.makedirs(os.path.dirname(PROCESSED_DATA_PATH), exist_ok=True)
    daily_df.to_csv(PROCESSED_DATA_PATH, index=False)
    print(f"      [+] Enriched daily metrics saved to: {PROCESSED_DATA_PATH}")

    # Step 4: Asset Summary & Analytics
    print("\n[4/5] Multi-Asset Analytics Summary:")
    print("-" * 65)
    print(f"{'Ticker':<8} {'Ann. Return':<13} {'Ann. Volatility':<16} {'Sharpe':<10} {'Max DD':<10}")
    print("-" * 65)
    for _, row in stats_df.iterrows():
        t        = row['ticker']
        ann_ret  = f"{row['annualised_return'] * 100:+.2f}%"
        ann_vol  = f"{row['annualised_volatility'] * 100:.2f}%"
        sharpe   = f"{row['sharpe_ratio']:.2f}" if pd.notna(row['sharpe_ratio']) else "N/A"
        max_dd   = f"{row['max_drawdown'] * 100:.2f}%"
        print(f"{t:<8} {ann_ret:<13} {ann_vol:<16} {sharpe:<10} {max_dd:<10}")
    print("-" * 65)

    # Step 5: Market Regime & Sample Trend Forecast
    print("\n[5/5] Testing Market Regime & Price Forecasting Engine...")
    sample_ticker = "AAPL"
    
    # Train regime classifier & run inference
    regime_results = train_regime_classifier(daily_df)
    pred_df = predict_regimes(daily_df)
    latest_regime = pred_df[pred_df["ticker"] == sample_ticker]["regime_label"].iloc[-1]
    print(f"      [+] {sample_ticker} Market Regime : {latest_regime} (CV Accuracy: {regime_results['cv_accuracy'] * 100:.1f}%)")

    forecast = forecast_price_trend(daily_df, sample_ticker, horizon=30)
    print(f"      [+] {sample_ticker} 30-Day Forecast: Last={forecast['historical_prices'][-1]:.2f} -> Forecast End={forecast['forecast_values'][-1]:.2f}")

    # Database loading attempt (optional)
    try:
        from backend.db import get_db_engine
        engine = get_db_engine()
        daily_df.to_sql("market_data", engine, if_exists="replace", index=False)
        stats_df.to_sql("asset_stats", engine, if_exists="replace", index=False)
        print("\n      [+] PostgreSQL connection detected -- Data loaded successfully into database tables!")
    except Exception:
        print("\n      [i] Note: Local PostgreSQL database offline -- pipeline completed successfully in CSV fallback mode.")

    print("\n" + "=" * 65)
    print(" Pipeline run complete! MarketLens is ready for dashboard / API serving.")
    print("=" * 65)


if __name__ == "__main__":
    main()

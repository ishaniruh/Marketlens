"""
MarketLens — Orchestration Script

Runs the full end-to-end data pipeline:
  1. Ingest  → yfinance → raw DataFrame
  2. Validate → clean + report
  3. Transform → metrics
  4. Persist → PostgreSQL

Run this script to populate (or refresh) the database.

Usage:
    python -m pipeline.run_pipeline
    python -m pipeline.run_pipeline --tickers AAPL MSFT GOOGL
"""

import argparse
import logging
import sys
from datetime import datetime

from pipeline.ingest    import fetch_market_data
from pipeline.validate  import validate_market_data
from pipeline.transform import (
    calculate_daily_metrics,
    calculate_monthly_returns,
    calculate_full_period_stats,
)
from pipeline.database  import (
    get_engine,
    initialise_schema,
    save_market_data,
    save_monthly_returns,
    save_full_period_stats,
)
from pipeline.config import TICKERS

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline.run_pipeline")


def run_pipeline(tickers: list[str] | None = None) -> None:
    start_time = datetime.now()
    tickers = tickers or TICKERS
    logger.info("═" * 60)
    logger.info("MarketLens Pipeline starting — %d tickers", len(tickers))
    logger.info("═" * 60)

    # ── Step 1: Ingest ───────────────────────────────────────────────────
    logger.info("[1/5] Ingesting data from Yahoo Finance …")
    raw_df = fetch_market_data(tickers=tickers)

    # ── Step 2: Validate ─────────────────────────────────────────────────
    logger.info("[2/5] Validating raw data …")
    clean_df, report = validate_market_data(raw_df)
    logger.info("Validation report: %s", report)

    # ── Step 3: Transform ────────────────────────────────────────────────
    logger.info("[3/5] Calculating daily metrics …")
    enriched_df = calculate_daily_metrics(clean_df)

    logger.info("[3/5] Calculating monthly returns …")
    monthly_df = calculate_monthly_returns(enriched_df)

    logger.info("[3/5] Calculating full-period stats …")
    stats_df = calculate_full_period_stats(enriched_df)

    # ── Step 4: Database ─────────────────────────────────────────────────
    logger.info("[4/5] Connecting to PostgreSQL …")
    engine = get_engine()

    logger.info("[4/5] Initialising schema …")
    initialise_schema(engine)

    logger.info("[5/5] Persisting market_data …")
    n = save_market_data(enriched_df, engine)
    logger.info("  → %d rows persisted to market_data.", n)

    logger.info("[5/5] Persisting monthly_returns …")
    save_monthly_returns(monthly_df, engine)

    logger.info("[5/5] Persisting asset_stats …")
    save_full_period_stats(stats_df, engine)

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("═" * 60)
    logger.info("Pipeline complete in %.1f seconds.", elapsed)
    logger.info("═" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the MarketLens data pipeline.")
    parser.add_argument(
        "--tickers", nargs="+", default=None,
        help="Space-separated list of ticker symbols (default: all 18 assets).",
    )
    args = parser.parse_args()
    try:
        run_pipeline(tickers=args.tickers)
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        sys.exit(1)

"""
MarketLens — Database Layer

Handles SQLAlchemy engine creation and all DataFrame → PostgreSQL persistence.
Uses upsert-style operations (INSERT ... ON CONFLICT DO UPDATE) to make
pipeline runs idempotent.

Usage:
    from pipeline.database import get_engine, save_market_data, ...
"""

import logging
import os
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_engine(
    host:     Optional[str] = None,
    port:     Optional[int] = None,
    dbname:   Optional[str] = None,
    user:     Optional[str] = None,
    password: Optional[str] = None,
) -> Engine:
    """Create and return a SQLAlchemy engine using env vars or parameters."""
    host     = host     or os.getenv("DB_HOST",     "localhost")
    port     = port     or int(os.getenv("DB_PORT", "5432"))
    dbname   = dbname   or os.getenv("DB_NAME",     "marketlens")
    user     = user     or os.getenv("DB_USER",     "marketlens_user")
    password = password or os.getenv("DB_PASSWORD", "marketlens_pass")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_engine(url, pool_pre_ping=True)
    logger.info("Database engine created: %s:%s/%s", host, port, dbname)
    return engine


def initialise_schema(engine: Engine) -> None:
    """Run the SQL schema creation script."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "init.sql")
    schema_path = os.path.normpath(schema_path)
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    with engine.begin() as conn:
        conn.execute(text(schema_sql))
    logger.info("Schema initialised.")


def save_market_data(df: pd.DataFrame, engine: Engine) -> int:
    """
    Persist the enriched daily market data DataFrame.
    Uses COPY-based bulk insert into a staging table, then upserts.
    Returns the number of rows inserted/updated.
    """
    # pandas to_sql with replace on staging, then upsert from staging → main
    staging = "market_data_staging"
    df.to_sql(staging, engine, if_exists="replace", index=False, method="multi", chunksize=5000)

    upsert_sql = """
        INSERT INTO market_data (
            date, ticker, company, sector,
            open, high, low, close, adj_close, volume,
            daily_return, ma_20, ma_50, ma_200,
            vol_20d, vol_60d, cumulative_return, drawdown, sharpe_252d
        )
        SELECT
            date, ticker, company, sector,
            open, high, low, close, adj_close, volume,
            daily_return, ma_20, ma_50, ma_200,
            vol_20d, vol_60d, cumulative_return, drawdown, sharpe_252d
        FROM market_data_staging
        ON CONFLICT (date, ticker)
        DO UPDATE SET
            adj_close        = EXCLUDED.adj_close,
            close            = EXCLUDED.close,
            volume           = EXCLUDED.volume,
            daily_return     = EXCLUDED.daily_return,
            ma_20            = EXCLUDED.ma_20,
            ma_50            = EXCLUDED.ma_50,
            ma_200           = EXCLUDED.ma_200,
            vol_20d          = EXCLUDED.vol_20d,
            vol_60d          = EXCLUDED.vol_60d,
            cumulative_return = EXCLUDED.cumulative_return,
            drawdown         = EXCLUDED.drawdown,
            sharpe_252d      = EXCLUDED.sharpe_252d,
            updated_at       = NOW();
    """
    with engine.begin() as conn:
        conn.execute(text(upsert_sql))

    logger.info("market_data upsert complete.")
    return len(df)


def save_monthly_returns(df: pd.DataFrame, engine: Engine) -> None:
    staging = "monthly_returns_staging"
    df.to_sql(staging, engine, if_exists="replace", index=False, method="multi", chunksize=2000)

    sql = """
        INSERT INTO monthly_returns (
            ticker, company, sector, year, month,
            month_open, month_close, monthly_return,
            monthly_volume, avg_close, avg_vol_20d
        )
        SELECT
            ticker, company, sector, year, month,
            month_open, month_close, monthly_return,
            monthly_volume, avg_close, avg_vol_20d
        FROM monthly_returns_staging
        ON CONFLICT (ticker, year, month)
        DO UPDATE SET
            month_close    = EXCLUDED.month_close,
            monthly_return = EXCLUDED.monthly_return,
            monthly_volume = EXCLUDED.monthly_volume,
            avg_close      = EXCLUDED.avg_close,
            avg_vol_20d    = EXCLUDED.avg_vol_20d,
            updated_at     = NOW();
    """
    with engine.begin() as conn:
        conn.execute(text(sql))
    logger.info("monthly_returns upsert complete.")


def save_full_period_stats(df: pd.DataFrame, engine: Engine) -> None:
    df.to_sql("asset_stats", engine, if_exists="replace", index=False, method="multi")
    logger.info("asset_stats table replaced.")

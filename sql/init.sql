-- ============================================================
--  MarketLens — PostgreSQL Schema Initialisation
--  Run once to create all tables. Safe to re-run (IF NOT EXISTS).
-- ============================================================

-- ── Core OHLCV + metrics table ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_data (
    id              BIGSERIAL PRIMARY KEY,
    date            DATE          NOT NULL,
    ticker          VARCHAR(10)   NOT NULL,
    company         VARCHAR(100)  NOT NULL,
    sector          VARCHAR(50)   NOT NULL,
    open            NUMERIC(14,4),
    high            NUMERIC(14,4),
    low             NUMERIC(14,4),
    close           NUMERIC(14,4),
    adj_close       NUMERIC(14,4),
    volume          BIGINT,
    daily_return    NUMERIC(10,6),
    ma_20           NUMERIC(14,4),
    ma_50           NUMERIC(14,4),
    ma_200          NUMERIC(14,4),
    vol_20d         NUMERIC(10,6),
    vol_60d         NUMERIC(10,6),
    cumulative_return NUMERIC(10,6),
    drawdown        NUMERIC(10,6),
    sharpe_252d     NUMERIC(10,4),
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   DEFAULT NOW(),
    UNIQUE (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_market_data_ticker ON market_data(ticker);
CREATE INDEX IF NOT EXISTS idx_market_data_date   ON market_data(date);
CREATE INDEX IF NOT EXISTS idx_market_data_sector ON market_data(sector);

-- ── Monthly aggregations ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS monthly_returns (
    id              BIGSERIAL PRIMARY KEY,
    ticker          VARCHAR(10)   NOT NULL,
    company         VARCHAR(100)  NOT NULL,
    sector          VARCHAR(50)   NOT NULL,
    year            INT           NOT NULL,
    month           INT           NOT NULL,
    month_open      NUMERIC(14,4),
    month_close     NUMERIC(14,4),
    monthly_return  NUMERIC(10,6),
    monthly_volume  BIGINT,
    avg_close       NUMERIC(14,4),
    avg_vol_20d     NUMERIC(10,6),
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   DEFAULT NOW(),
    UNIQUE (ticker, year, month)
);

CREATE INDEX IF NOT EXISTS idx_monthly_ticker ON monthly_returns(ticker);
CREATE INDEX IF NOT EXISTS idx_monthly_year   ON monthly_returns(year, month);

-- ── Full-period asset statistics ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS asset_stats (
    ticker                  VARCHAR(10)  NOT NULL PRIMARY KEY,
    company                 VARCHAR(100),
    sector                  VARCHAR(50),
    data_start              DATE,
    data_end                DATE,
    n_trading_days          INT,
    total_return            NUMERIC(10,6),
    annualised_return       NUMERIC(10,6),
    annualised_volatility   NUMERIC(10,6),
    sharpe_ratio            NUMERIC(10,4),
    max_drawdown            NUMERIC(10,6),
    avg_daily_volume        BIGINT,
    updated_at              TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Portfolio snapshots ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id                      BIGSERIAL PRIMARY KEY,
    portfolio_name          VARCHAR(100)  NOT NULL,
    created_at              TIMESTAMPTZ   DEFAULT NOW(),
    tickers                 TEXT[],
    weights                 JSONB,
    total_return            NUMERIC(10,6),
    annualised_return       NUMERIC(10,6),
    annualised_volatility   NUMERIC(10,6),
    sharpe_ratio            NUMERIC(10,4),
    max_drawdown            NUMERIC(10,6),
    sector_allocation       JSONB,
    risk_contribution       JSONB
);

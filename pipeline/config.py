"""
MarketLens — Configuration & Constants

Defines the universe of tracked assets, sectors, and project-wide settings.
All financial data is sourced from Yahoo Finance via yfinance.
"""

# ---------------------------------------------------------------------------
# Asset Universe — 18 major publicly traded companies across 6 sectors
# ---------------------------------------------------------------------------
ASSET_UNIVERSE = {
    # Technology
    "AAPL": {"name": "Apple Inc.",                  "sector": "Technology"},
    "MSFT": {"name": "Microsoft Corporation",        "sector": "Technology"},
    "GOOGL": {"name": "Alphabet Inc.",               "sector": "Technology"},
    "NVDA": {"name": "NVIDIA Corporation",           "sector": "Technology"},
    "META":  {"name": "Meta Platforms Inc.",          "sector": "Technology"},

    # Financial Services
    "JPM":  {"name": "JPMorgan Chase & Co.",         "sector": "Financial Services"},
    "GS":   {"name": "Goldman Sachs Group Inc.",     "sector": "Financial Services"},
    "BAC":  {"name": "Bank of America Corp.",        "sector": "Financial Services"},
    "BLK":  {"name": "BlackRock Inc.",               "sector": "Financial Services"},

    # Healthcare
    "JNJ":  {"name": "Johnson & Johnson",            "sector": "Healthcare"},
    "UNH":  {"name": "UnitedHealth Group Inc.",      "sector": "Healthcare"},
    "PFE":  {"name": "Pfizer Inc.",                  "sector": "Healthcare"},

    # Energy
    "XOM":  {"name": "Exxon Mobil Corporation",      "sector": "Energy"},
    "CVX":  {"name": "Chevron Corporation",          "sector": "Energy"},

    # Consumer Discretionary / Staples
    "AMZN": {"name": "Amazon.com Inc.",              "sector": "Consumer Discretionary"},
    "TSLA": {"name": "Tesla Inc.",                   "sector": "Consumer Discretionary"},
    "PG":   {"name": "Procter & Gamble Co.",         "sector": "Consumer Staples"},

    # Industrials
    "CAT":  {"name": "Caterpillar Inc.",             "sector": "Industrials"},
}

TICKERS = list(ASSET_UNIVERSE.keys())

# ---------------------------------------------------------------------------
# Data settings
# ---------------------------------------------------------------------------
DATA_START_DATE = "2019-01-01"     # ~5 years of history
DATA_END_DATE   = None             # None = today

RAW_DATA_PATH       = "data/raw/market_data_raw.csv"
PROCESSED_DATA_PATH = "data/processed/market_data_enriched.csv"

# Trading days per year (used for annualisation)
TRADING_DAYS_PER_YEAR = 252

# Risk-free rate used for Sharpe ratio (approximate US T-bill rate)
RISK_FREE_RATE_ANNUAL = 0.05   # 5 % p.a.
RISK_FREE_RATE_DAILY  = RISK_FREE_RATE_ANNUAL / TRADING_DAYS_PER_YEAR

# ---------------------------------------------------------------------------
# Database table names
# ---------------------------------------------------------------------------
TABLE_MARKET_DATA    = "market_data"
TABLE_DAILY_METRICS  = "daily_metrics"
TABLE_MONTHLY_RETURNS = "monthly_returns"
TABLE_PORTFOLIO      = "portfolio_positions"
TABLE_PORTFOLIO_PERF = "portfolio_performance"

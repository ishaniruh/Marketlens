# MarketLens 📊
### Financial Market Intelligence & Portfolio Analytics Platform

> A portfolio-ready, end-to-end financial analytics project demonstrating data engineering, SQL analytics, portfolio risk modelling, machine learning, and business intelligence — built for the **LSEG Business Graduate Associate – Data & Analytics** role.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Business Problem](#business-problem)
3. [Objectives](#objectives)
4. [Dataset & Source](#dataset--source)
5. [Financial Concepts](#financial-concepts)
6. [Architecture](#architecture)
7. [Data Pipeline](#data-pipeline)
8. [SQL Analytics](#sql-analytics)
9. [Portfolio Analytics](#portfolio-analytics)
10. [Forecasting](#forecasting)
11. [Machine Learning — Market Regime](#machine-learning--market-regime)
12. [Power BI Dashboard](#power-bi-dashboard)
13. [Web Application](#web-application)
14. [AI Business Insights](#ai-business-insights)
15. [API Documentation](#api-documentation)
16. [Installation & Setup](#installation--setup)
17. [Running with Docker](#running-with-docker)
18. [Testing](#testing)
19. [Limitations](#limitations)
20. [Future Improvements](#future-improvements)
21. [Technologies Used](#technologies-used)
22. [Resume Bullets](#resume-bullets)

---

## Project Overview

**MarketLens** is a realistic, end-to-end financial analytics platform that processes historical market data from 18 major publicly traded companies across 6 sectors and converts raw OHLCV data into meaningful financial and business intelligence.

The project demonstrates a complete data-to-insight pipeline:
- **Ingest** → Yahoo Finance via `yfinance`
- **Store** → PostgreSQL with proper schema design
- **Analyse** → SQL analytics + Python financial calculations
- **Visualise** → Web dashboard (FastAPI + HTML/CSS/JS) + Power BI
- **Model** → ETS forecasting + Random Forest regime classification
- **Interpret** → AI-generated commentary via Gemini API

---

## Business Problem

Investors and business analysts need to analyse large volumes of financial market data to:
- Understand asset and sector performance across multiple time horizons
- Construct and evaluate portfolios with quantified risk metrics
- Identify market regime shifts to calibrate investment strategies
- Generate data-driven business insights from complex financial signals

MarketLens provides a centralised analytics platform addressing all four needs.

---

## Objectives

| Objective | Demonstrated By |
|-----------|----------------|
| Financial market understanding | 18-asset universe, sector analysis, OHLCV processing |
| Data engineering | Modular Python pipeline with validation & idempotent upserts |
| SQL analytics | 11 business analytics queries using CTEs, window functions, CASE |
| Portfolio risk | Covariance-based volatility, Sharpe, drawdown, risk contribution |
| Forecasting | Holt-Winters ETS with confidence intervals |
| Machine learning | Random Forest regime classifier with time-series CV |
| Business intelligence | Power BI dashboard + web platform |
| AI integration | Gemini API for analytical commentary |

---

## Dataset & Source

- **Source:** Yahoo Finance via [`yfinance`](https://pypi.org/project/yfinance/) (free, publicly available)
- **Adjusted Close prices** used for all return calculations (accounts for dividends/splits)
- **Data period:** January 2019 – present (~5+ years)
- **Universe:** 18 assets across 6 sectors

| Sector | Tickers |
|--------|---------|
| Technology | AAPL, MSFT, GOOGL, NVDA, META |
| Financial Services | JPM, GS, BAC, BLK |
| Healthcare | JNJ, UNH, PFE |
| Energy | XOM, CVX |
| Consumer Discretionary | AMZN, TSLA |
| Consumer Staples | PG |
| Industrials | CAT |

---

## Financial Concepts

| Concept | Implementation |
|---------|---------------|
| **Daily Return** | `(P_t / P_{t-1}) - 1` using Adjusted Close |
| **Annualised Return** | Geometric compounding: `(1+R_total)^(252/N) - 1` |
| **Annualised Volatility** | `std(daily_returns) × √252` |
| **Sharpe Ratio** | `(Ann.Return - Rf) / Ann.Vol` where Rf = 5% (US T-bill) |
| **Maximum Drawdown** | `min((P_t - max(P_0..P_t)) / max(P_0..P_t))` |
| **Moving Averages** | 20, 50, 200-day simple MAs of Adjusted Close |
| **Correlation** | Pearson correlation of daily returns (diversification analysis) |
| **Portfolio Volatility** | `√(wᵀ Σ w)` where Σ is the annualised covariance matrix |
| **Risk Contribution** | Marginal contribution: `w × (Σw) / σ_portfolio` |
| **Golden/Death Cross** | MA20 crossing above/below MA50 (momentum signal) |
| **Market Regime** | Volatility tertile classification: Low / Medium / High |

---

## Architecture

```
marketlens/
├── pipeline/           # Data pipeline (ingest → validate → transform → store)
│   ├── config.py       # Asset universe, constants
│   ├── ingest.py       # Yahoo Finance data fetching
│   ├── validate.py     # 7-point data quality checks
│   ├── transform.py    # Financial metric calculations
│   ├── portfolio.py    # Portfolio analytics engine
│   ├── database.py     # SQLAlchemy + upsert logic
│   └── run_pipeline.py # Orchestration script
├── models/             # ML & forecasting
│   ├── regime_classifier.py  # Random Forest regime model
│   └── forecaster.py   # Holt-Winters ETS forecasting
├── sql/
│   ├── init.sql        # PostgreSQL schema
│   └── analytics_queries.sql  # 11 business analytics queries
├── backend/            # FastAPI REST API
│   ├── main.py         # App entry point
│   ├── db.py           # Connection pooling
│   └── routes/         # market / portfolio / forecast / regime / insights
├── frontend/           # Web interface
│   ├── templates/index.html
│   └── static/{css,js}
├── dashboards/         # Power BI design guide + DAX measures
├── notebooks/          # Jupyter EDA walkthrough
├── tests/              # Pytest test suite
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Data Pipeline

The pipeline (`pipeline/run_pipeline.py`) runs in 5 sequential steps:

```
[1] Ingest    → yfinance batch download for all 18 tickers
[2] Validate  → 7 quality checks (duplicates, nulls, negative prices, OHLC sanity)
[3] Transform → Daily metrics, monthly aggregations, full-period stats
[4] Connect   → SQLAlchemy connection to PostgreSQL
[5] Persist   → Idempotent upserts to market_data, monthly_returns, asset_stats
```

**Run the pipeline:**
```bash
python -m pipeline.run_pipeline

# Or for a subset of tickers:
python -m pipeline.run_pipeline --tickers AAPL MSFT GOOGL JPM
```

---

## SQL Analytics

The file [`sql/analytics_queries.sql`](sql/analytics_queries.sql) contains **11 production-quality queries**:

| Query | Business Purpose | SQL Features |
|-------|-----------------|--------------|
| Q1 | Best/worst performing stocks | CTE, RANK(), CASE |
| Q2 | Monthly return calendar | CASE pivot, GROUP BY |
| Q3 | Sector trading volume ranking | Aggregate, RANK() |
| Q4 | Sector-level performance | GROUP BY, AVG |
| Q5 | Highest-volatility assets (recent) | CTE, HAVING, RANK() |
| Q6 | Year-over-year annual returns | Window functions, LAG() |
| Q7 | Max drawdown analysis | CTE, CASE classification |
| Q8 | Market regime by volatility quartile | PERCENTILE_CONT, CASE |
| Q9 | Golden/Death Cross MA signals | Window functions, LAG() |
| Q10 | Portfolio HHI concentration | JSON expansion, aggregate |
| Q11 | Rolling 52-week high/low | Window functions |

---

## Portfolio Analytics

The portfolio engine (`pipeline/portfolio.py`) accepts any set of weighted assets and computes:

```python
weights = {"AAPL": 0.30, "MSFT": 0.25, "JPM": 0.25, "JNJ": 0.20}
result = compute_portfolio_metrics(df, weights, sector_map)
```

**Outputs:**
- Annualised return & volatility
- Sharpe ratio (rf = 5%)
- Maximum drawdown (full period)
- Sector allocation breakdown
- Asset-level return contribution
- Risk contribution (marginal variance contribution)
- Portfolio equity curve

> ⚠️ **All calculations are historical. Weights must sum to 100%. Not financial advice.**

---

## Forecasting

**Method:** Holt-Winters Exponential Smoothing (additive trend, damped)  
**Library:** `statsmodels`

The model:
1. Fits to the full historical Adjusted Close price series
2. Generates a forward trend estimate for 15–90 trading days
3. Provides bootstrapped confidence intervals (widening with horizon)
4. Optimises smoothing parameters via maximum likelihood

```
⚠️ IMPORTANT: Stock prices are not reliably predictable.
This component demonstrates time-series methodology.
Confidence intervals widen significantly at longer horizons.
This is NOT an investment recommendation.
```

---

## Machine Learning — Market Regime

**Model:** Random Forest Classifier (`scikit-learn`)  
**Task:** Multi-class classification of market volatility regime

**Features:**
| Feature | Description |
|---------|-------------|
| `daily_return` | Daily price change |
| `vol_20d` | 20-day annualised volatility |
| `vol_60d` | 60-day annualised volatility |
| `ma_spread` | (MA20 - MA50) / Price |
| `volume_z` | 60-day volume z-score |
| `return_5d` | 5-day rolling mean return |
| `return_20d` | 20-day rolling mean return |

**Labels:** Derived from vol_20d tertile thresholds:
- Low Volatility (bottom 33%)
- Medium Volatility (middle 33%)
- High Volatility (top 33%)

**Validation:** 5-fold time-series cross-validation (no data leakage)

```
⚠️ This model classifies historical volatility patterns.
It does NOT predict future prices or guarantee future regimes.
```

---

## Power BI Dashboard

See [`dashboards/POWER_BI_GUIDE.md`](dashboards/POWER_BI_GUIDE.md) for full design specification.

**4 Pages:**

| Page | Content |
|------|---------|
| Market Overview | KPIs, top/worst performers, sector chart, risk-return scatter |
| Asset Analysis | Price + MA chart, returns histogram, volatility, drawdown, monthly heatmap |
| Portfolio Risk | Portfolio KPIs, sector allocation, risk/return contribution, equity curve |
| Market Trends | Sector comparison, correlation matrix, regime distribution, MA signals |

**DAX Measures included:** YTD Return, Avg Ann Return, Vol Category, MA Signal, Sector Avg Sharpe, HHI Concentration

---

## Web Application

The web interface is served by FastAPI and accessed at `http://localhost:8000`.

**5 Pages (tabs):**
1. **Market Overview** — Cross-asset performance, sector analysis, risk-return scatter
2. **Asset Analysis** — Price chart, MA overlays, returns distribution, drawdown, monthly heatmap
3. **Portfolio Builder** — Interactive weight builder, equity curve, sector allocation
4. **Forecasting** — ETS trend estimate with confidence bands
5. **Market Regime** — Regime distribution, timeline, model methodology

---

## AI Business Insights

Powered by **Google Gemini API** (optional).

The AI receives **pre-computed metrics** (not raw data) and generates:
- Key performance observations
- Risk observations  
- Business/investment commentary
- Acknowledged limitations

**The model never invents financial numbers.** It only interprets the metrics you provide.

To enable: add `GEMINI_API_KEY=your_key` to `.env`.

---

## API Documentation

Full interactive docs at: `http://localhost:8000/api/docs`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market/assets` | List all 18 assets |
| GET | `/api/market/overview` | Market overview with top/worst performers |
| GET | `/api/market/prices/{ticker}` | Historical prices + metrics |
| GET | `/api/market/sector/{sector}` | Sector performance |
| GET | `/api/market/correlation` | Return correlation matrix |
| GET | `/api/market/monthly-returns/{ticker}` | Monthly return calendar |
| POST | `/api/portfolio/analyse` | Run portfolio analytics |
| POST | `/api/portfolio/equity-curve` | Portfolio equity curve data |
| GET | `/api/forecast/{ticker}` | Price trend forecast |
| POST | `/api/regime/train` | Train regime classifier |
| GET | `/api/regime/predict` | Get regime predictions |
| POST | `/api/insights/generate` | AI business insights |
| GET | `/health` | Health check |

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Git

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/marketlens.git
cd marketlens

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
# Edit .env with your PostgreSQL credentials and optional Gemini API key
```

### 3. Set Up Database
```bash
# Create database and user in PostgreSQL
psql -U postgres -c "CREATE USER marketlens_user WITH PASSWORD 'marketlens_pass';"
psql -U postgres -c "CREATE DATABASE marketlens OWNER marketlens_user;"
```

### 4. Run Data Pipeline
```bash
python -m pipeline.run_pipeline
# This fetches ~5 years of data for 18 assets (~40,000 rows)
# Takes approximately 2-4 minutes depending on connection speed
```

### 5. Train ML Model
```bash
# Start the backend first (step 6), then:
curl -X POST http://localhost:8000/api/regime/train
```

### 6. Start the Backend
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Open the App
Navigate to `http://localhost:8000`

---

## Running with Docker

```bash
# Copy environment file
copy .env.example .env

# Start all services
docker-compose up --build

# Run pipeline inside container
docker exec marketlens_backend python -m pipeline.run_pipeline

# Access at http://localhost:8000
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_validate.py -v
pytest tests/test_transform.py -v
pytest tests/test_portfolio.py -v
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=pipeline --cov=models --cov=backend -v
```

**Test coverage includes:**
- Data validation (7 scenarios)
- Financial metric accuracy (12 assertions)
- Portfolio weight validation (9 cases)
- Risk metric correctness (8 assertions)
- API endpoint responses (10 tests)

---

## Limitations

1. **Historical data only** — All metrics are derived from past prices. Past performance does not indicate future results.
2. **Yahoo Finance dependency** — Data availability and accuracy depends on yfinance/Yahoo Finance. Some historical data may be incomplete.
3. **ETS forecasting** — Exponential Smoothing assumes trend continuity. It does not account for structural breaks, earnings, or macroeconomic shocks.
4. **Regime classifier** — Labels are derived from historical volatility distribution. The model may not generalise to market conditions outside the training period.
5. **Risk-free rate** — Fixed at 5% (approximate US T-bill rate). This affects Sharpe ratio comparisons across different rate environments.
6. **Portfolio optimisation** — The platform analyses user-defined weights. It does not perform mean-variance optimisation or factor-based allocation.
7. **Single-currency** — All analysis is in USD. No FX adjustments for international assets.

---

## Future Improvements

1. **Factor analysis** — Fama-French 3/5 factor decomposition to explain return drivers
2. **Portfolio optimisation** — Mean-variance efficient frontier using `scipy.optimize`
3. **Options data** — Implied volatility from options chain (VIX-style analysis)
4. **Alternative data** — Sentiment analysis from news/social media
5. **Real-time streaming** — WebSocket price feeds for live dashboards
6. **Multi-currency support** — FX-adjusted returns for global portfolios
7. **Benchmark comparison** — S&P 500 / sector ETF benchmark tracking
8. **Risk stress testing** — Scenario analysis (2008 crisis, COVID crash)
9. **ESG scores** — Environmental, Social, Governance data integration
10. **Alert system** — Email/webhook notifications for regime changes or drawdown thresholds

---

## Technologies Used

| Category | Technology |
|----------|-----------|
| **Data Source** | Yahoo Finance (`yfinance 0.2.36`) |
| **Data Processing** | Python 3.11, pandas 2.1, NumPy 1.26 |
| **Database** | PostgreSQL 15, SQLAlchemy 2.0 |
| **Backend API** | FastAPI 0.109, Uvicorn |
| **Forecasting** | statsmodels 0.14 (Holt-Winters ETS) |
| **Machine Learning** | scikit-learn 1.4 (Random Forest) |
| **Frontend** | HTML5, Vanilla CSS, JavaScript, Chart.js 4.4 |
| **Visualisation** | matplotlib, seaborn, plotly, Chart.js |
| **Business Intelligence** | Power BI Desktop (DAX) |
| **AI** | Google Gemini 1.5 Flash |
| **Testing** | pytest, pytest-asyncio |
| **Containerisation** | Docker, Docker Compose |
| **Development** | Jupyter, python-dotenv, loguru |

---

## Resume Bullets

> Written in **Problem → Analytics → Business Impact** format for the LSEG Business Graduate Associate – Data & Analytics role:

**1. Data Engineering & SQL**
> Engineered an end-to-end financial data pipeline in Python ingesting 5+ years of OHLCV data for 18 major assets from Yahoo Finance, applying 7-point validation checks, and persisting via idempotent PostgreSQL upserts; authored 11 business-analytics SQL queries leveraging CTEs, window functions, and CASE expressions to surface sector performance, drawdown risk, and MA-based momentum signals.

**2. Portfolio Analytics & Risk Modelling**
> Built a covariance-based portfolio analytics engine computing annualised return, volatility, Sharpe ratio, maximum drawdown, sector allocation, and marginal risk contribution for user-defined weighted portfolios; validated all financial calculations against standard industry formulae and surfaced results through an interactive FastAPI web dashboard with real-time portfolio equity curves.

**3. Machine Learning & Business Intelligence**
> Deployed a Random Forest market-regime classifier using 7 engineered financial features (rolling volatility, return momentum, volume z-score, MA spread) with time-series cross-validation to prevent data leakage; integrated Holt-Winters ETS forecasting with uncertainty quantification and a Gemini AI commentary layer that interprets pre-computed metrics into actionable business observations for non-technical stakeholders.

---

> **Disclaimer:** MarketLens is an analytical portfolio project built for educational and career-development purposes. All metrics are derived from publicly available historical market data. Nothing in this project constitutes financial advice or investment recommendations.

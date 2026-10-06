# MarketLens — Power BI Dashboard Design Guide

## Overview

This document describes the Power BI dashboard design for MarketLens.
Export data from PostgreSQL using the provided queries and import into Power BI Desktop.

---

## Data Connection

**Connection Type:** PostgreSQL  
**Server:** localhost:5432 (or your Docker host)  
**Database:** marketlens  

**Tables to import:**
- `market_data` — Daily OHLCV + metrics
- `monthly_returns` — Monthly aggregations
- `asset_stats` — Full-period statistics per ticker
- `portfolio_snapshots` — Saved portfolio analyses

---

## DAX Measures

Paste these into the Power BI DAX editor:

```dax
-- Annualised Return (weighted average)
Avg Ann Return =
AVERAGEX(asset_stats, asset_stats[annualised_return]) * 100

-- Portfolio Sharpe (filtered to selected portfolio)
Portfolio Sharpe =
SELECTEDVALUE(portfolio_snapshots[sharpe_ratio])

-- Volatility Colour Flag (for conditional formatting)
Vol Category =
VAR vol = [Avg Ann Vol]
RETURN
    SWITCH(
        TRUE(),
        vol < 15, "Low",
        vol < 30, "Medium",
        "High"
    )

-- YTD Return
YTD Return =
VAR current_year = YEAR(TODAY())
VAR jan_price =
    CALCULATE(
        FIRSTNONBLANK(market_data[adj_close], 1),
        market_data[date] >= DATE(current_year, 1, 1),
        market_data[date] < DATE(current_year, 2, 1)
    )
VAR latest_price = LASTNONBLANK(market_data[adj_close], 1)
RETURN DIVIDE(latest_price - jan_price, jan_price) * 100

-- Sector Avg Sharpe
Sector Avg Sharpe =
AVERAGEX(
    FILTER(asset_stats, asset_stats[sector] = SELECTEDVALUE(asset_stats[sector])),
    asset_stats[sharpe_ratio]
)

-- Max Drawdown (most severe)
Worst Drawdown =
MINX(asset_stats, asset_stats[max_drawdown]) * 100

-- 52-Week High
52W High =
CALCULATE(
    MAX(market_data[adj_close]),
    DATESINPERIOD(market_data[date], LASTDATE(market_data[date]), -365, DAY)
)

-- Moving Average Spread Signal
MA Signal =
VAR ma20 = LASTNONBLANK(market_data[ma_20], 1)
VAR ma50 = LASTNONBLANK(market_data[ma_50], 1)
RETURN
    IF(ma20 > ma50, "Bullish (MA20 > MA50)", "Bearish (MA20 < MA50)")
```

---

## Page 1 — Market Overview

**Theme:** Dark background (#090e1a), accent blue (#3b82f6)

### Visuals:
1. **KPI Cards (top row):**
   - Total Assets Tracked (Card)
   - Avg Annualised Return % (Card with conditional colour)
   - Avg Volatility % (Card)
   - Avg Sharpe Ratio (Card)

2. **Clustered Bar Chart — Sector Performance**
   - X-axis: Sector  
   - Y-axis: Avg Ann Return %
   - Colour by sector

3. **Scatter Chart — Risk vs Return**
   - X: annualised_volatility  
   - Y: annualised_return  
   - Size: avg_daily_volume  
   - Colour: sector  
   - Data labels: ticker  

4. **Table — All Assets**
   - Columns: Ticker, Company, Sector, Ann. Return, Volatility, Sharpe, Max Drawdown
   - Conditional formatting: Green/Red on return column

5. **Slicer — Sector Filter**

---

## Page 2 — Asset Analysis

**Slicer:** Ticker (single select)

### Visuals:
1. **Line Chart — Price & Moving Averages**
   - X: date  
   - Lines: adj_close, ma_20, ma_50, ma_200  
   - Secondary Y for volume (Bar)

2. **Area Chart — Cumulative Return**
   - X: date  
   - Y: cumulative_return  

3. **Line Chart — Rolling Volatility**
   - X: date  
   - Y: vol_20d  
   - Reference line at 0.25 (25% vol threshold)

4. **Area Chart — Drawdown**
   - X: date  
   - Y: drawdown  
   - Fill colour: red with 30% opacity

5. **Matrix Heatmap — Monthly Returns**
   - Rows: year  
   - Columns: month  
   - Values: monthly_return  
   - Conditional formatting: Green positive, Red negative

---

## Page 3 — Portfolio Risk

**Note:** Requires a saved portfolio in `portfolio_snapshots` table.

### Visuals:
1. **KPI Cards:**
   - Portfolio Ann. Return  
   - Portfolio Volatility  
   - Sharpe Ratio  
   - Max Drawdown  

2. **Donut Chart — Sector Allocation**
   - From: portfolio_snapshots.sector_allocation (JSON → expand)

3. **Bar Chart — Risk Contribution by Asset**

4. **Bar Chart — Return Contribution by Asset**

5. **Line Chart — Equity Curve**
   - Requires equity curve data exported separately

6. **Text Box — Disclaimer**
   - "All metrics are historical. Not financial advice."

---

## Page 4 — Market Trends

### Visuals:
1. **Small Multiples Line Charts — Price Trends by Sector**
   - One sparkline per ticker, grouped by sector

2. **Matrix Heatmap — Correlation**
   - Rows & Columns: ticker  
   - Values: daily_return correlation (pre-compute in Python, export as CSV)

3. **Stacked Bar — Regime Distribution**
   - X: month  
   - Y: count of Low / Medium / High vol days  
   - Legend: regime label  

4. **Line Chart — Cross-sector Volatility Comparison**
   - X: date  
   - Lines: avg vol_20d per sector  

5. **Table — MA Signals**
   - Ticker, current MA signal (Golden Cross / Death Cross)

---

## Colour Scheme

| Element         | Colour   | Hex      |
|-----------------|----------|----------|
| Background      | Deep navy | #090e1a |
| Card surface    | Dark card | #101828  |
| Positive return | Green     | #22c55e  |
| Negative return | Red       | #ef4444  |
| Primary accent  | Blue      | #3b82f6  |
| Secondary       | Teal      | #14b8a6  |
| Warning         | Amber     | #f59e0b  |
| AI / Special    | Purple    | #a855f7  |

---

## Export Queries for Power BI

Run these queries in PostgreSQL to create flat tables for Power BI import:

```sql
-- Flat market data for Power BI
SELECT
    md.date,
    md.ticker,
    md.company,
    md.sector,
    md.adj_close,
    md.volume / 1e6      AS volume_m,
    md.daily_return * 100 AS daily_return_pct,
    md.ma_20,
    md.ma_50,
    md.ma_200,
    md.vol_20d * 100     AS vol_20d_pct,
    md.cumulative_return * 100 AS cum_return_pct,
    md.drawdown * 100    AS drawdown_pct,
    md.sharpe_252d       AS sharpe_rolling,
    ast.annualised_return * 100   AS ann_return_pct,
    ast.annualised_volatility * 100 AS ann_vol_pct,
    ast.sharpe_ratio,
    ast.max_drawdown * 100 AS max_drawdown_pct
FROM market_data md
LEFT JOIN asset_stats ast USING (ticker)
ORDER BY md.date, md.ticker;
```

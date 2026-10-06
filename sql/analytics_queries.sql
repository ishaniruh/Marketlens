-- ============================================================
--  MarketLens — Business Analytics Queries
--
--  A library of reusable SQL queries demonstrating SQL proficiency
--  for meaningful financial analysis.  Each query is labelled with
--  its business purpose.
-- ============================================================


-- ────────────────────────────────────────────────────────────────────────────
-- Q1. TOP 10 BEST & WORST PERFORMING STOCKS (Total Return, full period)
-- ────────────────────────────────────────────────────────────────────────────
WITH ranked AS (
    SELECT
        ticker,
        company,
        sector,
        annualised_return,
        annualised_volatility,
        sharpe_ratio,
        max_drawdown,
        RANK() OVER (ORDER BY annualised_return DESC) AS return_rank,
        RANK() OVER (ORDER BY annualised_return ASC)  AS worst_rank
    FROM asset_stats
)
SELECT
    ticker,
    company,
    sector,
    ROUND(annualised_return * 100, 2)     AS ann_return_pct,
    ROUND(annualised_volatility * 100, 2) AS ann_vol_pct,
    ROUND(sharpe_ratio, 2)                AS sharpe,
    ROUND(max_drawdown * 100, 2)          AS max_drawdown_pct,
    CASE
        WHEN return_rank <= 5 THEN 'Top Performer'
        WHEN worst_rank  <= 5 THEN 'Worst Performer'
        ELSE 'Mid Range'
    END AS performance_label
FROM ranked
ORDER BY annualised_return DESC;


-- ────────────────────────────────────────────────────────────────────────────
-- Q2. MONTHLY RETURN CALENDAR — Year-over-year monthly comparison for a ticker
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    ticker,
    year,
    MAX(CASE WHEN month = 1  THEN ROUND(monthly_return * 100, 2) END) AS jan,
    MAX(CASE WHEN month = 2  THEN ROUND(monthly_return * 100, 2) END) AS feb,
    MAX(CASE WHEN month = 3  THEN ROUND(monthly_return * 100, 2) END) AS mar,
    MAX(CASE WHEN month = 4  THEN ROUND(monthly_return * 100, 2) END) AS apr,
    MAX(CASE WHEN month = 5  THEN ROUND(monthly_return * 100, 2) END) AS may,
    MAX(CASE WHEN month = 6  THEN ROUND(monthly_return * 100, 2) END) AS jun,
    MAX(CASE WHEN month = 7  THEN ROUND(monthly_return * 100, 2) END) AS jul,
    MAX(CASE WHEN month = 8  THEN ROUND(monthly_return * 100, 2) END) AS aug,
    MAX(CASE WHEN month = 9  THEN ROUND(monthly_return * 100, 2) END) AS sep,
    MAX(CASE WHEN month = 10 THEN ROUND(monthly_return * 100, 2) END) AS oct,
    MAX(CASE WHEN month = 11 THEN ROUND(monthly_return * 100, 2) END) AS nov,
    MAX(CASE WHEN month = 12 THEN ROUND(monthly_return * 100, 2) END) AS dec
FROM monthly_returns
GROUP BY ticker, year
ORDER BY ticker, year;


-- ────────────────────────────────────────────────────────────────────────────
-- Q3. AVERAGE DAILY TRADING VOLUME BY SECTOR (with rank)
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    sector,
    COUNT(DISTINCT ticker)                   AS num_assets,
    ROUND(AVG(volume) / 1e6, 2)             AS avg_daily_volume_m,
    ROUND(SUM(volume) / 1e9, 2)             AS total_volume_b,
    RANK() OVER (ORDER BY AVG(volume) DESC)  AS volume_rank
FROM market_data
GROUP BY sector
ORDER BY avg_daily_volume_m DESC;


-- ────────────────────────────────────────────────────────────────────────────
-- Q4. SECTOR-LEVEL PERFORMANCE SUMMARY
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    sector,
    COUNT(DISTINCT ticker)                         AS num_stocks,
    ROUND(AVG(annualised_return)   * 100, 2)       AS avg_ann_return_pct,
    ROUND(AVG(annualised_volatility) * 100, 2)     AS avg_ann_vol_pct,
    ROUND(AVG(sharpe_ratio), 2)                    AS avg_sharpe,
    ROUND(MIN(max_drawdown)        * 100, 2)       AS worst_drawdown_pct,
    ROUND(MAX(annualised_return)   * 100, 2)       AS best_stock_return_pct
FROM asset_stats
GROUP BY sector
ORDER BY avg_ann_return_pct DESC;


-- ────────────────────────────────────────────────────────────────────────────
-- Q5. HIGHEST-VOLATILITY ASSETS — 30-day rolling vol, last 90 days
-- ────────────────────────────────────────────────────────────────────────────
WITH recent AS (
    SELECT
        ticker,
        company,
        sector,
        date,
        vol_20d,
        RANK() OVER (PARTITION BY ticker ORDER BY date DESC) AS day_rank
    FROM market_data
    WHERE date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT
    ticker,
    company,
    sector,
    ROUND(AVG(vol_20d) * 100, 2) AS avg_recent_vol_pct,
    ROUND(MAX(vol_20d) * 100, 2) AS peak_vol_pct
FROM recent
GROUP BY ticker, company, sector
HAVING AVG(vol_20d) IS NOT NULL
ORDER BY avg_recent_vol_pct DESC
LIMIT 10;


-- ────────────────────────────────────────────────────────────────────────────
-- Q6. YEAR-OVER-YEAR ANNUAL RETURNS (using window functions)
-- ────────────────────────────────────────────────────────────────────────────
WITH yearly AS (
    SELECT
        ticker,
        company,
        sector,
        EXTRACT(YEAR FROM date)::INT AS year,
        FIRST_VALUE(adj_close) OVER (PARTITION BY ticker, EXTRACT(YEAR FROM date) ORDER BY date)       AS year_open,
        LAST_VALUE(adj_close)  OVER (PARTITION BY ticker, EXTRACT(YEAR FROM date) ORDER BY date
                                     ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)         AS year_close
    FROM market_data
),
distinct_years AS (
    SELECT DISTINCT ticker, company, sector, year, year_open, year_close FROM yearly
)
SELECT
    ticker,
    company,
    sector,
    year,
    ROUND(year_open,  2)                              AS open_price,
    ROUND(year_close, 2)                              AS close_price,
    ROUND(((year_close - year_open) / year_open) * 100, 2) AS annual_return_pct,
    LAG(ROUND(((year_close - year_open) / year_open) * 100, 2))
        OVER (PARTITION BY ticker ORDER BY year)      AS prev_year_return_pct
FROM distinct_years
ORDER BY ticker, year;


-- ────────────────────────────────────────────────────────────────────────────
-- Q7. MAXIMUM DRAWDOWN ANALYSIS — Identify the worst peak-to-trough periods
-- ────────────────────────────────────────────────────────────────────────────
WITH drawdown_stats AS (
    SELECT
        ticker,
        company,
        sector,
        MIN(drawdown)            AS max_drawdown,
        DATE(MIN(date))          AS approx_trough_date,
        AVG(drawdown)            AS avg_drawdown
    FROM market_data
    WHERE drawdown IS NOT NULL
    GROUP BY ticker, company, sector
)
SELECT
    ticker,
    company,
    sector,
    ROUND(max_drawdown * 100, 2)  AS max_drawdown_pct,
    approx_trough_date,
    ROUND(avg_drawdown * 100, 2)  AS avg_drawdown_pct,
    CASE
        WHEN max_drawdown < -0.50  THEN 'Severe (>50%)'
        WHEN max_drawdown < -0.30  THEN 'High (30-50%)'
        WHEN max_drawdown < -0.15  THEN 'Moderate (15-30%)'
        ELSE 'Low (<15%)'
    END AS risk_category
FROM drawdown_stats
ORDER BY max_drawdown ASC;


-- ────────────────────────────────────────────────────────────────────────────
-- Q8. MARKET REGIME DETECTION — Days classified by volatility regime
--     (uses the 20-day rolling vol vs historical quartiles)
-- ────────────────────────────────────────────────────────────────────────────
WITH vol_quartiles AS (
    SELECT
        PERCENTILE_CONT(0.33) WITHIN GROUP (ORDER BY vol_20d) AS q33,
        PERCENTILE_CONT(0.67) WITHIN GROUP (ORDER BY vol_20d) AS q67
    FROM market_data
    WHERE vol_20d IS NOT NULL
)
SELECT
    md.date,
    md.ticker,
    md.sector,
    ROUND(md.vol_20d * 100, 2) AS vol_pct,
    CASE
        WHEN md.vol_20d < vq.q33  THEN 'Low Volatility'
        WHEN md.vol_20d < vq.q67  THEN 'Medium Volatility'
        ELSE                           'High Volatility'
    END AS market_regime,
    ROUND(md.daily_return * 100, 2) AS daily_return_pct
FROM market_data md, vol_quartiles vq
WHERE md.vol_20d IS NOT NULL
ORDER BY md.date DESC, md.ticker;


-- ────────────────────────────────────────────────────────────────────────────
-- Q9. MOVING AVERAGE SIGNAL — Golden/Death Cross detection
--     (MA20 crossing MA50 — common momentum signal)
-- ────────────────────────────────────────────────────────────────────────────
WITH ma_signals AS (
    SELECT
        date,
        ticker,
        company,
        adj_close,
        ma_20,
        ma_50,
        LAG(ma_20) OVER (PARTITION BY ticker ORDER BY date) AS prev_ma_20,
        LAG(ma_50) OVER (PARTITION BY ticker ORDER BY date) AS prev_ma_50
    FROM market_data
    WHERE ma_20 IS NOT NULL AND ma_50 IS NOT NULL
)
SELECT
    date,
    ticker,
    company,
    ROUND(adj_close, 2) AS price,
    ROUND(ma_20, 2)     AS ma_20,
    ROUND(ma_50, 2)     AS ma_50,
    CASE
        WHEN ma_20 > ma_50 AND prev_ma_20 <= prev_ma_50 THEN 'Golden Cross (Bullish)'
        WHEN ma_20 < ma_50 AND prev_ma_20 >= prev_ma_50 THEN 'Death Cross (Bearish)'
        WHEN ma_20 > ma_50 THEN 'Above MA50 (Bullish trend)'
        ELSE                    'Below MA50 (Bearish trend)'
    END AS ma_signal
FROM ma_signals
WHERE date >= CURRENT_DATE - INTERVAL '180 days'
ORDER BY date DESC, ticker;


-- ────────────────────────────────────────────────────────────────────────────
-- Q10. PORTFOLIO RISK CONCENTRATION — Herfindahl-Hirschman Index (HHI)
--      Measures whether portfolio is concentrated in a few sectors
--      HHI > 0.25 = highly concentrated; < 0.15 = diversified
-- ────────────────────────────────────────────────────────────────────────────
WITH sector_weights AS (
    SELECT
        ps.id AS portfolio_id,
        ps.portfolio_name,
        jsonb_each_text(ps.sector_allocation) AS sa
    FROM portfolio_snapshots ps
),
expanded AS (
    SELECT
        portfolio_id,
        portfolio_name,
        (sa).key   AS sector,
        ((sa).value)::NUMERIC AS weight
    FROM sector_weights
)
SELECT
    portfolio_id,
    portfolio_name,
    ROUND(SUM(weight * weight), 4)          AS hhi_concentration,
    COUNT(sector)                            AS num_sectors,
    CASE
        WHEN SUM(weight * weight) > 0.25 THEN 'Highly Concentrated'
        WHEN SUM(weight * weight) > 0.15 THEN 'Moderately Concentrated'
        ELSE                                  'Well Diversified'
    END AS diversification_label
FROM expanded
GROUP BY portfolio_id, portfolio_name
ORDER BY hhi_concentration DESC;


-- ────────────────────────────────────────────────────────────────────────────
-- Q11. ROLLING 52-WEEK HIGH/LOW — Price positioning indicator
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    date,
    ticker,
    company,
    sector,
    ROUND(adj_close, 2) AS current_price,
    MAX(adj_close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) AS high_52w,
    MIN(adj_close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) AS low_52w,
    ROUND(
        (adj_close - MIN(adj_close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW))
        / NULLIF(MAX(adj_close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW)
                 - MIN(adj_close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW), 0)
        * 100, 1
    ) AS pct_of_52w_range
FROM market_data
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY ticker, date DESC;

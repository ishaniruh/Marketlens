"""
MarketLens — Interactive Financial Analytics & Portfolio Intelligence Dashboard

Built with Streamlit and Plotly.
Run with:
    python -m streamlit run dashboard.py
    OR
    python -m streamlit run frontend/app.py
"""

import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.config import ASSET_UNIVERSE, PROCESSED_DATA_PATH
from pipeline.portfolio import compute_portfolio_metrics
from models.forecaster import forecast_price_trend
from models.regime_classifier import predict_regimes, train_regime_classifier

# -----------------------------------------------------------------------------
# Page Config & Theme
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="MarketLens — Financial Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Dark Mode Styling
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    .stMetric {
        background-color: #1E222D;
        border: 1px solid #2A2E39;
        padding: 15px;
        border-radius: 8px;
    }
    .stMetric label { color: #8A92A6 !important; font-size: 13px !important; }
    .stMetric div[data-testid="stMetricValue"] { color: #F0F2F6 !important; font-weight: 600; }
    h1, h2, h3 { color: #F0F2F6; font-family: 'Inter', sans-serif; }
    .stSelectbox, .stSlider, .stMultiSelect { color: #F0F2F6; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    if not os.path.exists(PROCESSED_DATA_PATH):
        from run_pipeline import main as run_pipeline_main
        run_pipeline_main()
    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


df = load_data()
all_tickers = sorted(df["ticker"].unique().tolist())
sector_map = {t: info["sector"] for t, info in ASSET_UNIVERSE.items() if t in all_tickers}

# -----------------------------------------------------------------------------
# Sidebar Navigation (Clean strings without emoji comparison bugs)
# -----------------------------------------------------------------------------
st.sidebar.title("MarketLens Platform")
st.sidebar.markdown("**LSEG Business Analytics Suite**")
st.sidebar.markdown("---")

M_OVERVIEW  = "1. Market Overview & Returns"
M_PORTFOLIO = "2. Portfolio Analytics & Risk"
M_REGIME    = "3. ML Market Regime & Forecasting"
M_DEEPDIVE  = "4. Single Asset Deep Dive"

page = st.sidebar.radio(
    "Navigate Analytics Module:",
    [M_OVERVIEW, M_PORTFOLIO, M_REGIME, M_DEEPDIVE],
    index=0
)

# -----------------------------------------------------------------------------
# Module 1: Market Overview & Returns
# -----------------------------------------------------------------------------
if page == M_OVERVIEW:
    st.title("📈 Multi-Asset Market Intelligence")
    st.caption("Historical performance, return dynamics, and risk parameters across tracked universe.")

    # Metric Cards Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tracked Assets", f"{len(all_tickers)} Stocks", delta="6 Sectors")
    with col2:
        top_perf = df.groupby("ticker")["cumulative_return"].last().idxmax()
        top_ret = df.groupby("ticker")["cumulative_return"].last().max() * 100
        st.metric("Top Outperformer", top_perf, delta=f"+{top_ret:.1f}% Total")
    with col3:
        avg_vol = df.groupby("ticker")["vol_20d"].last().mean() * 100
        st.metric("Avg 20D Volatility", f"{avg_vol:.2f}% p.a.")
    with col4:
        st.metric("Data History", f"{df['date'].min().strftime('%Y')} – {df['date'].max().strftime('%Y')}", "Daily Resolution")

    st.markdown("---")

    # Multi-Asset Price Select (Default to first 5 tickers, support all tickers)
    default_selected = [t for t in ["AAPL", "MSFT", "NVDA", "JPM", "XOM"] if t in all_tickers]
    selected_tickers = st.multiselect(
        "Select tickers to compare performance:",
        options=all_tickers,
        default=default_selected if default_selected else all_tickers[:5],
    )

    if selected_tickers:
        filtered_df = df[df["ticker"].isin(selected_tickers)]

        if not filtered_df.empty:
            tab1, tab2, tab3 = st.tabs(["Normalized Cumulative Return", "Adjusted Close Prices", "20D Rolling Volatility"])

            with tab1:
                fig_cum = px.line(
                    filtered_df,
                    x="date",
                    y="cumulative_return",
                    color="ticker",
                    title="Normalized Cumulative Growth (1.0 = Baseline)",
                    template="plotly_dark",
                )
                fig_cum.update_layout(yaxis_title="Growth Multiple", hovermode="x unified")
                st.plotly_chart(fig_cum, width="stretch")

            with tab2:
                fig_close = px.line(
                    filtered_df,
                    x="date",
                    y="adj_close",
                    color="ticker",
                    title="Historical Adjusted Close Prices (USD)",
                    template="plotly_dark",
                )
                fig_close.update_layout(yaxis_title="Price ($)", hovermode="x unified")
                st.plotly_chart(fig_close, width="stretch")

            with tab3:
                fig_vol = px.line(
                    filtered_df,
                    x="date",
                    y="vol_20d",
                    color="ticker",
                    title="20-Day Rolling Annualised Volatility",
                    template="plotly_dark",
                )
                fig_vol.update_layout(yaxis_title="Volatility (Dec.)", hovermode="x unified")
                st.plotly_chart(fig_vol, width="stretch")
        else:
            st.warning("No data found for the selected tickers.")
    else:
        st.info("💡 Please select at least one ticker from the dropdown above to display comparison charts.")

# -----------------------------------------------------------------------------
# Module 2: Portfolio Analytics & Risk
# -----------------------------------------------------------------------------
elif page == M_PORTFOLIO:
    st.title("💼 Portfolio Risk & Asset Allocation")
    st.caption("Construct multi-asset portfolios, analyze Sharpe ratios, sector concentrations, and risk contributions.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Portfolio Weight Allocator")
    
    # Allow user to pick which assets to include in portfolio
    portfolio_universe = st.sidebar.multiselect(
        "Select Portfolio Assets:",
        options=all_tickers,
        default=[t for t in ["AAPL", "MSFT", "NVDA", "JPM", "XOM"] if t in all_tickers],
    )

    if portfolio_universe:
        equal_weight = round(1.0 / len(portfolio_universe), 4)
        weights = {}
        total_w = 0.0

        for t in portfolio_universe:
            w = st.sidebar.slider(f"Weight: {t}", 0.0, 1.0, float(equal_weight), 0.05)
            weights[t] = w
            total_w += w

        if total_w > 0:
            weights = {t: round(w / total_w, 4) for t, w in weights.items()}
            st.sidebar.info(f"Total Normalized Allocation: 100.0%")
        else:
            st.sidebar.warning("Sum of weights is 0%")

        if total_w == 0:
            st.warning("⚠️ All asset weights are set to 0%. Please adjust the sliders in the sidebar to allocate weight to your portfolio.")
        else:
            try:
                portfolio_results = compute_portfolio_metrics(df, weights, sector_map)

                # Metric Cards
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Annualised Return", f"{portfolio_results['annualised_return'] * 100:+.2f}%")
                with col2:
                    st.metric("Annualised Volatility", f"{portfolio_results['annualised_volatility'] * 100:.2f}%")
                with col3:
                    st.metric("Sharpe Ratio", f"{portfolio_results['sharpe_ratio']:.2f}" if portfolio_results['sharpe_ratio'] is not None else "N/A")
                with col4:
                    st.metric("Max Drawdown", f"{portfolio_results['max_drawdown'] * 100:.2f}%")

                st.markdown("---")

                col_left, col_right = st.columns(2)

                with col_left:
                    sector_df = pd.DataFrame(
                        list(portfolio_results["sector_allocation"].items()),
                        columns=["Sector", "Weight"]
                    )
                    fig_sector = px.pie(
                        sector_df,
                        values="Weight",
                        names="Sector",
                        title="Sector Allocation Breakdown",
                        template="plotly_dark",
                        hole=0.4,
                    )
                    st.plotly_chart(fig_sector, width="stretch")

                with col_right:
                    risk_df = pd.DataFrame(
                        list(portfolio_results["risk_contribution"].items()),
                        columns=["Ticker", "Risk Contribution"]
                    )
                    fig_risk = px.bar(
                        risk_df,
                        x="Ticker",
                        y="Risk Contribution",
                        title="Marginal Risk Contribution by Asset",
                        template="plotly_dark",
                        color="Risk Contribution",
                        color_continuous_scale="Reds",
                    )
                    st.plotly_chart(fig_risk, width="stretch")

                # Equity Curve Chart
                st.subheader("Portfolio Historical Growth (Equity Curve)")
                eq_dates = pd.to_datetime(portfolio_results["dates"])
                eq_curve = portfolio_results["equity_curve"]
                fig_eq = px.line(
                    x=eq_dates,
                    y=eq_curve,
                    title="Portfolio Value ($1.0 Initial Investment)",
                    template="plotly_dark",
                    labels={"x": "Date", "y": "Portfolio Value ($)"}
                )
                st.plotly_chart(fig_eq, width="stretch")

            except Exception as exc:
                st.error(f"Portfolio calculation error: {exc}")
    else:
        st.info("💡 Please select at least one asset from 'Select Portfolio Assets' in the left sidebar.")

# -----------------------------------------------------------------------------
# Module 3: ML Market Regime & Forecasting
# -----------------------------------------------------------------------------
elif page == M_REGIME:
    st.title("🤖 ML Regime Classification & Trend Forecasting")
    st.caption("Random Forest market regime detection and Exponential Smoothing price trend forecasting with uncertainty bounds.")

    selected_ticker = st.selectbox("Select Asset for ML Analysis:", options=all_tickers, index=0)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Random Forest Market Regime Classifier")
        try:
            pred_df = predict_regimes(df)
        except Exception:
            with st.spinner("Training Random Forest Regime Classifier..."):
                train_regime_classifier(df)
            pred_df = predict_regimes(df)

        asset_preds = pred_df[pred_df["ticker"] == selected_ticker]
        if not asset_preds.empty:
            latest_regime = asset_preds["regime_label"].iloc[-1]
            st.metric(f"{selected_ticker} Current Regime", latest_regime)

            fig_reg = px.histogram(
                asset_preds,
                x="regime_label",
                title=f"{selected_ticker} Historical Regime Distribution",
                template="plotly_dark",
                color="regime_label",
            )
            st.plotly_chart(fig_reg, width="stretch")

    with col2:
        st.subheader("2. Price Trend Forecaster")
        horizon = st.slider("Forecast Horizon (Trading Days):", 10, 90, 30, 5)

        try:
            forecast = forecast_price_trend(df, selected_ticker, horizon=horizon)

            hist_dates = pd.to_datetime(forecast["historical_dates"])
            hist_prices = forecast["historical_prices"]
            fc_dates = pd.to_datetime(forecast["forecast_dates"])
            fc_vals = forecast["forecast_values"]
            lower_b = forecast["lower_bound"]
            upper_b = forecast["upper_bound"]

            fig_fc = go.Figure()
            fig_fc.add_trace(go.Scatter(x=hist_dates[-120:], y=hist_prices[-120:], name="Historical Price", line=dict(color="#2962FF", width=2)))
            fig_fc.add_trace(go.Scatter(x=fc_dates, y=fc_vals, name="Forecast Trend", line=dict(color="#00E676", width=2, dash="dash")))
            fig_fc.add_trace(go.Scatter(x=fc_dates, y=upper_b, name="Upper Bound (90%)", line=dict(color="rgba(0, 230, 118, 0.2)"), showlegend=False))
            fig_fc.add_trace(go.Scatter(x=fc_dates, y=lower_b, name="90% Confidence Interval", fill="tonexty", fillcolor="rgba(0, 230, 118, 0.15)", line=dict(color="rgba(0, 230, 118, 0.2)")))

            fig_fc.update_layout(
                title=f"{selected_ticker} {horizon}-Day Trend Estimate ({forecast['model_name']})",
                template="plotly_dark",
                hovermode="x unified",
                yaxis_title="Price ($)",
            )
            st.plotly_chart(fig_fc, width="stretch")
            st.caption(forecast["disclaimer"])

        except Exception as exc:
            st.error(f"Forecasting error: {exc}")

# -----------------------------------------------------------------------------
# Module 4: Single Asset Deep Dive
# -----------------------------------------------------------------------------
elif page == M_DEEPDIVE:
    st.title("🔍 Single Asset Analytical Deep Dive")
    selected_t = st.selectbox("Choose asset to inspect:", options=all_tickers, index=0)

    asset_df = df[df["ticker"] == selected_t].sort_values("date")
    info = ASSET_UNIVERSE.get(selected_t, {})

    st.markdown(f"### **{info.get('name', selected_t)}** ({selected_t}) — Sector: `{info.get('sector', 'General')}`")

    if not asset_df.empty:
        last_row = asset_df.iloc[-1]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Latest Adj Close", f"${last_row['adj_close']:.2f}")
        with col2:
            st.metric("Daily Return", f"{last_row['daily_return'] * 100:+.2f}%")
        with col3:
            ma20_val = last_row.get("ma_20", last_row["adj_close"])
            st.metric("20D Moving Avg", f"${ma20_val:.2f}")
        with col4:
            vol20_val = last_row.get("vol_20d", 0.0)
            st.metric("20D Volatility", f"{vol20_val * 100:.2f}%")

        st.markdown("---")

        fig_ma = go.Figure()
        fig_ma.add_trace(go.Scatter(x=asset_df["date"], y=asset_df["adj_close"], name="Adj Close", line=dict(color="#00E676", width=2)))
        if "ma_20" in asset_df.columns:
            fig_ma.add_trace(go.Scatter(x=asset_df["date"], y=asset_df["ma_20"], name="20D MA", line=dict(color="#FF9100", width=1.5)))
        if "ma_50" in asset_df.columns:
            fig_ma.add_trace(go.Scatter(x=asset_df["date"], y=asset_df["ma_50"], name="50D MA", line=dict(color="#2962FF", width=1.5)))

        fig_ma.update_layout(title=f"{selected_t} Price & Moving Averages", template="plotly_dark", yaxis_title="Price ($)", hovermode="x unified")
        st.plotly_chart(fig_ma, width="stretch")

        fig_vol = px.bar(asset_df, x="date", y="volume", title=f"{selected_t} Daily Trading Volume", template="plotly_dark")
        st.plotly_chart(fig_vol, width="stretch")
    else:
        st.warning(f"No data available for {selected_t}")

st.markdown("---")
st.caption("MarketLens Platform | Powered by FastAPI, Streamlit, PostgreSQL & Plotly | Developed for LSEG Graduate Analytics Role")

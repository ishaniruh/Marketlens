"""
MarketLens — FastAPI Backend

RESTful API exposing all analytics capabilities to the frontend.
Endpoints are organized by domain:
  /api/market   — market overview and asset data
  /api/portfolio — portfolio analytics
  /api/forecast  — price trend forecasting
  /api/regime    — market regime classification
  /api/insights  — AI-generated business insights (Gemini)
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routes import market, portfolio, forecast, regime, insights
from backend.db import get_db_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MarketLens API starting …")
    yield
    logger.info("MarketLens API shutting down.")


# ── App creation ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="MarketLens API",
    description=(
        "Financial Market Intelligence & Portfolio Analytics Platform. "
        "All financial metrics are calculated from historical market data sourced from Yahoo Finance. "
        "This API is for analytical and educational purposes. Not financial advice."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(market.router,    prefix="/api/market",    tags=["Market Data"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio Analytics"])
app.include_router(forecast.router,  prefix="/api/forecast",  tags=["Forecasting"])
app.include_router(regime.router,    prefix="/api/regime",    tags=["Market Regime"])
app.include_router(insights.router,  prefix="/api/insights",  tags=["AI Insights"])

# ── Serve frontend ────────────────────────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(frontend_path, "static")),
    name="static",
)

@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse(os.path.join(frontend_path, "templates", "index.html"))

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "MarketLens API", "version": "1.0.0"}

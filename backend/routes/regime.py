"""MarketLens — Market Regime Routes"""

import logging
import pandas as pd
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from backend.db import get_db_engine
from models.regime_classifier import train_regime_classifier, predict_regimes, build_features

router = APIRouter()
logger = logging.getLogger(__name__)


def _load_enriched_data() -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT date, ticker, sector, adj_close, daily_return,
                   vol_20d, vol_60d, ma_20, ma_50, volume
            FROM market_data
            WHERE daily_return IS NOT NULL AND vol_20d IS NOT NULL
            ORDER BY ticker, date
        """))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


@router.post("/train")
def train_model():
    """
    Train the market regime classifier on current database data.
    Run this once after the data pipeline populates the database.
    """
    try:
        df     = _load_enriched_data()
        result = train_regime_classifier(df)
        return {
            "status":               "trained",
            "cv_accuracy":          result["cv_accuracy"],
            "feature_importance":   result["feature_importance"],
            "label_map":            result["label_map"],
            "methodology":          result["methodology"],
        }
    except Exception as e:
        logger.exception("Model training failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict")
def get_regime_predictions(ticker: str = None):
    """
    Return market regime classifications for all (or a specific) ticker.
    Model must be trained first via POST /api/regime/train.
    """
    try:
        df       = _load_enriched_data()
        if ticker:
            df = df[df["ticker"] == ticker.upper()]
            if df.empty:
                raise HTTPException(status_code=404, detail=f"No data for ticker '{ticker}'.")
        pred_df  = predict_regimes(df)
        # Return latest 90 days per ticker for the frontend
        pred_df  = pred_df.sort_values(["ticker", "date"])
        recent   = pred_df.groupby("ticker").tail(90)
        return {
            "predictions": recent.to_dict(orient="records"),
            "disclaimer":  "Market regime labels are derived from historical volatility patterns. "
                           "They reflect past conditions and are not predictive of future regimes.",
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Regime prediction failed")
        raise HTTPException(status_code=500, detail=str(e))

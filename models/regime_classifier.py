"""
MarketLens — Market Regime Classification Model

Classifies each trading day into one of three volatility regimes:
  - Low Volatility
  - Medium Volatility
  - High Volatility

This is a meaningful ML use-case: understanding the current market regime
helps investors calibrate risk tolerance and position sizing.

Methodology:
  - Features: rolling returns, rolling volatility, volume z-score, MA spread
  - Labels: derived from historical volatility tertiles (unsupervised labelling
    → supervised classification so the model generalises to unseen dates)
  - Model: Random Forest Classifier (interpretable, handles non-linearity)
  - Evaluation: Classification report + confusion matrix

DISCLAIMER: This model classifies historical patterns. It is NOT a price
prediction tool and should not be used as the basis for investment decisions.
"""

import logging
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODEL_DIR  = Path(__file__).parent
MODEL_PATH  = MODEL_DIR / "regime_classifier.pkl"
SCALER_PATH = MODEL_DIR / "regime_scaler.pkl"


# ── Feature Engineering ───────────────────────────────────────────────────────

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature matrix from daily market data for regime classification.

    Features per ticker-day:
      - daily_return
      - vol_20d   (annualised 20-day rolling vol)
      - vol_60d   (annualised 60-day rolling vol)
      - ma_spread (MA20 - MA50 as % of price)  — momentum signal
      - volume_z  (z-score of daily volume within trailing 60 days)
      - return_5d (5-day rolling mean return)
      - return_20d (20-day rolling mean return)
    """
    features = df.copy().sort_values(["ticker", "date"])

    features["ma_spread"] = (features["ma_20"] - features["ma_50"]) / features["adj_close"]

    def volume_zscore(v: pd.Series) -> pd.Series:
        roll_mean = v.rolling(60, min_periods=10).mean()
        roll_std  = v.rolling(60, min_periods=10).std()
        return (v - roll_mean) / roll_std.replace(0, np.nan)

    features["volume_z"] = features.groupby("ticker")["volume"].transform(volume_zscore)

    features["return_5d"]  = features.groupby("ticker")["daily_return"].transform(
        lambda x: x.rolling(5, min_periods=3).mean()
    )
    features["return_20d"] = features.groupby("ticker")["daily_return"].transform(
        lambda x: x.rolling(20, min_periods=10).mean()
    )

    FEATURE_COLS = [
        "daily_return", "vol_20d", "vol_60d",
        "ma_spread", "volume_z", "return_5d", "return_20d",
    ]
    return features[["date", "ticker", "sector"] + FEATURE_COLS].dropna()


def label_regime(df: pd.DataFrame, feature_df: pd.DataFrame) -> pd.Series:
    """
    Create regime labels based on the 33rd and 67th percentile of vol_20d.
    Label 0 = Low Vol, 1 = Medium Vol, 2 = High Vol
    """
    q33 = feature_df["vol_20d"].quantile(0.33)
    q67 = feature_df["vol_20d"].quantile(0.67)

    labels = pd.cut(
        feature_df["vol_20d"],
        bins=[-np.inf, q33, q67, np.inf],
        labels=[0, 1, 2],
    ).astype(int)
    return labels


# ── Training ──────────────────────────────────────────────────────────────────

def train_regime_classifier(df: pd.DataFrame) -> dict:
    """
    Train a Random Forest regime classifier using time-series cross-validation.

    Returns a dict with model, scaler, feature importance, and evaluation metrics.
    """
    logger.info("Building features for regime classification …")
    feature_df = build_features(df)
    labels     = label_regime(df, feature_df)

    FEATURE_COLS = [
        "daily_return", "vol_20d", "vol_60d",
        "ma_spread", "volume_z", "return_5d", "return_20d",
    ]

    X = feature_df[FEATURE_COLS].values
    y = labels.values

    # ── Time-series-aware cross validation (no data leakage) ─────────────
    tscv = TimeSeriesSplit(n_splits=5)
    cv_reports = []

    scaler = StandardScaler()
    clf    = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=20,
        random_state=42,
        n_jobs=-1,
    )

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        X_train_s = scaler.fit_transform(X_train)
        X_test_s  = scaler.transform(X_test)
        clf.fit(X_train_s, y_train)
        preds = clf.predict(X_test_s)

        report = classification_report(
            y_test, preds,
            target_names=["Low Vol", "Med Vol", "High Vol"],
            output_dict=True,
            zero_division=0,
        )
        cv_reports.append(report)
        logger.info("  Fold %d accuracy: %.3f", fold + 1, report["accuracy"])

    # ── Final fit on all data ─────────────────────────────────────────────
    X_scaled = scaler.fit_transform(X)
    clf.fit(X_scaled, y)

    # ── Feature importance ────────────────────────────────────────────────
    importance = dict(zip(FEATURE_COLS, clf.feature_importances_.tolist()))
    avg_accuracy = np.mean([r["accuracy"] for r in cv_reports])

    logger.info("Final model trained. Average CV accuracy: %.3f", avg_accuracy)

    # Persist
    with open(MODEL_PATH,  "wb") as f: pickle.dump(clf,    f)
    with open(SCALER_PATH, "wb") as f: pickle.dump(scaler, f)
    logger.info("Model saved to %s", MODEL_PATH)

    return {
        "model":            clf,
        "scaler":           scaler,
        "feature_cols":     FEATURE_COLS,
        "feature_importance": importance,
        "cv_accuracy":      round(avg_accuracy, 4),
        "label_map":        {0: "Low Volatility", 1: "Medium Volatility", 2: "High Volatility"},
        "methodology": (
            "Random Forest Classifier trained on rolling volatility, return momentum, "
            "volume z-score, and MA spread features. Labels derived from historical "
            "vol_20d tertile thresholds. Time-series cross-validation (5 folds) used "
            "to prevent data leakage. Model classifies market regimes — it is NOT a "
            "price prediction tool."
        ),
    }


# ── Inference ─────────────────────────────────────────────────────────────────

def predict_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Load trained model and return DataFrame with regime predictions appended.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run train_regime_classifier() first."
        )

    with open(MODEL_PATH,  "rb") as f: clf    = pickle.load(f)
    with open(SCALER_PATH, "rb") as f: scaler = pickle.load(f)

    FEATURE_COLS = [
        "daily_return", "vol_20d", "vol_60d",
        "ma_spread", "volume_z", "return_5d", "return_20d",
    ]
    feature_df = build_features(df)
    X_scaled   = scaler.transform(feature_df[FEATURE_COLS].values)
    preds      = clf.predict(X_scaled)
    proba      = clf.predict_proba(X_scaled)

    label_map = {0: "Low Volatility", 1: "Medium Volatility", 2: "High Volatility"}

    feature_df = feature_df.copy()
    feature_df["regime_label"] = [label_map[p] for p in preds]
    feature_df["prob_low_vol"]  = proba[:, 0]
    feature_df["prob_med_vol"]  = proba[:, 1]
    feature_df["prob_high_vol"] = proba[:, 2]

    return feature_df

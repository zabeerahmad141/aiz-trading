"""
XGBoost Model — primary trading signal generator.
XGBoost is fast, accurate, and handles financial time-series well.

How it works:
  1. Trained on 3 years of OHLCV data + 24 technical indicators
  2. Learns patterns that precede price increases/decreases
  3. Outputs probability score (0-1) → converted to BUY/SELL/HOLD
  4. Re-trained daily at 8 AM (before market opens)
"""
import os
import pickle
import numpy as np
import pandas as pd
import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
from loguru import logger

from src.data.features import FEATURE_COLUMNS


MODEL_PATH = "models/xgboost_model.pkl"
SCALER_PATH = "models/xgboost_scaler.pkl"


class XGBoostTradingModel:
    def __init__(self):
        self.model: xgb.XGBClassifier | None = None
        self.scaler: StandardScaler | None = None
        self._load_if_exists()

    def _load_if_exists(self):
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(SCALER_PATH, "rb") as f:
                self.scaler = pickle.load(f)
            logger.info("XGBoost model loaded from disk.")

    def train(self, df: pd.DataFrame, symbol: str = "AGGREGATE") -> dict:
        """
        Train on feature-engineered dataframe.
        Uses TimeSeriesSplit to prevent look-ahead bias.
        """
        os.makedirs("models", exist_ok=True)
        X = df[FEATURE_COLUMNS].values
        y = df["target"].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # TimeSeriesSplit — crucial for financial data (no future leakage)
        tscv = TimeSeriesSplit(n_splits=5)
        fold_scores = []

        model = xgb.XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            tree_method="hist",
        )

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_scaled)):
            model.fit(
                X_scaled[train_idx], y[train_idx],
                eval_set=[(X_scaled[val_idx], y[val_idx])],
                verbose=False,
            )
            preds = model.predict(X_scaled[val_idx])
            acc = accuracy_score(y[val_idx], preds)
            fold_scores.append(acc)
            logger.info(f"Fold {fold+1} accuracy: {acc:.3f}")

        avg_acc = np.mean(fold_scores)
        logger.info(f"Mean CV Accuracy: {avg_acc:.3f}")

        # Final fit on all data
        model.fit(X_scaled, y, verbose=False)
        self.model = model
        self.scaler = scaler

        with open(MODEL_PATH, "wb") as f:
            pickle.dump(model, f)
        with open(SCALER_PATH, "wb") as f:
            pickle.dump(scaler, f)

        # Log to MLflow
        try:
            with mlflow.start_run(run_name=f"xgboost_{symbol}"):
                mlflow.log_metric("cv_accuracy", avg_acc)
                mlflow.log_param("n_estimators", 500)
                mlflow.log_param("symbol", symbol)
                mlflow.xgboost.log_model(model, "model")
        except Exception as e:
            logger.warning(f"MLflow logging failed (non-critical): {e}")

        return {"accuracy": round(avg_acc, 4), "folds": fold_scores}

    def predict(self, features: pd.DataFrame) -> dict:
        """
        Returns signal dict: {signal: BUY/SELL/HOLD, confidence: 0-100, proba: float}
        """
        if self.model is None or self.scaler is None:
            return {"signal": "HOLD", "confidence": 0, "proba": 0.5}

        X = features[FEATURE_COLUMNS].values
        X_scaled = self.scaler.transform(X)
        proba = self.model.predict_proba(X_scaled)[0]
        buy_proba = float(proba[1])

        if buy_proba >= 0.65:
            signal = "BUY"
        elif buy_proba <= 0.35:
            signal = "SELL"
        else:
            signal = "HOLD"

        confidence = int(abs(buy_proba - 0.5) * 200)

        return {
            "signal": signal,
            "confidence": min(confidence, 99),
            "proba": round(buy_proba, 4),
        }

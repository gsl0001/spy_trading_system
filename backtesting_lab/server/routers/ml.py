"""
ML API Router — Endpoints for training and managing ML models.
"""
import sys
import os
from fastapi import APIRouter
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backtesting_lab.server.models import (
    MLTrainRequest, MLTrainResponse, MLStatusResponse,
    FeatureImportanceResponse, StatusResponse
)

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])

# Global ML filter reference (injected from main.py)
_ml_filter = None


def set_ml_filter(ml_filter):
    """Inject the ML filter instance."""
    global _ml_filter
    _ml_filter = ml_filter


@router.get("/status", response_model=MLStatusResponse)
async def get_ml_status():
    """Get current ML model status and capabilities."""
    if _ml_filter is None:
        return MLStatusResponse()

    return MLStatusResponse(
        is_trained=getattr(_ml_filter, 'is_trained', False),
        is_ensemble_trained=getattr(_ml_filter, 'is_ensemble_trained', False),
        reliability_score=round(getattr(_ml_filter, 'reliability_score', 0), 4),
        confidence_threshold=_ml_filter.confidence_threshold,
        feature_count=len(getattr(_ml_filter, 'features', [])),
        features=getattr(_ml_filter, 'features', []),
        trust_scores=getattr(_ml_filter, 'trust_scores', {}),
    )


@router.post("/train", response_model=MLTrainResponse)
async def train_model(req: MLTrainRequest):
    """Train or retrain the ML model."""
    if _ml_filter is None:
        return MLTrainResponse(success=False, message="ML engine not initialized")

    try:
        from core.data import fetch_spy_data, preprocess_data, merge_macro_data
        from core.strategies import BacktestEngine
        from core.sentiment import get_insider_sentiment
        from core.macro_engine import get_macro_context
        import pandas as pd

        # Fetch full historical data
        d_p, d_m, d_v = fetch_spy_data(interval="1d", years=12)
        df_all = preprocess_data(d_p, d_m, d_v)
        macro_df = get_macro_context()
        df_all = merge_macro_data(df_all, macro_df)

        # Sentiment
        sentiment_df = get_insider_sentiment()
        if not sentiment_df.empty:
            df_all['temp_date'] = pd.to_datetime(df_all.index.date)
            sentiment_df.index = pd.to_datetime(sentiment_df.index)
            idx_name = df_all.index.name or 'Date'
            df_all = df_all.reset_index().merge(
                sentiment_df, left_on='temp_date', right_index=True, how='left'
            ).set_index(idx_name)
            df_all['Insider_Sentiment'] = df_all['Insider_Sentiment'].ffill().fillna(1.0)
            df_all.drop(columns=['temp_date'], inplace=True)
        else:
            df_all['Insider_Sentiment'] = 1.0

        engine = BacktestEngine(df_all, initial_capital=100000, risk_pc=1.0)

        if req.mode == "ensemble":
            # Train ensemble on all strategies
            from server.routers.backtest import STRATEGY_CATALOG
            strategy_names = [s.full_name for s in STRATEGY_CATALOG if s.id <= 37]
            signal_df = engine.get_all_signals(strategy_names)
            all_trades = pd.concat([engine.run_strategy(s)[0] for s in strategy_names])
            success, msg = _ml_filter.train_ensemble(df_all, signal_df, all_trades)
        else:
            # Train base model
            if req.strategy:
                trades = engine.run_strategy(req.strategy)[0]
            else:
                from server.routers.backtest import STRATEGY_CATALOG
                strategy_names = [s.full_name for s in STRATEGY_CATALOG if s.id <= 37]
                trades = pd.concat([engine.run_strategy(s)[0] for s in strategy_names])
            success, msg = _ml_filter.train(df_all, trades)

        return MLTrainResponse(
            success=success,
            message=msg,
            reliability_score=round(_ml_filter.reliability_score, 4) if success else 0,
        )

    except Exception as e:
        logger.error(f"ML training failed: {e}")
        return MLTrainResponse(success=False, message=f"Training failed: {str(e)}")


@router.get("/importance", response_model=FeatureImportanceResponse)
async def get_feature_importance():
    """Get feature importance scores from the trained model."""
    if _ml_filter is None or not _ml_filter.is_trained:
        return FeatureImportanceResponse(features={}, is_ensemble=False)

    is_ensemble = getattr(_ml_filter, 'is_ensemble_trained', False)
    importance = _ml_filter.get_feature_importance(use_ensemble=is_ensemble)

    return FeatureImportanceResponse(
        features=importance,
        is_ensemble=is_ensemble,
    )


@router.post("/export", response_model=StatusResponse)
async def export_model():
    """Save the trained model to disk."""
    if _ml_filter is None or not _ml_filter.is_trained:
        return StatusResponse(success=False, message="No trained model to export")

    try:
        import joblib
        from pathlib import Path

        save_dir = Path("models")
        save_dir.mkdir(exist_ok=True)

        from datetime import datetime
        filename = save_dir / f"ml_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        export_data = {
            "model": _ml_filter.model,
            "ensemble_model": getattr(_ml_filter, 'ensemble_model', None),
            "features": _ml_filter.features,
            "base_features": _ml_filter.base_features,
            "ensemble_features": getattr(_ml_filter, 'ensemble_features', []),
            "trust_scores": getattr(_ml_filter, 'trust_scores', {}),
            "reliability_score": _ml_filter.reliability_score,
        }

        joblib.dump(export_data, filename)
        return StatusResponse(
            success=True,
            message=f"Model exported to {filename}",
            data={"path": str(filename)}
        )
    except Exception as e:
        return StatusResponse(success=False, message=f"Export failed: {str(e)}")

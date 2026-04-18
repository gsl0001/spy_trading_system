import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.metrics import accuracy_score
from sklearn.cluster import KMeans

class MarketRegimeDetector:
    def __init__(self, n_regimes=4):
        self.n_regimes = n_regimes
        self.model = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
        self.is_fitted = False
        self.regime_features = ['ATR_Pct', 'SMA_20_Dist', 'Momentum_10']

    def fit(self, data):
        X = data[self.regime_features].dropna()
        self.model.fit(X)
        self.is_fitted = True
        return self.predict(data)

    def predict(self, data):
        if not self.is_fitted:
            return pd.Series(0, index=data.index)
        X = data[self.regime_features].fillna(0)
        return self.model.predict(X)

class MLSignalFilter:
    def __init__(self, confidence_threshold=0.5):
        self.model = XGBClassifier(
            objective='binary:logistic',
            random_state=42,
            n_jobs=-1
        )
        self.confidence_threshold = confidence_threshold
        self.is_trained = False
        self.is_base_trained = False
        self.regime_detector = MarketRegimeDetector()
        self.reliability_score = 0.0
        self.base_features = [
            'SMA_20_Dist', 'SMA_50_Dist', 'RSI', 'Vol_Ratio', 'Hist_Vol',
            'ADX_14', 'MACD_Hist_Dist', 'BB_Percent', 'Momentum_10', 'ATR_Pct',
            'CMF', 'CCI_14', 'Insider_Sentiment', 'T10Y2Y', 'FEDFUNDS', 'Market_Regime'
        ]
        self.features = self.base_features.copy()

    def train(self, data, trades):
        if len(trades) < 15: 
            return False, f"Insufficient trade data: Found {len(trades)}, need 15. Tip: Try a faster interval (e.g., 15m) or a wider date range."

        # 1. Fit Market Regimes
        regime_labels = self.regime_detector.fit(data)
        data_with_regime = data.copy()
        data_with_regime['Market_Regime'] = regime_labels

        # 2. Prepare Training Set
        df_trades = pd.DataFrame(trades)
        df_trades['label'] = (df_trades['PnL'] > 0).astype(int)
        
        training_data = []
        labels = []
        for _, trade in df_trades.iterrows():
            entry_date = trade['Date In']
            if entry_date in data_with_regime.index:
                feat_row = data_with_regime.loc[entry_date][self.features]
                if not feat_row.isnull().any():
                    training_data.append(feat_row.values)
                    labels.append(trade['label'])

        if len(training_data) < 10:
            return False, "Not enough valid feature rows found."

        X = np.array(training_data).astype(float)
        y = np.array(labels)
        
        if len(np.unique(y)) < 2:
            return False, "Need both Winners and Losers to learn signals."

        # 3. Hyperparameter Auto-Tuning
        param_dist = {
            'n_estimators': [50, 100],
            'max_depth': [2, 3],
            'learning_rate': [0.05, 0.1],
            'subsample': [0.8, 1.0]
        }
        
        # Use TimeSeriesSplit for more realistic validation
        tscv = TimeSeriesSplit(n_splits=2) # Reduced splits for small data
        random_search = RandomizedSearchCV(
            self.model, param_distributions=param_dist, 
            n_iter=5, cv=tscv, scoring='accuracy', n_jobs=-1, random_state=42
        )
        
        random_search.fit(X, y)
        self.model = random_search.best_estimator_
        self.reliability_score = random_search.best_score_
        self.is_trained = True
        self.is_base_trained = True
        
        return True, f"Trained with {len(X)} trades. Reliability: {self.reliability_score:.2f}"

    def train_0dte(self, data, trades):
        """Specialized training for the 1-minute 0DTE VWAP Breakout model."""
        if len(trades) < 5: 
            return False, f"Insufficient 1m trade data: Found {len(trades)}. Need at least 5 for 0DTE training."

        df_trades = pd.DataFrame(trades)
        df_trades['label'] = (df_trades['PnL'] > 0).astype(int)
        
        # Specific features for the 0DTE live hub
        training_features = ['MACD_Hist_Dist', 'CMF', 'VWAP_Proxy_Dist']
        
        training_data = []
        labels = []
        for _, trade in df_trades.iterrows():
            entry_date = trade['Date In']
            if entry_date in data.index:
                feat_row = data.loc[entry_date][training_features]
                if not feat_row.isnull().any():
                    training_data.append(feat_row.values)
                    labels.append(trade['label'])

        if len(training_data) < 5:
            return False, "Not enough valid feature rows found for 0DTE."

        X = np.array(training_data).astype(float)
        y = np.array(labels)
        
        if len(np.unique(y)) < 2:
            return False, "Need both Winners and Losers to learn 0DTE signals."

        param_dist = {
            'n_estimators': [50, 100],
            'max_depth': [2, 3],
            'learning_rate': [0.05, 0.1]
        }
        
        from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
        tscv = TimeSeriesSplit(n_splits=2)
        random_search = RandomizedSearchCV(
            self.model, param_distributions=param_dist, 
            n_iter=5, cv=tscv, scoring='accuracy', n_jobs=-1, random_state=42
        )
        
        random_search.fit(X, y)
        self.model = random_search.best_estimator_
        self.reliability_score = random_search.best_score_
        self.is_trained = True
        
        # Save model specifically for live trading hub
        import joblib
        import os
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'my_0dte_model.pkl')
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(self.model, model_path)
        
        return True, f"0DTE Model trained with {len(X)} trades and saved to {model_path}."

    def predict(self, feature_vector):
        if not self.is_trained:
            return 1.0
        
        # Robust dimensionality check
        X = np.array([feature_vector]).astype(float).reshape(1, -1)
        
        # If the input matches ensemble size, use ensemble model if available
        if getattr(self, 'is_ensemble_trained', False) and hasattr(self, 'ensemble_model') and self.ensemble_model is not None:
            if X.shape[1] == len(getattr(self, 'ensemble_features', [])):
                return self.ensemble_model.predict_proba(X)[0][1]
        
        # Fallback to base model (standard strategy AI)
        # Check if shape matches Base Model (16 features typically)
        if getattr(self, 'is_base_trained', False) and getattr(self, 'model', None) and X.shape[1] == len(self.base_features):
             return self.model.predict_proba(X)[0][1]
             
        return 0.5 # Default to neutral if no model matches shape

    def get_feature_importance(self, use_ensemble=False):
        if use_ensemble and hasattr(self, 'ensemble_model'):
            importance = self.ensemble_model.feature_importances_
            return dict(zip(self.ensemble_features, [round(float(f), 3) for f in importance]))
        
        if not self.is_trained or not self.model:
            return {}
        importance = self.model.feature_importances_
        return dict(zip(self.features, [round(float(f), 3) for f in importance]))

class MLEnsembleFilter(MLSignalFilter):
    def __init__(self, confidence_threshold=0.5):
        super().__init__(confidence_threshold)
        self.features = self.base_features.copy()
        self.trust_scores = {}
        self.is_ensemble_trained = False
        self.ensemble_model = None
        self.ensemble_features = []

    def train(self, data, trades):
        """Force reset to base features for standard single-strategy training."""
        self.features = self.base_features.copy()
        self.is_ensemble_trained = False
        return super().train(data, trades)

    def train_ensemble(self, data, signal_df, trades):
        """
        Special training for the ensemble.
        dataset: Combine data indicators + strategy signals.
        """
        if len(trades) < 25:
            return False, f"Ensemble needs 25 historical trades. Found {len(trades)}."
            
        # 1. Align signals with main data
        orig_names = signal_df.columns.tolist()
        merged = pd.concat([data, signal_df], axis=1)
        
        # 2. Extract features for each trade
        X_list = []
        y_list = []
        
        # Track which features we are using
        self.ensemble_features = self.base_features + orig_names
        
        for _, trade in trades.iterrows():
            entry_date = trade['Date In']
            target = 1 if trade['PnL'] > 0 else 0
            
            if entry_date in merged.index:
                # Use all merged features (indicators + signals)
                feat_row = merged.loc[entry_date]
                # Ensure we only pick the columns we want in correct order
                feat_row = feat_row.reindex(self.ensemble_features).fillna(0)
                X_list.append(feat_row.values)
                y_list.append(target)
        
        if len(X_list) < 20:
             return False, "Insufficient localized trade data for Ensemble training."

        X = np.array(X_list)
        y = np.array(y_list)
        
        # 3. Train the ensemble model separately
        self.ensemble_model = XGBClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.05, 
            random_state=42, use_label_encoder=False, eval_metric='logloss'
        )
        
        param_dist = {
            'n_estimators': [100],
            'max_depth': [3],
            'learning_rate': [0.05],
            'gamma': [0.1]
        }
        
        tscv = TimeSeriesSplit(n_splits=2)
        n_iter_search = min(4, len(param_dist['n_estimators']) * len(param_dist['max_depth']))
        rs = RandomizedSearchCV(self.ensemble_model, param_dist, n_iter=n_iter_search, cv=tscv, scoring='accuracy', n_jobs=-1)
        rs.fit(X, y)
        
        self.ensemble_model = rs.best_estimator_
        self.reliability_score = rs.best_score_
        self.is_ensemble_trained = True
        self.is_trained = True # Mark as trained globally
        
        # Calculate strategy trust scores based on feature importance
        raw_imp = self.ensemble_model.feature_importances_
        imp_dict = dict(zip(self.ensemble_features, raw_imp))
        self.trust_scores = {}
        for s_name in orig_names:
            self.trust_scores[s_name] = round(float(imp_dict.get(s_name, 0)), 3)
        
        return True, f"Ensemble AI active. Reliability: {self.reliability_score:.2%} ({len(X)} samples)"

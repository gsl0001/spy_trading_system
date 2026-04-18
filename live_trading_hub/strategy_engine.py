import pandas as pd
import numpy as np

class StrategyEngine:
    def __init__(self, ai_confidence_threshold=0.60):
        self.ai_threshold = ai_confidence_threshold
        # Placeholder for AI model (e.g., loaded from pickle)
        self.ai_model = None 

    def load_ai_model(self, model_path="model.pkl"):
        """Load pretrained Scikit or XGBoost model."""
        import os
        import joblib
        if os.path.exists(model_path):
            try:
                self.ai_model = joblib.load(model_path)
                print(f"Loaded AI Model from {model_path}")
            except Exception as e:
                print(f"Failed to load AI Model from {model_path}: {e}")
        else:
            print(f"AI Model {model_path} not found. Running in dummy threshold mode.")

    def evaluate_bar(self, df: pd.DataFrame) -> dict:
        """
        Evaluates the latest bar for the VWAP Keltner Compression Breakout Strategy.
        Returns a dict: {"signal": "LONG"/"SHORT"/"NONE", "confidence": float}
        """
        if len(df) < 21:
            return {"signal": "NONE", "confidence": 0.0}

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # VWAP Proximity: price within 0.5% of VWAP_Proxy
        vwap_proximity = abs(latest['VWAP_Proxy_Dist']) < 0.005
        
        # Keltner Squeeze Logic
        sqz_on_prev = (prev['BB_Upper'] < prev['KC_Upper']) and (prev['BB_Lower'] > prev['KC_Lower'])
        sqz_on_curr = (latest['BB_Upper'] < latest['KC_Upper']) and (latest['BB_Lower'] > latest['KC_Lower'])
        squeeze_release = not sqz_on_curr and sqz_on_prev
        
        # CMF Institutional Flow
        flow_positive = latest['CMF'] > 0.05
        flow_negative = latest['CMF'] < -0.05
        
        # MACD Momentum Ignition
        macd_cross_up = (latest['MACD_Hist_Dist'] > 0) and (prev['MACD_Hist_Dist'] <= 0)
        macd_cross_down = (latest['MACD_Hist_Dist'] < 0) and (prev['MACD_Hist_Dist'] >= 0)
        
        signal = "NONE"
        if (vwap_proximity or squeeze_release) and flow_positive and macd_cross_up:
            signal = "LONG"
        elif (vwap_proximity or squeeze_release) and flow_negative and macd_cross_down:
            signal = "SHORT"
            
        # Get AI Trust Score
        confidence = self._get_ai_trust(df, signal)
        
        if signal != "NONE" and confidence >= self.ai_threshold:
            return {"signal": signal, "confidence": confidence}
            
        return {"signal": "NONE", "confidence": confidence}

    def _get_ai_trust(self, df, signal):
        """Passes the latest feature vector to the ML model to get probability."""
        if signal == "NONE":
            return 0.0
            
        if self.ai_model is None:
            # Dummy logic until real model is linked:
            # Assume any signal generated is blindly trusted for this scaffold if no model is present.
            return 0.90
            
        feat_vector = df.iloc[-1][['MACD_Hist_Dist', 'CMF', 'VWAP_Proxy_Dist']].values.reshape(1, -1)
        try:
            prob = self.ai_model.predict_proba(feat_vector)[0][1]
            return prob
        except Exception as e:
            print(f"Error predicting with ML model: {e}")
            return 0.5

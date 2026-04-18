import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Ensure the parent directory is in the path so we can import spy_trading_system modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data import fetch_spy_data, preprocess_data
import joblib
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_curve, auc, confusion_matrix

st.set_page_config(page_title="SPY AI Model Trainer", layout="wide", initial_sidebar_state="expanded")

# --- PREMIUM UI STYLE SETUP ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
    :root {
        --bg-main: #1C1C1E;
        --bg-card: #2C2C2E;
        --border-color: rgba(255, 255, 255, 0.1);
        --accent-green: #34C759;
        --accent-blue: #0A84FF;
        --accent-red: #FF3B30;
        --text-dim: #98989D;
    }
    .stApp {
        background-color: var(--bg-main);
        color: #F2F2F7;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #242426 !important;
        border-right: 1px solid var(--border-color);
    }
    .metric-box {
        background: var(--bg-card);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid var(--border-color);
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-val { font-family: 'JetBrains Mono'; font-size: 24px; font-weight: bold; color: var(--accent-blue); }
    .metric-lbl { font-size: 12px; color: var(--text-dim); text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.markdown("### 🧠 AI Trainer Settings")
st.sidebar.markdown("---")

st.sidebar.markdown("#### Data Origin")
data_years = st.sidebar.slider("Historical Data Scope (Years)", 1, 10, 5)
interval = st.sidebar.selectbox("Bar Interval", ["1d", "1h", "15m", "5m", "1m"], index=0)

st.sidebar.markdown("#### Model Architecture")
model_type = st.sidebar.selectbox("Algorithm", ["XGBoost Classifier", "Random Forest Classifier"])

st.sidebar.markdown("#### Hyperparameters")
col1, col2 = st.sidebar.columns(2)
n_estimators = col1.number_input("n_estimators", 10, 1000, 100, 10)
max_depth = col2.number_input("max_depth", 1, 20, 5, 1)

if model_type == "XGBoost Classifier":
    learning_rate = st.sidebar.slider("learning_rate", 0.001, 0.5, 0.05, 0.001)
else:
    learning_rate = None

test_size = st.sidebar.slider("Holdout Test Size (%)", 10, 50, 20) / 100.0
target_lookahead = st.sidebar.number_input("Target Lookahead (Bars)", 1, 50, 1)

AVAILABLE_FEATURES = [
    'RSI', 'MACD_Hist_Dist', 'Vol_Ratio', 'SMA_20_Dist', 'SMA_50_Dist', 
    'BB_Percent', 'ATR_Pct', 'CMF', 'Momentum_10', 'VIX_Close'
]
st.sidebar.markdown("#### Features")
selected_features = st.sidebar.multiselect("Select Feature Vector", AVAILABLE_FEATURES, default=AVAILABLE_FEATURES[:5])

# --- STATE MANAGEMENT ---
if 'trained_model' not in st.session_state:
    st.session_state.trained_model = None
if 'eval_metrics' not in st.session_state:
    st.session_state.eval_metrics = None
if 'model_features' not in st.session_state:
    st.session_state.model_features = None

def get_data():
    with st.spinner("Fetching Market Data..."):
        df1, dfm, df2 = fetch_spy_data(interval, data_years)
        df = preprocess_data(df1, dfm, df2)
        return df

def generate_target(df, lookahead=1):
    # Target: Will the forward price be positive?
    future_return = df['Close'].shift(-lookahead) / df['Close'] - 1
    target = (future_return > 0).astype(int)
    return target

# --- MAIN APP ---
st.markdown("## ⚙️ Quant Model Training Simulator")
st.markdown("Train, validate, and serialize machine learning weights for autonomous trading bots.")

if st.sidebar.button("🚀 Start Training", use_container_width=True):
    if not selected_features:
        st.error("Select at least one feature.")
    else:
        # Load & Prep Data
        df = get_data()
        df['Target'] = generate_target(df, target_lookahead)
        
        # Drop NaNs
        ml_df = df[selected_features + ['Target']].dropna()
        
        X = ml_df[selected_features].values
        y = ml_df['Target'].values
        
        # Time-Series Split (No random shuffling to prevent data leakage)
        train_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:train_idx], X[train_idx:]
        y_train, y_test = y[:train_idx], y[train_idx:]
        
        # Init Model
        st.info(f"Training on {len(X_train)} samples. Validating on {len(X_test)} samples.")
        
        if model_type == "XGBoost Classifier":
            model = XGBClassifier(
                n_estimators=n_estimators, 
                learning_rate=learning_rate, 
                max_depth=max_depth,
                random_state=42
            )
        else:
            model = RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=42
            )
            
        with st.spinner("Optimizing weights..."):
            model.fit(X_train, y_train)
            
            # Predict
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]
            
            # Metrics
            st.session_state.eval_metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1': f1_score(y_test, y_pred),
                'y_test': y_test,
                'y_prob': y_prob
            }
            
            # Feature Importance
            if hasattr(model, 'feature_importances_'):
                st.session_state.feature_importance = pd.DataFrame({
                    'Feature': selected_features,
                    'Importance': model.feature_importances_
                }).sort_values(by='Importance', ascending=True)
            
            st.session_state.trained_model = model
            st.session_state.model_features = selected_features

# --- DISPLAY RESULTS ---
if st.session_state.trained_model is not None:
    metrics = st.session_state.eval_metrics
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='metric-box'><div class='metric-lbl'>OOS Accuracy</div><div class='metric-val'>{metrics['accuracy']:.2%}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-box'><div class='metric-lbl'>Precision</div><div class='metric-val'>{metrics['precision']:.2%}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-box'><div class='metric-lbl'>Recall (Win Rate)</div><div class='metric-val'>{metrics['recall']:.2%}</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-box'><div class='metric-lbl'>F1-Score</div><div class='metric-val'>{metrics['f1']:.2%}</div></div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.markdown("### Feature Importance")
        fig = go.Figure(go.Bar(
            x=st.session_state.feature_importance['Importance'],
            y=st.session_state.feature_importance['Feature'],
            orientation='h',
            marker_color='#0A84FF'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#F2F2F7', margin=dict(l=0, r=0, t=30, b=0), height=350
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("### Receiver Operating Characteristic (ROC)")
        fpr, tpr, _ = roc_curve(metrics['y_test'], metrics['y_prob'])
        roc_auc = auc(fpr, tpr)
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines', name=f'AUC = {roc_auc:.3f}', line=dict(color='#34C759', width=2)))
        fig2.add_shape(type='line', line=dict(dash='dash', color='#98989D'), x0=0, x1=1, y0=0, y1=1)
        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#F2F2F7', margin=dict(l=0, r=0, t=30, b=0), height=350,
            xaxis_title='False Positive Rate', yaxis_title='True Positive Rate'
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("### Save Model Artifact")
    
    col_a, _ = st.columns([1, 2])
    with col_a:
        filename = st.text_input("Filename", value="my_0dte_model.pkl")
        if st.button("Export to Disk"):
            # Save the model and the expected feature list
            export_dict = {
                'model': st.session_state.trained_model,
                'features': st.session_state.model_features
            }
            joblib.dump(export_dict, filename)
            st.success(f"Model saved to `{filename}` successfully!")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core.data import fetch_spy_data, preprocess_data, merge_macro_data
from core.strategies import BacktestEngine
from core.options_engine import OptionsBacktestEngine
from core.ml_engine import MLEnsembleFilter
from core.sentiment import get_insider_sentiment
from core.macro_engine import get_macro_context
from streamlit_lightweight_charts import renderLightweightCharts
import datetime

# Page Config
st.set_page_config(page_title="SPY AI Quant Workstation", layout="wide", initial_sidebar_state="expanded")

# --- PREMIUM UI STYLE SETUP ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
    /* Global Overrides */
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
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: #242426 !important;
        border-right: 1px solid var(--border-color);
        padding-top: 1rem;
    }

    /* Hide Default Streamlit Elements */
    header, footer, [data-testid="stToolbar"] { visibility: hidden; height: 0; }
    
    /* Advanced Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #48484A; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #636366; }

    /* Component Overrides */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
        border-bottom: 1px solid var(--border-color);
        padding: 0 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        padding: 12px 4px;
        color: var(--text-dim);
        font-weight: 500;
        font-size: 14px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: none;
        letter-spacing: 0.2px;
    }
    
    .stTabs [aria-selected="true"] {
        color: var(--accent-blue) !important;
        background-color: transparent !important;
        border-bottom: 2px solid var(--accent-blue) !important;
    }

    /* Professional Card Styling */
    .glass-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Button Refinement */
    .stButton > button {
        background: var(--accent-blue) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
        letter-spacing: 0px !important;
        text-transform: none;
        transition: background 0.2s ease, filter 0.2s ease !important;
    }
    .stButton > button:hover {
        filter: brightness(110%);
        box-shadow: 0 4px 12px rgba(10, 132, 255, 0.3);
    }

    /* Input Styling */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background-color: #1C1C1E !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
        color: #F2F2F7 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Signal Indicators */
    .signal-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        position: relative;
    }
    .signal-pulse::after {
        content: '';
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: inherit;
        animation: pulse 2s ease-out infinite;
        opacity: 0.6;
    }
    @keyframes pulse {
        0% { transform: scale(1); opacity: 0.6; }
        100% { transform: scale(2.5); opacity: 0; }
    }
</style>
""", unsafe_allow_html=True)

if 'ml_filter' not in st.session_state:
    st.session_state.ml_filter = MLEnsembleFilter()

# --- CUSTOM SIDEBAR UI ---
st.sidebar.markdown("""
    <div style='margin-bottom: 3rem; padding: 0 0.5rem;'>
        <div style='display: flex; align-items: center; gap: 14px;'>
            <div style='background: #0A84FF; width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(10, 132, 255, 0.3);'>
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="4"/><path d="m9 15 2-2 4 4"/></svg>
            </div>
            <div>
                <h1 style='font-size: 20px; font-weight: 700; margin: 0; color: #F2F2F7; font-family: "Plus Jakarta Sans"; letter-spacing: -0.5px; line-height: 1;'>Quant<span style='color: #0A84FF;'>OS</span></h1>
                <p style='font-size: 10px; color: #98989D; font-weight: 500; margin-top: 2px; font-family: "Plus Jakarta Sans";'>Institutional Analytics</p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Sophisticated Market Status
is_live = datetime.datetime.now().hour >= 9 and datetime.datetime.now().hour < 16
status_color = "#34C759" if is_live else "#FF3B30"
st.sidebar.markdown(f"""
    <div style='background: #2C2C2E; border: 1px solid rgba(255, 255, 255, 0.1); padding: 14px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;'>
        <div style='display: flex; align-items: center; gap: 10px;'>
            <div class='signal-pulse' style='background: {status_color};'></div>
            <span style='font-size: 11px; font-weight: 600; color: #9ca3af;'>NYSE / NASDAQ</span>
        </div>
        <span style='font-size: 10px; font-weight: 800; color: {status_color}; text-transform: uppercase;'>{ "Live" if is_live else "Closed" }</span>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<p style='font-size: 10px; font-weight: 800; color: #4b5563; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-left: 4px;'>Core Intelligence</p>", unsafe_allow_html=True)
use_ml = st.sidebar.toggle("Ensemble Signal Filter", value=True)
ml_conf = st.sidebar.slider("ML Threshold", 0.4, 0.7, 0.5, 0.05)
st.session_state.ml_filter.confidence_threshold = ml_conf

st.sidebar.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

strategy_options = [
    "Strategy 1: 20/50 Trend Pullback", "Strategy 2: Range Breakout", "Strategy 3: Mean Reversion",
    "Strategy 4: Bull Put Spread (Syn)", "Strategy 5: Bear Call Spread (Syn)", "Strategy 6: Iron Condor (Syn)",
    "Strategy 7: Inside-Bar Breakout", "Strategy 8: 3-Day Pullback", "Strategy 9: Fade Strategy 4",
    "Strategy 10: Insider Alpha (Smart Money)", "Strategy 11: Combo Alpha (Multi-Signal)", "Strategy 12: Streak Follower",
    "Strategy 13: SuperTrend Follower", "Strategy 14: Ichimoku Cloud Breakout", "Strategy 15: EMA Ribbon Expansion",
    "Strategy 16: Donchian 20-Day Breakout", "Strategy 17: HMA Slope Pivot", "Strategy 18: Stochastic RS Fade",
    "Strategy 19: Fisher Transform Reversal", "Strategy 20: Parabolic SAR Flip", "Strategy 21: Volatility Squeeze Breakout",
    "Strategy 22: Money Flow Index (MFI)", "Strategy 23: ORB (30-min Approximation)", "Strategy 24: Gap-and-Go",
    "Strategy 25: Gap Fade", "Strategy 26: Turnaround Tuesday", "Strategy 27: Friday Afternoon Squeeze",
    "Strategy 28: Pivot Point Bounce", "Strategy 29: MTF RSI Alignment", "Strategy 30: Heikin Ashi Rider",
    "Strategy 31: Volatility Spike Fade", "Strategy 32: Mean Reversion (v2)",
    "Strategy 33: Yield Curve Regime Filter",    "Strategy 34: VIX Spike Mean Reversion",
    "Strategy 35: Monetary Policy Pivot",
    "Strategy 36: AI Meta-Ensemble",
    "Strategy 37: VWAP-Keltner Compression Breakout",
    "Portfolio: Average All Models",
    "AI Selective Master (Single Position)"
]

st.sidebar.markdown("<p style='font-size: 10px; font-weight: 800; color: #4b5563; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-left: 4px;'>Execution parameters</p>", unsafe_allow_html=True)
interval = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"], index=4)
col_s, col_e = st.sidebar.columns(2)
start_date = col_s.date_input("Start", datetime.date.today() - datetime.timedelta(days=365))
end_date = col_e.date_input("End", datetime.date.today())

selected_strategy = st.sidebar.selectbox("Active Model", strategy_options, index=strategy_options.index("Strategy 36: AI Meta-Ensemble") if "Strategy 36: AI Meta-Ensemble" in strategy_options else 0)

st.sidebar.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 10px; font-weight: 800; color: #4b5563; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-left: 4px;'>Capital Allocation</p>", unsafe_allow_html=True)
capital = st.sidebar.number_input("Vault Balance ($)", value=100000, step=1000)
risk_pc = st.sidebar.slider("Risk Exposure %", 0.1, 5.0, 1.0)

st.sidebar.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 10px; font-weight: 800; color: #4b5563; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-left: 4px;'>Trading Vehicle</p>", unsafe_allow_html=True)
trade_mode = st.sidebar.selectbox("Asset Class", ["Spot Equity (SPY)", "Options (Calls/Puts)"])

target_dte = 30
target_delta = 0.50
if trade_mode == "Options (Calls/Puts)":
    dt_c1, dt_c2 = st.sidebar.columns(2)
    target_dte = dt_c1.number_input("Target DTE", 1, 365, 30)
    target_delta = dt_c2.slider("Target Delta", 0.10, 0.90, 0.50, 0.05)


with st.sidebar.expander("🛡️ Global Safeguards"):
    g_sl = st.slider("Global Stop Loss %", 0.0, 10.0, 0.0, 0.5, help="Hard exit if loss exceeds this %")
    g_tp = st.slider("Global Take Profit %", 0.0, 20.0, 0.0, 0.5, help="Hard exit if profit exceeds this %")
    g_ts = st.slider("Trailing Stop %", 0.0, 10.0, 0.0, 0.5, help="Exit if price drops this % from peak")
    g_hold = st.number_input("Max Holding (Bars)", 0, 100, 0, help="Exit after fixed number of bars")

# Data Loading
@st.cache_data
def get_data(interval_val):
    # 1. Fetch SPY + VIX
    d_p, d_m, d_v = fetch_spy_data(interval=interval_val, years=12)
    
    # 2. Fetch Macro & Alt
    sentiment_df = get_insider_sentiment()
    macro_df = get_macro_context()
    
    # 3. Preprocess SPY Indicators
    df_combined = preprocess_data(d_p, d_m, d_v)
    
    # 4. Merge Macro Context
    df_combined = merge_macro_data(df_combined, macro_df)
    
    # 5. Merge Insider Sentiment (Existing logic)
    if not sentiment_df.empty:
        df_combined['temp_date'] = pd.to_datetime(df_combined.index.date)
        sentiment_df.index = pd.to_datetime(sentiment_df.index)
        idx_name = df_combined.index.name or 'Date'
        df_combined = df_combined.reset_index().merge(
            sentiment_df, left_on='temp_date', right_index=True, how='left'
        ).set_index(idx_name)
        df_combined['Insider_Sentiment'] = df_combined['Insider_Sentiment'].ffill().fillna(1.0)
        df_combined.drop(columns=['temp_date'], inplace=True)
    else:
        df_combined['Insider_Sentiment'] = 1.0
        
    return df_combined

try:
    df_all = get_data(interval)
    df = df_all.loc[(df_all.index.date >= start_date) & (df_all.index.date <= end_date)].copy()
except Exception as e:
    st.error(f"Engine Core Error: {e}"); st.stop()

EngineClass = OptionsBacktestEngine if trade_mode == "Options (Calls/Puts)" else BacktestEngine
engine_kwargs = {
    "initial_capital": capital, "risk_pc": risk_pc, 
    "global_stop_loss": g_sl, "global_take_profit": g_tp, 
    "trailing_stop": g_ts, "max_hold_bars": g_hold
}
if trade_mode == "Options (Calls/Puts)":
    engine_kwargs["target_dte"] = target_dte
    engine_kwargs["target_delta"] = target_delta

if st.sidebar.button("Retrain AI Model"):
    with st.spinner("Analyzing Market Patterns..."):
        temp_engine = EngineClass(df_all, **engine_kwargs)
        
        if "AI Meta-Ensemble" in selected_strategy or "AI Selective Master" in selected_strategy:
            # Training the Meta-Learner requires the Signal Matrix
            strategy_names = strategy_options[:-2] # All except Ensemble and Portfolio
            signal_df = temp_engine.get_all_signals(strategy_names)
            
            # Label trades from ALL strategies for broader learning
            all_trades = pd.concat([temp_engine.run_strategy(s)[0] for s in strategy_names])
            success, msg = st.session_state.ml_filter.train_ensemble(df_all, signal_df, all_trades)
        else:
            trades_for_training = pd.concat([temp_engine.run_strategy(s)[0] for s in strategy_options[:-2]]) if "Portfolio" in selected_strategy else temp_engine.run_strategy(selected_strategy)[0]
            success, msg = st.session_state.ml_filter.train(df_all, trades_for_training)
        
        if success: st.sidebar.success(msg)
        else: st.sidebar.warning(msg)

try:
    engine_kwargs["ml_filter"] = st.session_state.ml_filter
    engine = EngineClass(df, **engine_kwargs)
    collisions_count = 0
    if selected_strategy == "AI Selective Master (Single Position)":
        # 1. Check if trained Specifically for Ensemble
        if not getattr(st.session_state.ml_filter, 'is_ensemble_trained', False):
            st.warning("AI Meta-Ensemble must be trained before Selective Mode is available. Running Strategy 36 fallback.")
            trades_res, equity_res = engine.run_strategy("Strategy 36", use_ml=use_ml)
        else:
            trades_res, equity_res, collisions_count = engine.run_ai_selective_master(strategy_options)
    elif "Portfolio" in selected_strategy:
        # Exclude Strategy 36 (Ensemble), Portfolio, and Selective Master from the average
        base_strategies = [s for s in strategy_options if "Strategy" in s and "36" not in s]
        res = [engine.run_strategy(s, use_ml=use_ml) for s in base_strategies]
        trades_res = pd.concat([r[0] for r in res]).sort_values("Date In") if not all(r[0].empty for r in res) else pd.DataFrame()
        equity_res = pd.concat([r[1] for r in res], axis=1).mean(axis=1) if len(res) > 0 else pd.Series([capital]*len(df), index=df.index)
    else:
        trades_res, equity_res = engine.run_strategy(selected_strategy, use_ml=use_ml)
    
    metrics = engine._calculate_metrics(trades_res, equity_res)
except Exception as e:
    st.error(f"Execution Error in Mode: {selected_strategy}")
    st.exception(e)
    st.stop()

# --- TRADINGVIEW DATA FORMATTER ---
def format_tv_data(df_input):
    df_p = df_input.copy().reset_index()
    time_col = df_p.columns[0]
    
    if interval == "1d": 
        df_p['time'] = df_p[time_col].dt.strftime('%Y-%m-%d')
    else:
        df_p['time'] = df_p[time_col].apply(lambda x: int(x.timestamp()))
    
    # Price Group
    candlesticks = df_p[['time', 'Open', 'High', 'Low', 'Close']].rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'}).to_dict('records')
    sma20 = df_p[['time', 'SMA_20']].rename(columns={'SMA_20': 'value'}).dropna().to_dict('records')
    sma50 = df_p[['time', 'SMA_50']].rename(columns={'SMA_50': 'value'}).dropna().to_dict('records')
    mtf_s = df_p[['time', 'MTF_SMA_Short']].rename(columns={'MTF_SMA_Short': 'value'}).dropna().to_dict('records')
    mtf_l = df_p[['time', 'MTF_SMA_Long']].rename(columns={'MTF_SMA_Long': 'value'}).dropna().to_dict('records')
    
    # Volume Group
    volume = []
    for _, row in df_p.iterrows():
        color = 'rgba(0, 255, 163, 0.2)' if row['Close'] >= row['Open'] else 'rgba(255, 77, 77, 0.2)'
        volume.append({'time': row['time'], 'value': row['Volume'], 'color': color})
    
    # Sentiment Group
    sentiment = df_p[['time', 'Insider_Sentiment']].rename(columns={'Insider_Sentiment': 'value'}).to_dict('records')
        
    return candlesticks, sma20, sma50, mtf_s, mtf_l, volume, sentiment

# --- DASHBOARD UI ---
st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 2.5rem; padding-top: 1rem;'>
    <div>
        <div style='display: flex; align-items: center; gap: 10px; margin-bottom: 6px;'>
            <span style='background: rgba(10, 132, 255, 0.1); color: #0A84FF; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px;'>Protected Session</span>
            <span style='color: #98989D; font-size: 11px; font-weight: 500;'>{datetime.datetime.now().strftime('%H:%M:%S')} UTC</span>
        </div>
        <h1 style='font-size: 32px; font-weight: 700; color: #F2F2F7; letter-spacing: -1px; margin: 0; line-height: 1.1;'>Trading <span style='color: #0A84FF;'>Dashboard</span></h1>
        <p style='font-size: 14px; color: #98989D; margin-top: 6px; font-weight: 400;'>{selected_strategy}</p>
    </div>
    <div style='display: flex; align-items: center; gap: 24px;'>
        <div style='text-align: right;'>
            <p style='font-size: 10px; font-weight: 700; color: #4b5563; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px;'>Auth Profile</p>
            <div style='display: flex; align-items: center; gap: 12px;'>
                <div style='text-align: right;'>
                    <p style='font-size: 14px; font-weight: 600; color: #F2F2F7; margin: 0;'>Standard User</p>
                    <p style='font-size: 11px; font-weight: 500; color: #0A84FF; margin: 0;'>Institutional Tier</p>
                </div>
                <div style='width: 42px; height: 42px; border-radius: 12px; background: #2C2C2E; border: 1px solid rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

def draw_metric(label, value, delta, is_pos=True, trend_data=None):
    delta_color = "#34C759" if is_pos else "#FF3B30"
    st.markdown(f"""
        <div class="glass-card">
            <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;'>
                <p style='color: #98989D; font-size: 12px; font-weight: 500; margin: 0;'>{label}</p>
                <div style='background: rgba(255, 255, 255, 0.05); padding: 5px; border-radius: 8px;'>
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#98989D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
                </div>
            </div>
            <div style='display: flex; align-items: flex-end; gap: 10px;'>
                <h3 style='color: #F2F2F7; font-size: 26px; font-weight: 600; margin: 0; letter-spacing: -0.5px;'>{value}</h3>
                <span style='color: {delta_color}; font-size: 13px; font-weight: 500; margin-bottom: 4px; background: rgba({ "52, 199, 89" if is_pos else "255, 59, 48" }, 0.1); padding: 2px 6px; border-radius: 4px;'>{delta}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Main Performance Bar
with st.container():
    kp1, kp2, kp3, kp4, kp5 = st.columns(5)
    
    with kp1: draw_metric("Return Profile", f"{metrics['Total Return %']}%", f"+{metrics['Expectancy']}")
    with kp2: draw_metric("Risk Exposure", f"{metrics['Max Drawdown %']}%", "Optimal", is_pos=True)
    with kp3: draw_metric("Hit Rate", f"{metrics['Win Rate %']}%", "Stable")
    with kp4: 
        if selected_strategy == "AI Selective Master (Single Position)":
            draw_metric("AI Filter", collisions_count, "Active")
        else:
            draw_metric("Profit Alpha", metrics['Profit Factor'], "High")
    with kp5: draw_metric("Sharpe Index", metrics['Sharpe Ratio'], "Tier 1")
    
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# Institutional Ticker Row
t1, t2, t3, t4 = st.columns(4)
def draw_ticker(symbol, name, price, change, is_pos=True):
    color = "#34C759" if is_pos else "#FF3B30"
    st.markdown(f"""
        <div class="glass-card">
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;'>
                <span style='color: #F2F2F7; font-weight: 600; font-size: 16px; letter-spacing: -0.5px;'>{symbol}</span>
                <div style='display: flex; align-items: center; gap: 4px; background: rgba({ "52, 199, 89" if is_pos else "255, 59, 48" }, 0.1); padding: 2px 6px; border-radius: 4px;'>
                    <span style='color: {color}; font-size: 12px; font-weight: 600;'>{change}</span>
                    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="{ "m5 12 7-7 7 7" if is_pos else "m19 12-7 7-7-7" }"/><path d="{ "M12 19V5" if is_pos else "M12 5v14" }"/></svg>
                </div>
            </div>
            <p style='color: #98989D; font-size: 11px; font-weight: 500; margin-bottom: 12px;'>{name}</p>
            <h4 style='color: #F2F2F7; font-size: 22px; font-weight: 600; margin: 0;'>${price}</h4>
        </div>
    """, unsafe_allow_html=True)

with t1: draw_ticker("SPY", "S&P 500 ETF", f"{df['Close'].iloc[-1]:.2f}", "+1.45%")
with t2: draw_ticker("QQQ", "NASDAQ 100", "442.10", "+2.10%")
with t3: draw_ticker("DIA", "DOW JONES", "389.50", "+0.85%")
with t4: draw_ticker("IWM", "RUSSELL 2000", "204.30", "-0.32%", is_pos=False)

st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)

# ---- MAIN CHART & AI ROW ----
main_col, ai_col = st.columns([2.8, 1.2])

with main_col:
    st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>Interactive Price Action & Alpha Execution</p>", unsafe_allow_html=True)
    c, s20, s50, m1, m2, v, sent = format_tv_data(df)
    
    markers = []
    if not trades_res.empty:
        for _, trade in trades_res.iterrows():
            t_in = trade['Date In'].strftime('%Y-%m-%d') if interval == "1d" else int(trade['Date In'].timestamp())
            t_out = trade['Date Out'].strftime('%Y-%m-%d') if interval == "1d" else int(trade['Date Out'].timestamp())
            
            # Use Strategy ID if available
            strat_id = ""
            if 'Strategy' in trade: strat_id = f"[{trade['Strategy'].split(' ')[-1]}] "
                
            markers.append({'time': t_in, 'position': 'belowBar', 'color': '#34C759', 'shape': 'arrowUp', 'text': f"{strat_id}BUY @ {trade['Entry Price']}"})
            markers.append({'time': t_out, 'position': 'aboveBar', 'color': '#FF3B30', 'shape': 'arrowDown', 'text': f"SELL @ {trade['Exit Price']}"})
    
    chart_options = {
        "layout": { "background": { "type": "solid", "color": "#1C1C1E" }, "textColor": "#98989D" },
        "grid": { "vertLines": { "color": "rgba(31, 41, 55, 0.5)" }, "horzLines": { "color": "rgba(31, 41, 55, 0.5)" } },
        "rightPriceScale": { "borderVisible": False, "scaleMargins": { "top": 0.1, "bottom": 0.3 } },
        "overlayPriceScales": { "scaleMargins": { "top": 0.7, "bottom": 0.1 } }, 
        "crosshair": { "mode": 0, "vertLine": {"color": "#48484A"}, "horzLine": {"color": "#48484A"} },
        "timeScale": { "borderVisible": False, "timeVisible": True },
        "watermark": {
            "visible": True, "fontSize": 20, "horzAlign": 'center', "vertAlign": 'center', "color": 'rgba(255, 255, 255, 0.03)',
            "text": f"QUANT OS // {interval.upper()} VIEW",
        },
        "height": 600
    }
    
    series_data = [
        {"type": "Candlestick", "data": c, "options": {"upColor": "#34C759", "downColor": "#FF3B30", "borderVisible": False, "wickUpColor": "#34C759", "wickDownColor": "#FF3B30"}, "markers": markers},
        {"type": "Line", "data": s20, "options": {"color": "#34C759", "lineWidth": 1, "opacity": 0.4}},
        {"type": "Line", "data": s50, "options": {"color": "#0A84FF", "lineWidth": 1, "opacity": 0.4}},
        {"type": "Line", "data": m1, "options": {"color": "#FF3B30", "lineWidth": 1, "lineStyle": 2, "opacity": 0.3}},
        {"type": "Line", "data": m2, "options": {"color": "#34C759", "lineWidth": 1, "lineStyle": 2, "opacity": 0.3}},
        {"type": "Histogram", "data": v, "options": {"color": "rgba(152, 152, 157, 0.2)", "priceFormat": {"type": "volume"}, "priceScaleId": "volume"}},
        {"type": "Area", "data": sent, "options": {"topColor": "rgba(52, 199, 89, 0.2)", "bottomColor": "rgba(52, 199, 89, 0.0)", "lineColor": "#34C759", "lineWidth": 2, "priceScaleId": "sentiment"}}
    ]
    
    if c:
        renderLightweightCharts([{"chart": chart_options, "series": series_data}], 'main_tv_chart')
    else:
        st.info("Insufficient data for the selected period.")

with ai_col:
    if st.session_state.ml_filter.is_trained:
        st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>AI Engine Diagnostics</p>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="glass-card" style='text-align: center; border-left: 4px solid #34C759; margin-bottom: 10px;'>
            <p style='color: #98989D; font-size: 11px; font-weight: 700; margin-bottom: 8px;'>AI RELIABILITY SCORE</p>
            <h1 style='color: #34C759; margin: 0; font-family: "JetBrains Mono"; font-size: 42px;'>{st.session_state.ml_filter.reliability_score:.1%}</h1>
            <p style='color: #98989D; font-size: 11px; margin-top: 10px;'>Active Model Confidence Matrix</p>
        </div>
        """, unsafe_allow_html=True)
        
        regime_preds = st.session_state.ml_filter.regime_detector.predict(engine.df)
        regimes = pd.Series(regime_preds).value_counts()
        fig_pie = go.Figure(data=[go.Pie(labels=regimes.index, values=regimes.values, hole=.7, marker=dict(colors=['#34C759', '#0A84FF', '#2C2C2E', '#98989D']))])
        fig_pie.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        is_ensemble = "Meta-Ensemble" in selected_strategy or "Selective" in selected_strategy
        importance = st.session_state.ml_filter.get_feature_importance(use_ensemble=is_ensemble)
        if importance:
            imp_df = pd.DataFrame(list(importance.items()), columns=['Feature', 'Val']).sort_values('Val', ascending=True).tail(5)
            fig_imp = go.Figure(go.Bar(x=imp_df['Val'], y=imp_df['Feature'], orientation='h', marker_color='#34C759', marker_line_color='#1C1C1E', marker_line_width=1))
            fig_imp.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False))
            st.plotly_chart(fig_imp, use_container_width=True)
    else:
        st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>AI Engine Diagnostics</p>", unsafe_allow_html=True)
        st.info("Retrain the ML model (Strategy 36) to view active real-time AI context.")

st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)

# ---- ROW 2: EQUITY CURVE AND LOG ----
eq_col, log_col = st.columns([1.5, 1])

with eq_col:
    st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>Equity Curve & Drawdown</p>", unsafe_allow_html=True)
    fig_perf = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
    fig_perf.add_trace(go.Scatter(x=equity_res.index, y=equity_res, fill='tozeroy', line=dict(color='#34C759', width=2), name='Equity', fillcolor='rgba(52, 199, 89, 0.1)'), row=1, col=1)
    rolling_max = equity_res.cummax()
    dd_pc = ((equity_res - rolling_max) / rolling_max) * 100
    fig_perf.add_trace(go.Scatter(x=dd_pc.index, y=dd_pc, fill='tozeroy', line=dict(color='#FF3B30', width=1), name='DD %', fillcolor='rgba(255, 59, 48, 0.1)'), row=2, col=1)
    
    fig_perf.update_layout(
        height=400, template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0,r=0,t=0,b=0), font=dict(family="Plus Jakarta Sans", size=10),
        xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(gridcolor='rgba(255,255,255,0.05)', zeroline=False),
        yaxis2=dict(gridcolor='rgba(255,255,255,0.05)', zeroline=False)
    )
    st.plotly_chart(fig_perf, use_container_width=True)

with log_col:
    st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>Interactive Execution Log</p>", unsafe_allow_html=True)
    if not trades_res.empty:
        df_display = trades_res[['Date In', 'Date Out', 'Type', 'Entry Price', 'Exit Price', 'PnL %']].copy().iloc[::-1]
        st.dataframe(df_display, use_container_width=True, height=400)
    else:
        st.info("No trades executed.")

st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)

# ---- ROW 3: HEATMAP AND VIOLIN ----
heat_col, vio_col = st.columns(2)

with heat_col:
    st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>Returns Heatmap</p>", unsafe_allow_html=True)
    try:
        m_returns = equity_res.resample('ME').last().pct_change() * 100
        m_df = m_returns.to_frame('Return')
        m_df['Year'], m_df['Month'] = m_df.index.year, m_df.index.strftime('%b')
        pivot_df = m_df.pivot(index='Year', columns='Month', values='Return')
        mo = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        pivot_df = pivot_df.reindex(columns=[m for m in mo if m in pivot_df.columns])
        fig_heat = go.Figure(go.Heatmap(z=pivot_df.values, x=pivot_df.columns, y=pivot_df.index, colorscale=[[0, '#FF3B30'], [0.5, '#2C2C2E'], [1, '#34C759']], zmid=0, text=np.round(pivot_df.values, 1), texttemplate="%{text}%"))
        fig_heat.update_layout(template='plotly_dark', height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_heat, use_container_width=True)
    except: st.info("Profile pending...")

with vio_col:
    st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>Trade PnL Distribution</p>", unsafe_allow_html=True)
    if not trades_res.empty:
        fig_vio = go.Figure(go.Violin(y=trades_res['PnL %'], box_visible=True, points='all', fillcolor='rgba(52, 199, 89, 0.4)', line_color='#34C759'))
        fig_vio.update_layout(template='plotly_dark', height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_vio, use_container_width=True)
    else:
        st.info("No distribution data available.")

st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)

# ---- ROW 4: MACRO ----
if 'T10Y2Y' in df.columns:
    st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>Global Macro Conditions</p>", unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    with m1:
        fig_yc = go.Figure()
        fig_yc.add_trace(go.Scatter(x=df.index, y=df['T10Y2Y'], name="Spread", fill='tozeroy', line=dict(color='#34C759'), fillcolor='rgba(52, 199, 89, 0.05)'))
        fig_yc.add_hline(y=0, line_dash="dash", line_color="#FF3B30")
        fig_yc.update_layout(title="Yield Curve Strategy Filter", height=300, template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig_yc, use_container_width=True)
    with m2:
        fig_fed = go.Figure()
        fig_fed.add_trace(go.Scatter(x=df.index, y=df['FEDFUNDS'], name="Rate", line=dict(color='#0A84FF', width=2)))
        fig_fed.update_layout(title="Monetary Policy Regime", height=300, template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig_fed, use_container_width=True)

# ---- ROW 5: ENSEMBLE VIEW (if trained) ----
if hasattr(st.session_state.ml_filter, 'trust_scores') and st.session_state.ml_filter.is_trained:
    st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)
    e_c1, e_c2 = st.columns([2, 1])
    with e_c1:
        st.markdown("<p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 1rem;'>Ensemble Trust Hierarchy</p>", unsafe_allow_html=True)
        trust_df = pd.DataFrame(list(st.session_state.ml_filter.trust_scores.items()), columns=['Strat', 'Weight']).sort_values('Weight', ascending=True).tail(15)
        fig_trust = go.Figure(go.Bar(x=trust_df['Weight'], y=trust_df['Strat'], orientation='h', marker=dict(color=trust_df['Weight'], colorscale=[[0, '#2C2C2E'], [1, '#34C759']], line=dict(color='#1C1C1E', width=1))))
        fig_trust.update_layout(height=400, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_trust, use_container_width=True)
    
    with e_c2:
        st.markdown(f"""
            <div class='glass-card' style='border-top: 4px solid #34C759; height: 100%;'>
                <p style='font-size: 11px; font-weight: 800; color: #98989D; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 1rem;'>Intelligence Consensus</p>
                <p style='font-size: 13px; color: #F2F2F7; line-height: 1.6;'>
                    The **Trust Hierarchy** visualizes the AI Meta-Ensemble's internal weighting system. 
                    Strategies with higher weights have demonstrated superior predictive alpha in the current market regime.
                </p>
                <div style='margin-top: 2rem;'>
                    <p style='font-size: 10px; color: #98989D; text-transform: uppercase; font-weight: 700;'>Base Reliability</p>
                    <h2 style='color: #34C759; font-family: "JetBrains Mono"; margin: 0;'>{st.session_state.ml_filter.reliability_score:.1%}</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height: 4rem;'></div>", unsafe_allow_html=True)
f_c1, f_c2 = st.columns([1, 1])
f_c1.markdown(f"<span style='color: #48484A; font-size: 10px; font-weight: 600; letter-spacing: 1px;'>TERMINAL_ID: {datetime.datetime.now().strftime('%Y%m%d-%H%M')} // AES-256</span>", unsafe_allow_html=True)
f_c2.markdown("<p style='text-align: right; color: #48484A; font-size: 10px; font-weight: 600; letter-spacing: 1px;'>DESIGNED BY FINX SYSTEMS // V4.2.0-STABLE</p>", unsafe_allow_html=True)

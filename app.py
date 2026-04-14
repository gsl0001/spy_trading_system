import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data import fetch_spy_data, preprocess_data, merge_macro_data
from strategies import BacktestEngine
from ml_engine import MLEnsembleFilter
from sentiment import get_insider_sentiment
from macro_engine import get_macro_context
from streamlit_lightweight_charts import renderLightweightCharts
import datetime

# Page Config
st.set_page_config(page_title="SPY AI Quant Workstation", layout="wide", initial_sidebar_state="expanded")

# --- PREMIUM UI STYLE SETUP ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
    /* Global Overrides */
    body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        color: #e6edf3;
    }
    
    .main {
        background: radial-gradient(circle at top right, #0a0b1e, #040406);
        color: #e6edf3;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #06070a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Metric Card Glassmorphism */
    div.stMetric {
        background: rgba(18, 18, 24, 0.7);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 20px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease-out;
    }
    
    div.stMetric:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 251, 255, 0.4);
        box-shadow: 0 8px 30px rgba(0, 251, 255, 0.1);
    }
    
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px !important;
        color: #00fbff !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.6) !important;
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(18, 18, 24, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 6px 6px 0 0;
        padding: 10px 20px;
        color: rgba(255, 255, 255, 0.6);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 251, 255, 0.1) !important;
        border-color: rgba(0, 251, 255, 0.3) !important;
        color: #00fbff !important;
    }

    /* Ticker/Status Effect */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-live { background-color: #00ff88; box-shadow: 0 0 10px #00ff88; }
    .status-closed { background-color: #ff3a60; }
</style>
""", unsafe_allow_html=True)

if 'ml_filter' not in st.session_state:
    st.session_state.ml_filter = MLEnsembleFilter()

# Sidebar
st.sidebar.markdown("""
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 20px;'>
        <img src="https://img.icons8.com/nolan/64/bullish.png" width="48"/>
        <h1 style='font-size: 20px; font-weight: 700; margin: 0;'>QUANT ENGINE</h1>
    </div>
""", unsafe_allow_html=True)

# Market Status Indicator
is_live = datetime.datetime.now().hour >= 9 and datetime.datetime.now().hour < 16 # Simple proxy
st.sidebar.markdown(f"""
    <div style='background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border-left: 3px solid {"#00ff88" if is_live else "#ff3a60"}; margin-bottom: 20px;'>
        <span class='status-indicator {"status-live" if is_live else "status-closed"}'></span>
        <span style='font-size: 11px; font-weight: 600; text-transform: uppercase;'>Market Status: {"LIVE" if is_live else "CLOSED"}</span>
    </div>
""", unsafe_allow_html=True)

st.sidebar.subheader("🤖 Intelligence Layer")
use_ml = st.sidebar.toggle("XGBoost Signal Filter", value=False)
ml_conf = st.sidebar.slider("AI Confidence Threshold", 0.4, 0.7, 0.5, 0.05)
st.session_state.ml_filter.confidence_threshold = ml_conf

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Parameters")
interval = st.sidebar.selectbox("Data Interval", ["1m", "5m", "15m", "1h", "1d"], index=4)
lookback_info = {"1m": "7 Days", "5m": "60 Days", "15m": "60 Days", "1h": "730 Days", "1d": "12 Years"}
st.sidebar.caption(f"Max History: {lookback_info.get(interval)}")

col_s, col_e = st.sidebar.columns(2)
start_date = col_s.date_input("Start", datetime.date.today() - datetime.timedelta(days=7 if interval=="1m" else 30 if interval=="5m" else 365))
end_date = col_e.date_input("End", datetime.date.today())

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
    "Portfolio: Average All Models",
    "AI Selective Master (Single Position)"
]
selected_strategy = st.sidebar.selectbox("Active Strategy", strategy_options)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Risk & Execution Control")
capital = st.sidebar.number_input("Starting Capital ($)", value=100000, step=1000)
risk_pc = st.sidebar.slider("Risk Per Trade %", 0.1, 5.0, 1.0)

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

if st.sidebar.button("Retrain AI Model"):
    with st.spinner("Analyzing Market Patterns..."):
        temp_engine = BacktestEngine(df_all, initial_capital=capital, risk_pc=risk_pc, 
                                     global_stop_loss=g_sl, global_take_profit=g_tp, trailing_stop=g_ts, max_hold_bars=g_hold)
        
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
    engine = BacktestEngine(df, initial_capital=capital, risk_pc=risk_pc, ml_filter=st.session_state.ml_filter,
                            global_stop_loss=g_sl, global_take_profit=g_tp, trailing_stop=g_ts, max_hold_bars=g_hold)
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
        color = 'rgba(0, 150, 136, 0.4)' if row['Close'] >= row['Open'] else 'rgba(255, 82, 82, 0.4)'
        volume.append({'time': row['time'], 'value': row['Volume'], 'color': color})
    
    # Sentiment Group
    sentiment = df_p[['time', 'Insider_Sentiment']].rename(columns={'Insider_Sentiment': 'value'}).to_dict('records')
        
    return candlesticks, sma20, sma50, mtf_s, mtf_l, volume, sentiment

# --- DASHBOARD UI ---
st.markdown("<h1 style='letter-spacing: -1px; font-weight: 800; color: #fff;'>STATISTICAL ARBITRAGE TERMINAL v4.2</h1>", unsafe_allow_html=True)

# Main Performance Bar
with st.container():
    st.markdown("<div style='margin-bottom: 25px;'>", unsafe_allow_html=True)
    kp1, kp2, kp3, kp4, kp5, kp6 = st.columns(6)
    
    with kp1: st.metric("TOTAL RETURN", f"{metrics['Total Return %']}%", f"{metrics['Expectancy']} exp")
    with kp2: st.metric("MAX DRAWDOWN", f"{metrics['Max Drawdown %']}%", delta_color="inverse")
    with kp3: st.metric("WIN RATE", f"{metrics['Win Rate %']}%")
    with kp4: 
        if selected_strategy == "AI Selective Master (Single Position)":
            st.metric("COLLISION SQUELCH", collisions_count, "Clean Execution")
        else:
            st.metric("PROFIT FACTOR", metrics['Profit Factor'])
    with kp5: st.metric("SHARPE RATIO", metrics['Sharpe Ratio'])
    
    # Insider Metric
    current_bias = df['Insider_Sentiment'].iloc[-1] if 'Insider_Sentiment' in df.columns else 1.0
    bias_label = "ACCELERATING" if current_bias > 1.1 else "NEUTRAL" if current_bias > 0.9 else "DECELERATING"
    with kp6: st.metric("INSIDER MOMENTUM", bias_label, f"{round(current_bias, 3)}x")
    st.markdown("</div>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Performance Executive", "📑 Detailed Log", "🌍 Global Macro", "🧠 Ensemble Brain"])

with tab1:
    c, s20, s50, m1, m2, v, sent = format_tv_data(df)
    
    markers = []
    if not trades_res.empty:
        for _, trade in trades_res.iterrows():
            t_in = trade['Date In'].strftime('%Y-%m-%d') if interval == "1d" else int(trade['Date In'].timestamp())
            t_out = trade['Date Out'].strftime('%Y-%m-%d') if interval == "1d" else int(trade['Date Out'].timestamp())
            
            # Use Strategy ID if available (from Selective Master or individual tags)
            strat_id = ""
            if 'Strategy' in trade: 
                strat_id = f"[{trade['Strategy'].split(' ')[-1]}] "
            elif 'strat_name' in trade:
                strat_id = f"[{trade['strat_name'].split(' ')[-1]}] "
                
            markers.append({'time': t_in, 'position': 'belowBar', 'color': '#2196f3', 'shape': 'arrowUp', 'text': f"{strat_id}BUY @ {trade['Entry Price']}"})
            markers.append({'time': t_out, 'position': 'aboveBar', 'color': '#e91e63', 'shape': 'arrowDown', 'text': f"SELL @ {trade['Exit Price']}"})
    
    chart_options = {
        "layout": { "background": { "type": "solid", "color": "#040406" }, "textColor": "rgba(255, 255, 255, 0.9)" },
        "grid": { "vertLines": { "color": "rgba(42, 46, 57, 0.1)" }, "horzLines": { "color": "rgba(42, 46, 57, 0.1)" } },
        "rightPriceScale": { "borderVisible": False, "scaleMargins": { "top": 0.1, "bottom": 0.4 } },
        "overlayPriceScales": { "scaleMargins": { "top": 0.65, "bottom": 0.15 } }, 
        "crosshair": { "mode": 0 },
        "timeScale": { "borderVisible": False, "timeVisible": True },
        "watermark": {
            "visible": True, "fontSize": 18, "horzAlign": 'center', "vertAlign": 'center', "color": 'rgba(0, 251, 255, 0.1)',
            "text": f"SPY {interval.upper()} // STATISTICAL TERMINAL",
        },
        "height": 700
    }
    
    series_data = [
        {"type": "Candlestick", "data": c, "options": {"upColor": "#26a69a", "downColor": "#ef5350", "borderVisible": False, "wickUpColor": "#26a69a", "wickDownColor": "#ef5350"}, "markers": markers},
        {"type": "Line", "data": s20, "options": {"color": "#ff9f43", "lineWidth": 1}},
        {"type": "Line", "data": s50, "options": {"color": "#54a0ff", "lineWidth": 1}},
        {"type": "Line", "data": m1, "options": {"color": "#ff6b6b", "lineWidth": 1, "lineStyle": 2}},
        {"type": "Line", "data": m2, "options": {"color": "#1dd1a1", "lineWidth": 1, "lineStyle": 2}},
        {
            "type": "Histogram", "data": v, 
            "options": {"color": "#2196f3", "priceFormat": {"type": "volume"}, "priceScaleId": "volume"}, # Volume in middle-ish
            "priceScale": { "scaleMargins": { "top": 0.65, "bottom": 0.2 } }
        },
        {
            "type": "Area", "data": sent, 
            "options": {
                "topColor": "rgba(171, 71, 188, 0.4)", "bottomColor": "rgba(171, 71, 188, 0.0)", 
                "lineColor": "rgba(171, 71, 188, 1)", "lineWidth": 2, "priceScaleId": "sentiment"
            },
            "priceScale": { "scaleMargins": { "top": 0.82, "bottom": 0 } } # Sentiment at bottom
        }
    ]
    
    if c:
        renderLightweightCharts([{"chart": chart_options, "series": series_data}], 'main_tv_chart')
    else:
        st.info("Insufficient data for the selected period. Expand your date range.")
    
    st.subheader("Interactive execution Log")
    st.dataframe(
        trades_res[['Date In', 'Date Out', 'Type', 'Entry Price', 'Exit Price', 'PnL', 'PnL %']].iloc[::-1] if not trades_res.empty else pd.DataFrame(),
        selection_mode="single-row", width="stretch"
    )

with tab2:
    st.subheader("Performance Intelligence")
    fig_perf = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_width=[0.3, 0.7])
    fig_perf.add_trace(go.Scatter(x=equity_res.index, y=equity_res, fill='tozeroy', line=dict(color='#00d4ff', width=3), name='Equity Curve'), row=1, col=1)
    rolling_max = equity_res.cummax()
    dd_pc = ((equity_res - rolling_max) / rolling_max) * 100
    fig_perf.add_trace(go.Scatter(x=dd_pc.index, y=dd_pc, fill='tozeroy', line=dict(color='#ff4d4d', width=1), name='Drawdown %'), row=2, col=1)
    fig_perf.update_layout(
        height=500, 
        template='plotly_dark', 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0,r=0,t=20,b=0),
        font=dict(family="Inter")
    )
    st.plotly_chart(fig_perf, width="stretch")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Monthly Returns Profile")
        try:
            m_returns = equity_res.resample('ME').last().pct_change() * 100
            m_df = m_returns.to_frame('Return')
            m_df['Year'], m_df['Month'] = m_df.index.year, m_df.index.strftime('%b')
            pivot_df = m_df.pivot(index='Year', columns='Month', values='Return')
            mo = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            pivot_df = pivot_df.reindex(columns=[m for m in mo if m in pivot_df.columns])
            fig_heat = go.Figure(go.Heatmap(z=pivot_df.values, x=pivot_df.columns, y=pivot_df.index, colorscale='RdYlGn', text=np.round(pivot_df.values, 1), texttemplate="%{text}%"))
            fig_heat.update_layout(
                template='plotly_dark', 
                height=400, 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0,r=0,t=20,b=0),
                font=dict(family="Inter")
            )
            st.plotly_chart(fig_heat, width="stretch")
        except: st.info("More historical data needed for profiling.")
    
    with c2:
        st.subheader("Trade Return Distribution")
        if not trades_res.empty:
            fig_vio = go.Figure(go.Violin(y=trades_res['PnL %'], box_visible=True, points='all', fillcolor='#00fbff', opacity=0.6))
            fig_vio.update_layout(
                template='plotly_dark', 
                height=400, 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0,r=0,t=20,b=0),
                font=dict(family="Inter")
            )
            st.plotly_chart(fig_vio, width="stretch")
    
    st.subheader("Institutional Risk Metrics")
    st.table(pd.DataFrame({
        "Metric": ["Expectancy ($)", "Sortino Ratio", "Recovery Factor", "Payoff Ratio"], 
        "Value": [round(metrics['Expectancy'],2), round(metrics['Sortino Ratio'],2), round(metrics['Recovery Factor'],2), round(metrics['Payoff Ratio'],2)]
    }))

with tab3:
    st.markdown("### 🌍 Global Macro Framework")
    st.info("Institutional filters based on US Yield Curve and Monetary Policy bias.")
    
    if 'T10Y2Y' in df.columns:
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            fig_yc = go.Figure()
            fig_yc.add_trace(go.Scatter(x=df.index, y=df['T10Y2Y'], name="10Y-2Y Spread", fill='tozeroy', line=dict(color='#00fbff')))
            fig_yc.add_hline(y=0, line_dash="dash", line_color="red")
            fig_yc.update_layout(title="Yield Curve (Recession Monitor)", height=400, template="plotly_dark", 
                               plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_yc, width='stretch')
            
        with m_col2:
            fig_fed = go.Figure()
            fig_fed.add_trace(go.Scatter(x=df.index, y=df['FEDFUNDS'], name="Fed Funds Rate", line=dict(color='#ff9f43', width=3)))
            fig_fed.update_layout(title="Federal Funds Effective Rate", height=400, template="plotly_dark",
                                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_fed, width='stretch')
            
        st.markdown("---")
        st.markdown("#### Macro Opportunity Score")
        yield_status = "⚠️ INVERTED (High Recession Risk)" if df['T10Y2Y'].iloc[-1] < 0 else "✅ NORMAL (Growth Environment)"
        fed_status = "🔴 TIGHTENING" if df['Fed_Policy_Bias'].iloc[-1] > 0 else "🟢 EASING/STABLE"
        c1, c2 = st.columns(2)
        c1.write(f"**Yield Regime:** {yield_status}")
        c2.write(f"**Fed Policy:** {fed_status}")
    else:
        st.warning("Macro data not available in currently selected time window.")

# --- Model Intelligence Section (Global) ---
if st.session_state.ml_filter.is_trained:
    st.markdown("---")
    st.subheader("🤖 Model Intelligence Overlay")
    m_col1, m_col2 = st.columns([1, 2])
    with m_col1:
        st.markdown(f"""
        <div style='background: rgba(0, 212, 255, 0.05); padding: 20px; border-radius: 12px; border: 1px solid rgba(0, 212, 255, 0.2); text-align: center;'>
            <p style='color: rgba(255,255,255,0.6); font-size: 14px; margin-bottom: 5px;'>RELIABILITY SCORE</p>
            <h1 style='color: #00d4ff; margin: 0;'>{st.session_state.ml_filter.reliability_score:.1%}</h1>
            <p style='font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 10px;'>Cross-Validated Accuracy</p>
        </div>
        """, unsafe_allow_html=True)
        regimes = engine.df['Market_Regime'].value_counts()
        regime_names = {0: "Low Vol Bull", 1: "High Vol Bull", 2: "Low Vol Bear", 3: "High Vol Bear"}
        fig_pie = go.Figure(data=[go.Pie(labels=[regime_names.get(i, f"Regime {i}") for i in regimes.index], values=regimes.values, hole=.6)])
        fig_pie.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', showlegend=True)
        st.plotly_chart(fig_pie, width='stretch')
    with m_col2:
        st.markdown("<p style='color: rgba(255,255,255,0.6); font-size: 14px; margin-bottom: 5px;'>FEATURE PRIORITY (WHAT THE AI IS WATCHING)</p>", unsafe_allow_html=True)
        importance = st.session_state.ml_filter.get_feature_importance()
        if importance:
            imp_df = pd.DataFrame(list(importance.items()), columns=['Feature', 'Importance']).sort_values('Importance', ascending=True)
            fig_imp = go.Figure(go.Bar(x=imp_df['Importance'], y=imp_df['Feature'], orientation='h', marker_color='#00d4ff'))
            fig_imp.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0), template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
            st.plotly_chart(fig_imp, use_container_width=True)

with tab4:
    st.markdown("### 🧠 AI Ensemble Intelligence")
    if not hasattr(st.session_state.ml_filter, 'trust_scores') or not st.session_state.ml_filter.is_trained:
        st.info("Retrain the model while 'Strategy 36: AI Meta-Ensemble' is selected to view ensemble weights.")
    else:
        e_col1, e_col2 = st.columns([2, 1])
        with e_col1:
            st.subheader("Strategy Trust Hierarchy")
            trust_df = pd.DataFrame(list(st.session_state.ml_filter.trust_scores.items()), columns=['Strategy', 'AI Weight']).sort_values('AI Weight', ascending=True)
            if not trust_df.empty:
                fig_trust = go.Figure(go.Bar(x=trust_df['AI Weight'], y=trust_df['Strategy'], orientation='h', marker_color='#00fbff'))
                fig_trust.update_layout(height=600, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_trust, width='stretch')
            else:
                st.warning("No strategy weights available yet. Ensure the ensemble was trained on multiple signals.")
        
        with e_col2:
            st.subheader("Consensus Heatmap")
            st.markdown("""
            This tab shows the AI's internal logic for the Meta-Ensemble. 
            The **Trust Hierarchy** indicates which strategies the AI relies on most in the current market regime. 
            High weights mean the strategy has proven consistent in similar historical conditions.
            """)
            st.metric("Model Reliability", f"{st.session_state.ml_filter.reliability_score:.1%}")
            st.metric("Active Model Input", "35 Strategies")

st.markdown("---")
col_f1, col_f2 = st.columns([1, 1])
col_f1.markdown(f"<span style='color: rgba(255,255,255,0.3); font-size: 11px;'>TERMINAL_ID: {datetime.datetime.now().strftime('%Y%m%d-%H%M')} | ENCRYPTION: AES-256</span>", unsafe_allow_html=True)
col_f2.markdown("<p style='text-align: right; color: rgba(255,255,255,0.3); font-size: 11px;'>DESIGNED BY ANTIGRAVITY // QUANT_SKILLS_V1.0</p>", unsafe_allow_html=True)

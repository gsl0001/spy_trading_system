import yfinance as yf
import pandas as pd
import numpy as np

def fetch_spy_data(interval="1d", years=10):
    """Fetch historical SPY data and VIX context."""
    ticker = "SPY"
    
    # Mapping for Dynamic MTF
    mtf_map = {
        "1m": "15m", "5m": "60m", "15m": "1d", "60m": "1d", "1h": "1d", "1d": "1wk"
    }
    mtf_interval = mtf_map.get(interval, "1wk")
    
    if interval == "1m": period = "7d"
    elif interval in ["5m", "15m"]: period = "60d"
    elif interval in ["60m", "1h"]: period = "730d"
    else: period = f"{years}y"

    df_primary = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
    df_mtf = yf.download(ticker, period=period, interval=mtf_interval, auto_adjust=True)
    df_vix = yf.download("^VIX", period=period, interval=interval if interval != "1m" else "5m", auto_adjust=True)
    
    if df_primary.empty:
        raise ValueError(f"No data fetched for interval {interval}.")

    for d in [df_primary, df_mtf, df_vix]:
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
            
    return df_primary, df_mtf, df_vix

def merge_macro_data(df, macro_df):
    """Integrates low-frequency macro data into the primary backtesting dataframe."""
    if macro_df is None or macro_df.empty:
        return df
        
    df['temp_date'] = pd.to_datetime(df.index.date)
    macro_df.index = pd.to_datetime(macro_df.index)
    
    # Use a dynamic index name to support both Date and Datetime
    idx_name = df.index.name or 'Date'
    
    df = df.reset_index().merge(
        macro_df, left_on='temp_date', right_index=True, how='left'
    ).set_index(idx_name)
    
    # Forward fill macro status (it changes slowly)
    macro_cols = macro_df.columns.tolist()
    df[macro_cols] = df[macro_cols].ffill()
    
    # Clean up
    if 'temp_date' in df.columns:
        df.drop(columns=['temp_date'], inplace=True)
        
    return df

def preprocess_data(df_primary, df_mtf, df_vix=None):
    """Compute indicators including Dynamic MTF and Volatility context."""
    df = df_primary.copy()
    mdf = df_mtf.copy()
    
    # --- Volatility (VIX) Context ---
    if df_vix is not None and not df_vix.empty:
        vix_c = df_vix['Close'].reindex(df.index, method='ffill')
        df['VIX_Close'] = vix_c
        df['VIX_Momentum'] = df['VIX_Close'].pct_change(10)
    else:
        df['VIX_Close'] = 20.0 # Standard neutral
        df['VIX_Momentum'] = 0.0

    df['IV_Decimal'] = (df['VIX_Close'] / 100.0).fillna(0.20) # NEW: For Options Pricing

    # ...rest of the indicators...
    
    # --- Primary indicators ---
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP_Proxy'] = (tp * df['Volume'].replace(0, 1)).rolling(window=20).sum() / df['Volume'].replace(0, 1).rolling(window=20).sum()
    df['VWAP_Proxy_Dist'] = (df['Close'] / df['VWAP_Proxy']) - 1.0
    
    df['DC_20_Upper'] = df['High'].rolling(window=20).max()
    df['DC_20_Lower'] = df['Low'].rolling(window=20).min()
    
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean()
    
    df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Hist_Vol'] = df['Log_Ret'].rolling(window=20).std() * np.sqrt(252) # Note: 252 is for daily, intraday might need different scaling but works for relative sorting
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Patterns
    df['Body'] = (df['Close'] - df['Open']).abs()
    df['Lower_Wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['Upper_Wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    df['Bullish_Reversal'] = (df['Close'] > df['Open']) & (df['Lower_Wick'] > 1.2 * df['Body']) & (df['Body'] > 0)
    df['Bearish_Reversal'] = (df['Close'] < df['Open']) & (df['Upper_Wick'] > 1.2 * df['Body']) & (df['Body'] > 0)
    df['Inside_Bar'] = (df['High'] < df['High'].shift(1)) & (df['Low'] > df['Low'].shift(1))
    
    # ML Features
    df['SMA_20_Dist'] = (df['Close'] / df['SMA_20'] - 1) * 100
    df['SMA_50_Dist'] = (df['Close'] / df['SMA_50'] - 1) * 100
    df['Vol_Ratio'] = df['Volume'] / df['Volume'].replace(0, 1).rolling(20).mean()
    
    # --- Advanced ML Features ---
    # ADX Calculation
    upmove = df['High'] - df['High'].shift(1)
    downmove = df['Low'].shift(1) - df['Low']
    plus_dm = np.where((upmove > downmove) & (upmove > 0), upmove, 0)
    minus_dm = np.where((downmove > upmove) & (downmove > 0), downmove, 0)
    df['Plus_DI'] = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / df['ATR_14'])
    df['Minus_DI'] = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / df['ATR_14'])
    dx = 100 * (df['Plus_DI'] - df['Minus_DI']).abs() / (df['Plus_DI'] + df['Minus_DI']).replace(0, 1)
    df['ADX_14'] = dx.rolling(14).mean()
    
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist_Dist'] = df['MACD'] - df['MACD_Signal']
    
    # Bollinger Bands
    df['BB_Mid'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
    df['BB_Percent'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower']).replace(0, 1)
    
    df['Momentum_10'] = (df['Close'] / df['Close'].shift(10) - 1) * 100
    df['ATR_Pct'] = (df['ATR_14'] / df['Close']) * 100
    
    # Chaikin Money Flow (CMF)
    mfm = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']).replace(0, 1)
    mfv = mfm * df['Volume']
    df['CMF'] = mfv.rolling(20).sum() / df['Volume'].rolling(20).sum().replace(0, 1)
    
    # Commodity Channel Index (CCI)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    tp_sma = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
    df['CCI_14'] = (tp - tp_sma) / (0.015 * mad).replace(0, 1)
    
    # --- Project 32: Advanced Strategy Indicators ---
    # 1. Donchian Channels (20-period)
    df['Donchian_High'] = df['High'].rolling(20).max()
    df['Donchian_Low'] = df['Low'].rolling(20).min()
    df['Donchian_Mid'] = (df['Donchian_High'] + df['Donchian_Low']) / 2
    
    # 2. Money Flow Index (MFI)
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    rmf = tp * df['Volume']
    mf_dir = np.where(tp > tp.shift(1), 1, -1)
    pos_mf = (rmf * (mf_dir == 1)).rolling(14).sum()
    neg_mf = (rmf * (mf_dir == -1)).rolling(14).sum()
    df['MFI_14'] = 100 - (100 / (1 + (pos_mf / neg_mf.replace(0, 1))))
    
    # 3. Hull Moving Average (HMA) Helper
    def get_wma(series, period):
        weights = np.arange(1, period + 1)
        return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    
    wma_half = get_wma(df['Close'], 10)
    wma_full = get_wma(df['Close'], 20)
    df['HMA_20'] = get_wma(2 * wma_half - wma_full, int(np.sqrt(20)))
    
    # 4. Fisher Transform
    h_max = df['High'].rolling(9).max()
    l_min = df['Low'].rolling(9).min()
    val = (0.33 * 2 * ((df['Close'] - l_min) / (h_max - l_min).replace(0, 0.1) - 0.5)).rolling(1).mean() # smoothing
    def fisher_calc(x):
        fish = 0; res = []
        for v in x:
            v_adj = max(min(v, 0.999), -0.999)
            fish = 0.5 * np.log((1 + v_adj) / (1 - v_adj)) + 0.5 * fish
            res.append(fish)
        return res
    df['Fisher'] = fisher_calc(val.fillna(0))
    
    # 5. Ichimoku Cloud
    df['Ichi_Tenkan'] = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
    df['Ichi_Kijun'] = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
    df['Ichi_Senkou_A'] = ((df['Ichi_Tenkan'] + df['Ichi_Kijun']) / 2).shift(26)
    df['Ichi_Senkou_B'] = ((df['High'].rolling(52).max() + df['Low'].rolling(52).min()) / 2).shift(26)
    
    # 6. SuperTrend (Looping for signal consistency)
    hl2 = ((df['High'] + df['Low']) / 2).values
    atr = df['ATR_14'].values
    upper = hl2 + (3 * atr); lower = hl2 - (3 * atr)
    final_upper = upper.copy(); final_lower = lower.copy()
    close_arr = df['Close'].values
    st_signal = np.zeros(len(df))
    for i in range(1, len(df)):
        if upper[i] < final_upper[i-1] or close_arr[i-1] > final_upper[i-1]:
            final_upper[i] = upper[i]
        else: final_upper[i] = final_upper[i-1]
        if lower[i] > final_lower[i-1] or close_arr[i-1] < final_lower[i-1]:
            final_lower[i] = lower[i]
        else: final_lower[i] = final_lower[i-1]
        
        if close_arr[i] > final_upper[i]: st_signal[i] = 1
        elif close_arr[i] < final_lower[i]: st_signal[i] = -1
        else: st_signal[i] = st_signal[i-1]
    df['SuperTrend'] = st_signal
    
    # 7. Floor Pivots (Daily)
    df['P'] = (df['High'].shift(1) + df['Low'].shift(1) + df['Close'].shift(1)) / 3
    df['S1'] = (2 * df['P']) - df['High'].shift(1)
    df['R1'] = (2 * df['P']) - df['Low'].shift(1)
    
    # --- New indicators for Credit Spread Strategies ---
    df['sma_01'] = df['Close'].rolling(window=3).mean()
    df['sma_02'] = df['Close'].rolling(window=8).mean()
    df['sma_03'] = df['Close'].rolling(window=10).mean()
    df['ema_01'] = df['Close'].ewm(span=5, adjust=False).mean()
    df['ema_02'] = df['Close'].ewm(span=3, adjust=False).mean()
    df['ohlc_avg'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0
    
    # Streaks (Consecutive Green/Red Days)
    is_green = df['Close'] > df['Open']
    is_red = df['Close'] < df['Open']
    
    def get_streak(col):
        s = col.astype(int)
        group = (col != col.shift()).cumsum()
        return s.groupby(group).cumsum().where(col, 0)
        
    df['greenDays'] = get_streak(is_green)
    df['redDays'] = get_streak(is_red)
    
    # --- MTF indicators ---
    mdf['MTF_SMA_Short'] = mdf['Close'].rolling(window=10).mean()
    mdf['MTF_SMA_Long'] = mdf['Close'].rolling(window=40).mean()
    
    # Normalize timezones and join
    df.index = df.index.tz_localize(None)
    mdf.index = mdf.index.tz_localize(None)
    
    df = df.join(mdf[['MTF_SMA_Short', 'MTF_SMA_Long']], how='left')
    df['MTF_SMA_Short'] = df['MTF_SMA_Short'].ffill()
    df['MTF_SMA_Long'] = df['MTF_SMA_Long'].ffill()
    
    return df

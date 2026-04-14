import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, data, initial_capital=100000, risk_pc=1.0, ml_filter=None, 
                 global_stop_loss=0.0, global_take_profit=0.0, trailing_stop=0.0, max_hold_bars=0):
        self.df = data.copy()
        
        # Apply Market Regime if ML filter is capable
        if ml_filter and hasattr(ml_filter, 'regime_detector'):
            self.df['Market_Regime'] = ml_filter.regime_detector.predict(self.df)
        elif 'Market_Regime' not in self.df.columns:
            self.df['Market_Regime'] = 0
            
        self.initial_capital = initial_capital
        self.risk_pc = risk_pc / 100.0
        self.ml_filter = ml_filter
        self.global_stop_loss = global_stop_loss / 100.0
        self.global_take_profit = global_take_profit / 100.0
        self.trailing_stop = trailing_stop / 100.0
        self.max_hold_bars = max_hold_bars
        
    def run_strategy(self, strategy_name, use_ml=False, return_signal=False, return_logic=False):
        """Dispatches to the specific strategy method, with support for logic extraction."""
        try:
            if "Portfolio" in strategy_name:
                raise ValueError("run_strategy should be called on individual strategies.")
            parts = strategy_name.split(':')
            strategy_num = parts[0].strip().split(' ')[-1]
            method_name = f"strategy_{strategy_num}"
            if hasattr(self, method_name):
                return getattr(self, method_name)(use_ml=use_ml, return_signal=return_signal, return_logic=return_logic)
            else:
                raise ValueError(f"Strategy method {method_name} not found.")
        except Exception as e:
            if return_signal: return pd.Series(False, index=self.df.index)
            if return_logic: return None
            return pd.DataFrame(), pd.Series([self.initial_capital]*len(self.df), index=self.df.index)

    def get_all_signals(self, strategy_names):
        """Generates a matrix of entry signals for the provided strategies."""
        signals = {}
        for s in strategy_names:
            sig = self.run_strategy(s, return_signal=True)
            signals[s.split(':')[0]] = sig
        return pd.DataFrame(signals, index=self.df.index)

    def _calculate_metrics(self, trades, equity_curve):
        if trades.empty:
            return {
                "Total Return %": 0, "Max Drawdown %": 0, "Win Rate %": 0,
                "Profit Factor": 0, "Sharpe Ratio": 0, "Trade Count": 0,
                "Expectancy": 0, "Recovery Factor": 0, "Sortino Ratio": 0,
                "Avg Win": 0, "Avg Loss": 0, "Payoff Ratio": 0,
                "Max Consecutive Wins": 0, "Max Consecutive Losses": 0
            }
        
        total_return = (equity_curve.iloc[-1] / self.initial_capital - 1) * 100
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_dd = drawdown.min() * 100
        
        wins = trades[trades['PnL'] > 0]
        losses = trades[trades['PnL'] <= 0]
        win_rate = (len(wins) / len(trades)) * 100 if len(trades) > 0 else 0
        
        gross_profit = wins['PnL'].sum()
        gross_loss = abs(losses['PnL'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        avg_win = wins['PnL'].mean() if not wins.empty else 0
        avg_loss = abs(losses['PnL'].mean()) if not losses.empty else 0
        payoff_ratio = avg_win / avg_loss if avg_loss != 0 else 0
        
        expectancy = ((win_rate/100) * avg_win) - ((1 - win_rate/100) * avg_loss)
        total_profit = equity_curve.iloc[-1] - self.initial_capital
        money_drawdown = (equity_curve - rolling_max).min()
        recovery_factor = abs(total_profit / money_drawdown) if money_drawdown != 0 else 0
        
        returns = equity_curve.pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
        downside_returns = returns[returns < 0]
        sortino = (returns.mean() / downside_returns.std()) * np.sqrt(252) if not downside_returns.empty and downside_returns.std() != 0 else 0
        
        trades['is_win'] = trades['PnL'] > 0
        consecutive = trades['is_win'].groupby((trades['is_win'] != trades['is_win'].shift()).cumsum()).cumcount() + 1
        max_wins = consecutive[trades['is_win']].max() if any(trades['is_win']) else 0
        max_losses = consecutive[~trades['is_win']].max() if any(~trades['is_win']) else 0
        
        return {
            "Total Return %": round(total_return, 2), "Max Drawdown %": round(max_dd, 2),
            "Win Rate %": round(win_rate, 2), "Profit Factor": round(profit_factor, 2),
            "Sharpe Ratio": round(sharpe, 2), "Sortino Ratio": round(sortino, 2),
            "Trade Count": len(trades), "Expectancy": round(expectancy, 2),
            "Recovery Factor": round(recovery_factor, 2), "Avg Win": round(avg_win, 2),
            "Avg Loss": round(avg_loss, 2), "Payoff Ratio": round(payoff_ratio, 2),
            "Max Consecutive Wins": int(max_wins), "Max Consecutive Losses": int(max_losses)
        }

    def _simulate_trades(self, entries, exits_logic, type='long', fixed_stop_dist=0.03, use_ml=False, return_signal=False, return_logic=False, strat_name=""):
        if return_signal:
            return entries
        if return_logic:
            return exits_logic
            
        df = self.df.copy()
        df['Signal'] = entries
        trades = []
        equity = [self.initial_capital] * len(df)
        current_equity = self.initial_capital
        in_position = False
        entry_price = 0
        entry_idx = 0
        allocated_pos_size = 0
        
        hwm = 0 # High Water Mark for Trailing Stop
        
        for i in range(len(df)):
            if not in_position:
                if df['Signal'].iloc[i]:
                    should_trade = True
                    if use_ml and self.ml_filter and self.ml_filter.is_trained:
                        feat_row = df.loc[df.index[i]][self.ml_filter.features]
                        if not feat_row.isnull().any():
                            prob = self.ml_filter.predict(feat_row.values)
                            if prob < self.ml_filter.confidence_threshold:
                                should_trade = False
                    
                    if should_trade:
                        in_position = True
                        entry_price = df['Close'].iloc[i]
                        entry_idx = i
                        hwm = entry_price
                        risk_amount = current_equity * self.risk_pc
                        allocated_pos_size = min(risk_amount / fixed_stop_dist, current_equity)
                
                if i > 0: equity[i] = equity[i-1]
            else:
                # Update HWM for trailing stop
                if type == 'long':
                    hwm = max(hwm, df['High'].iloc[i])
                else:
                    hwm = min(hwm, df['Low'].iloc[i])
                
                # 1. Strategy Logic
                exit_signal, exit_price = exits_logic(df, i, entry_price, entry_idx)
                
                # 2. Global Overrides (Safeguards)
                bars_in = i - entry_idx
                if not exit_signal:
                    # Global Stop Loss
                    if self.global_stop_loss > 0:
                        sl_price = entry_price * (1 - self.global_stop_loss) if type == 'long' else entry_price * (1 + self.global_stop_loss)
                        if (type == 'long' and df['Low'].iloc[i] <= sl_price) or (type == 'short' and df['High'].iloc[i] >= sl_price):
                            exit_signal, exit_price = True, sl_price
                    
                    # Global Take Profit
                    if not exit_signal and self.global_take_profit > 0:
                        tp_price = entry_price * (1 + self.global_take_profit) if type == 'long' else entry_price * (1 - self.global_take_profit)
                        if (type == 'long' and df['High'].iloc[i] >= tp_price) or (type == 'short' and df['Low'].iloc[i] <= tp_price):
                            exit_signal, exit_price = True, tp_price
                            
                    # Global Trailing Stop
                    if not exit_signal and self.trailing_stop > 0:
                        ts_price = hwm * (1 - self.trailing_stop) if type == 'long' else hwm * (1 + self.trailing_stop)
                        if (type == 'long' and df['Low'].iloc[i] <= ts_price) or (type == 'short' and df['High'].iloc[i] >= ts_price):
                            exit_signal, exit_price = True, ts_price
                            
                    # Max Holding Bars
                    if not exit_signal and self.max_hold_bars > 0:
                        if bars_in >= self.max_hold_bars:
                            exit_signal, exit_price = True, df['Close'].iloc[i]

                if exit_signal:
                    pnl_pct = (exit_price / entry_price - 1) if type == 'long' else (1 - exit_price / entry_price)
                    trade_pnl = allocated_pos_size * pnl_pct
                    current_equity += trade_pnl
                    trades.append({
                        "Strategy": strat_name,
                        "Date In": df.index[entry_idx], 
                        "Date Out": df.index[i], 
                        "Type": type.capitalize(), 
                        "Entry Price": round(entry_price, 2), 
                        "Exit Price": round(exit_price, 2), 
                        "PnL": round(trade_pnl, 2), 
                        "PnL %": round(pnl_pct * 100, 2)
                    })
                    in_position = False
                
                if in_position:
                    unrealized_pnl_pct = max((df['Close'].iloc[i] / entry_price - 1) if type == 'long' else (1 - df['Close'].iloc[i] / entry_price), -1.0)
                    equity[i] = current_equity + (allocated_pos_size * unrealized_pnl_pct)
                else: equity[i] = current_equity
        return pd.DataFrame(trades), pd.Series(equity, index=df.index)

    # --- STRATEGIES (Updated to be bar-indexed) ---

    def strategy_1(self, use_ml=False, **kwargs):
        entries = (self.df['Close'] > self.df['SMA_20']) & (self.df['Close'] > self.df['SMA_50']) & (self.df['Low'] <= self.df['SMA_20'] * 1.01) & (self.df['Bullish_Reversal'])
        def exit_logic(df, i, ep, ei):
            t, s = df['DC_20_Upper'].iloc[ei], df['Low'].iloc[ei] - df['ATR_14'].iloc[ei] * 0.5
            if df['High'].iloc[i] >= t: return True, t
            if df['Low'].iloc[i] <= s: return True, s
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 1", **kwargs)

    def strategy_2(self, use_ml=False, **kwargs):
        entries = (self.df['Close'] > self.df['DC_20_Upper'].shift(1)) & (self.df['Volume'] > self.df['Volume'].rolling(20).mean() * 1.2)
        def exit_logic(df, i, ep, ei):
            rd = ep - (df['Low'].iloc[ei-1] if ei > 0 else ep*0.98)
            t, tr = ep + 2 * rd, df['Low'].iloc[i-1]
            if df['High'].iloc[i] >= t: return True, t
            if df['Low'].iloc[i] <= tr: return True, tr
            return False, 0
        return self._simulate_trades(entries, exit_logic, fixed_stop_dist=0.04, use_ml=use_ml, strat_name="Strategy 2", **kwargs)

    def strategy_3(self, use_ml=False, **kwargs):
        entries = (self.df['Close'] < self.df['SMA_20'] - 2 * self.df['ATR_14']) & (self.df['Bullish_Reversal'])
        def exit_logic(df, i, ep, ei):
            t, s = df['SMA_20'].iloc[i], df['Low'].iloc[ei] * 0.98
            if df['Close'].iloc[i] >= t: return True, df['Close'].iloc[i]
            if df['Low'].iloc[i] <= s: return True, s
            return False, 0
        return self._simulate_trades(entries, exit_logic, fixed_stop_dist=0.05, use_ml=use_ml, strat_name="Strategy 3", **kwargs)

    def strategy_4(self, use_ml=False, **kwargs):
        entries = (self.df['SMA_50'] > self.df['SMA_50'].shift(10)) & (self.df['Low'] <= self.df['SMA_20'] * 1.01) & (self.df['Hist_Vol'] > self.df['Hist_Vol'].rolling(50).mean())
        def exit_logic(df, i, ep, ei):
            bars_in = i - ei
            if bars_in >= 15 or df['Close'].iloc[i] >= ep * 1.01: return True, ep * 1.015
            if df['Close'].iloc[i] < df['SMA_50'].iloc[i]: return True, ep * 0.97
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 4", **kwargs)

    def strategy_5(self, use_ml=False, **kwargs):
        entries = (self.df['Close'] < self.df['SMA_50']) & (self.df['High'] >= self.df['SMA_20'] * 0.99) & (self.df['Bearish_Reversal'])
        def exit_logic(df, i, ep, ei):
            bars_in = i - ei
            if bars_in >= 15 or df['Close'].iloc[i] <= ep * 0.99: return True, ep * 0.985
            if df['Close'].iloc[i] > df['DC_20_Upper'].iloc[ei]: return True, ep * 1.03
            return False, 0
        return self._simulate_trades(entries, exit_logic, type='short', use_ml=use_ml, strat_name="Strategy 5", **kwargs)

    def strategy_6(self, use_ml=False, **kwargs):
        entries = (self.df['Inside_Bar']) & (self.df['Hist_Vol'] > self.df['Hist_Vol'].rolling(50).mean())
        def exit_logic(df, i, ep, ei):
            bars_in, pdv = i - ei, abs(df['Close'].iloc[i] / ep - 1)
            if bars_in >= 15: return True, ep * (1.01 if pdv < 0.03 else 0.97)
            if pdv > 0.04: return True, ep * 0.96
            return False, 0
        return self._simulate_trades(entries, exit_logic, fixed_stop_dist=0.04, use_ml=use_ml, strat_name="Strategy 6", **kwargs)

    def strategy_7(self, use_ml=False, **kwargs):
        entries = (self.df['Inside_Bar'].shift(1)) & (self.df['High'] > self.df['High'].shift(2))
        def exit_logic(df, i, ep, ei):
            t, s = ep + df['ATR_14'].iloc[ei] * 2, df['Low'].iloc[ei-1]
            if df['High'].iloc[i] >= t: return True, t
            if df['Low'].iloc[i] <= s: return True, s
            return False, 0
        return self._simulate_trades(entries, exit_logic, fixed_stop_dist=0.02, use_ml=use_ml, strat_name="Strategy 7", **kwargs)

    def strategy_8(self, use_ml=False, **kwargs):
        uptrend = self.df['SMA_50'] > self.df['SMA_50'].shift(5)
        pullback = (self.df['Close'].shift(1) < self.df['Close'].shift(2)) & (self.df['Close'].shift(2) < self.df['Close'].shift(3))
        entries = uptrend & pullback & self.df['Bullish_Reversal']
        def exit_logic(df, i, ep, ei):
            t, s = df['High'].rolling(10).max().iloc[ei], df['Low'].iloc[i-1]
            if df['High'].iloc[i] >= t: return True, t
            if df['Low'].iloc[i] <= s: return True, s
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 8", **kwargs)

    def strategy_9(self, use_ml=False, **kwargs):
        entries = (self.df['SMA_50'] > self.df['SMA_50'].shift(10)) & (self.df['Low'] <= self.df['SMA_20'] * 1.01) & (self.df['Hist_Vol'] > self.df['Hist_Vol'].rolling(50).mean())
        def exit_logic(df, i, ep, ei):
            bars_in = i - ei
            if bars_in >= 15 or df['Close'].iloc[i] <= ep * 0.99: return True, ep * 0.985
            if df['Close'].iloc[i] > df['SMA_50'].iloc[i] * 1.02: return True, ep * 1.03
            return False, 0
        return self._simulate_trades(entries, exit_logic, type='short', use_ml=use_ml, strat_name="Strategy 9", **kwargs)

    def strategy_10(self, use_ml=False, **kwargs):
        """Strategy 10: Insider Alpha (Smart Money Following - Buys Only)"""
        if 'Insider_Sentiment' not in self.df.columns:
            return pd.DataFrame(), pd.Series([self.initial_capital]*len(self.df), index=self.df.index)
            
        # Entry: Buy intensity is 10% above its 50-day SMA + Long Term Trend
        entries = (self.df['Insider_Sentiment'] > 1.10) & (self.df['Close'] > self.df['SMA_50']) & (self.df['Bullish_Reversal'])
        
        def exit_logic(df, i, ep, ei):
            # 3.5% Stop / 7% Target
            t, s = ep * 1.07, ep * 0.965
            
            # Reversal criteria: Buying intensity drops below neutral
            sent_rev = df['Insider_Sentiment'].iloc[i] < 0.95 if 'Insider_Sentiment' in df.columns else False
            trend_brk = df['Close'].iloc[i] < df['SMA_50'].iloc[i]
            
            if df['High'].iloc[i] >= t: return True, t
            if df['Low'].iloc[i] <= s: return True, s
            if sent_rev or trend_brk: return True, df['Close'].iloc[i]
            return False, 0
            
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 10", **kwargs)

    def strategy_11(self, use_ml=False, **kwargs):
        """Strategy 11: Combo Alpha (Multi-Signal Mean Reversion)"""
        df = self.df
        e1 = (df['Close'] < df['sma_03']) & (df['Close'] <= df['sma_01']) & (df['Close'].shift(1) > df['sma_01'].shift(1)) & (df['Open'] > df['ema_01']) & (df['sma_02'] < df['sma_02'].shift(1))
        e2 = (df['Close'] < df['ema_02']) & (df['Open'] > df['ohlc_avg']) & (df['Volume'] <= df['Volume'].shift(1))
        entries = e1 | e2
        
        def exit_logic(df, i, ep, ei):
            bars_in = i - ei
            profit_closes = (df['Close'].iloc[ei+1:i+1] > ep).sum()
            if profit_closes >= 5: return True, df['Close'].iloc[i]
            if bars_in >= 10: return True, df['Close'].iloc[i]
            if df['Low'].iloc[i] <= ep * 0.95: return True, ep * 0.95
            return False, 0
            
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 11", **kwargs)

    def strategy_12(self, use_ml=False, **kwargs):
        """Strategy 12: Streak Follower (Behavioral Over-extension)"""
        entries = (self.df['redDays'] >= 3)
        def exit_logic(df, i, ep, ei):
            if df['greenDays'].iloc[i] >= 2: return True, df['Close'].iloc[i]
            if df['Low'].iloc[i] <= ep * 0.95: return True, ep * 0.95
            if i - ei >= 15: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 12", **kwargs)

    def strategy_13(self, use_ml=False, **kwargs):
        """Strategy 13: SuperTrend Follower"""
        entries = (self.df['SuperTrend'] == 1) & (self.df['SuperTrend'].shift(1) == -1)
        def exit_logic(df, i, ep, ei):
            if df['SuperTrend'].iloc[i] == -1: return True, df['Close'].iloc[i]
            if i - ei > 30: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 13", **kwargs)

    def strategy_14(self, use_ml=False, **kwargs):
        """Strategy 14: Ichimoku Cloud Breakout"""
        entries = (self.df['Close'] > self.df['Ichi_Senkou_A']) & (self.df['Close'] > self.df['Ichi_Senkou_B']) & \
                  (self.df['Close'].shift(1) <= self.df['Ichi_Senkou_A'].shift(1))
        def exit_logic(df, i, ep, ei):
            if df['Close'].iloc[i] < df['Ichi_Kijun'].iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 14", **kwargs)

    def strategy_15(self, use_ml=False, **kwargs):
        """Strategy 15: EMA Ribbon Expansion"""
        ema5 = self.df['Close'].ewm(span=5).mean()
        ema13 = self.df['Close'].ewm(span=13).mean()
        ema21 = self.df['Close'].ewm(span=21).mean()
        entries = (ema5 > ema13) & (ema13 > ema21) & (ema5 > ema5.shift(1))
        def exit_logic(df, i, ep, ei):
            if df['Close'].iloc[i] < ema21.iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 15", **kwargs)

    def strategy_16(self, use_ml=False, **kwargs):
        """Strategy 16: Donchian 20-Day Breakout"""
        entries = (self.df['Close'] > self.df['Donchian_High'].shift(1))
        def exit_logic(df, i, ep, ei):
            if df['Close'].iloc[i] < df['Donchian_Mid'].iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 16", **kwargs)

    def strategy_17(self, use_ml=False, **kwargs):
        """Strategy 17: HMA Slope Pivot"""
        entries = (self.df['HMA_20'] > self.df['HMA_20'].shift(1)) & (self.df['HMA_20'].shift(1) <= self.df['HMA_20'].shift(2))
        def exit_logic(df, i, ep, ei):
            if df['HMA_20'].iloc[i] < df['HMA_20'].shift(1).iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 17", **kwargs)

    def strategy_18(self, use_ml=False, **kwargs):
        """Strategy 18: Stochastic RS Fade"""
        low_roll = self.df['Low'].rolling(14).min()
        high_roll = self.df['High'].rolling(14).max()
        stoch_k = 100 * (self.df['Close'] - low_roll) / (high_roll - low_roll).replace(0, 1)
        entries = (stoch_k < 20) & (self.df['RSI'] < 30)
        def exit_logic(df, i, ep, ei):
            if stoch_k.iloc[i] > 80: return True, df['Close'].iloc[i]
            if df['Low'].iloc[i] <= ep * 0.97: return True, ep * 0.97
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 18", **kwargs)

    def strategy_19(self, use_ml=False, **kwargs):
        """Strategy 19: Fisher Transform Reversal"""
        entries = (self.df['Fisher'] > self.df['Fisher'].shift(1)) & (self.df['Fisher'].shift(1) < -1.5)
        def exit_logic(df, i, ep, ei):
            if df['Fisher'].iloc[i] < df['Fisher'].shift(1).iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 19", **kwargs)

    def strategy_20(self, use_ml=False, **kwargs):
        """Strategy 20: Parabolic SAR Flip"""
        # Close enough approximation using price/HL2
        entries = (self.df['Close'] > self.df['Donchian_Mid']) & (self.df['Close'].shift(1) <= self.df['Donchian_Mid'].shift(1))
        def exit_logic(df, i, ep, ei):
            if df['Close'].iloc[i] < df['Donchian_Mid'].iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 20", **kwargs)

    def strategy_21(self, use_ml=False, **kwargs):
        """Strategy 21: Volatility Squeeze Breakout"""
        kc_mid = self.df['Close'].rolling(20).mean()
        kc_range = self.df['ATR_14'] * 1.5
        kc_upper = kc_mid + kc_range; kc_lower = kc_mid - kc_range
        is_squeeze = (self.df['BB_Upper'] < kc_upper) & (self.df['BB_Lower'] > kc_lower)
        entries = (~is_squeeze) & (is_squeeze.shift(1)) & (self.df['Close'] > self.df['Close'].shift(1))
        def exit_logic(df, i, ep, ei):
            if i - ei > 10: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 21", **kwargs)

    def strategy_22(self, use_ml=False, **kwargs):
        """Strategy 22: Money Flow Index (MFI) Divergence"""
        entries = (self.df['MFI_14'] < 20) & (self.df['Close'] < self.df['Close'].shift(1))
        def exit_logic(df, i, ep, ei):
            if df['MFI_14'].iloc[i] > 60: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 22", **kwargs)

    def strategy_23(self, use_ml=False, **kwargs):
        """Strategy 23: ORB (30-min Approximation)"""
        # Approximating ORB using High/Low of first bar (Daily approximation)
        day_range = (self.df['High'] - self.df['Low']).rolling(10).mean()
        entries = (self.df['Close'] > self.df['Open'] + (day_range * 0.2))
        def exit_logic(df, i, ep, ei):
            if df['Close'].iloc[i] < df['Open'].iloc[ei]: return True, df['Close'].iloc[i]
            if i - ei > 5: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 23", **kwargs)

    def strategy_24(self, use_ml=False, **kwargs):
        """Strategy 24: Gap-and-Go"""
        gap = (self.df['Open'] / self.df['Close'].shift(1)) - 1
        entries = (gap > 0.005) & (self.df['Volume'] > self.df['Volume'].rolling(20).mean())
        def exit_logic(df, i, ep, ei):
            if i - ei >= 1: return True, df['Close'].iloc[i] # Day trade logic
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 24", **kwargs)

    def strategy_25(self, use_ml=False, **kwargs):
        """Strategy 25: Gap Fade"""
        gap = (self.df['Open'] / self.df['Close'].shift(1)) - 1
        entries = (gap > 0.015) & (self.df['RSI'] > 70)
        def exit_logic(df, i, ep, ei):
            # Exit once gap is closed or 2 days pass
            if df['Low'].iloc[i] <= df['Close'].iloc[ei-1]: return True, df['Close'].iloc[i]
            if i - ei >= 2: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 25", **kwargs)

    def strategy_26(self, use_ml=False, **kwargs):
        """Strategy 26: Turnaround Tuesday"""
        # Logic: Wednesday (3) if Monday/Tuesday were red
        is_wed = self.df.index.dayofweek == 2
        entries = is_wed & (self.df['Close'].shift(1) < self.df['Open'].shift(1)) & (self.df['Close'].shift(2) < self.df['Open'].shift(2))
        def exit_logic(df, i, ep, ei):
            if i - ei >= 3: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 26", **kwargs)

    def strategy_27(self, use_ml=False, **kwargs):
        """Strategy 27: Friday Afternoon Squeeze"""
        is_fri = self.df.index.dayofweek == 4
        entries = is_fri & (self.df['Close'] > self.df['Open']) & (self.df['Close'] > self.df['SMA_20'])
        def exit_logic(df, i, ep, ei):
            if i - ei >= 1: return True, df['Open'].iloc[i+1] if i+1 < len(df) else df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 27", **kwargs)

    def strategy_28(self, use_ml=False, **kwargs):
        """Strategy 28: Pivot Point Bounce"""
        entries = (self.df['Low'] <= self.df['S1']) & (self.df['Close'] > self.df['S1'])
        def exit_logic(df, i, ep, ei):
            if df['High'].iloc[i] >= df['P'].iloc[i]: return True, df['P'].iloc[i]
            if df['Low'].iloc[i] < df['Low'].iloc[ei] * 0.98: return True, df['Low'].iloc[ei] * 0.98
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 28", **kwargs)

    def strategy_29(self, use_ml=False, **kwargs):
        """Strategy 29: MTF RSI Alignment"""
        # Weekly RSI approximation using 70-day window
        weekly_rsi = self.df['RSI'].rolling(5).mean()
        entries = (self.df['RSI'] < 40) & (weekly_rsi < 45) & (self.df['RSI'] > self.df['RSI'].shift(1))
        def exit_logic(df, i, ep, ei):
            if df['RSI'].iloc[i] > 65: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 29", **kwargs)

    def strategy_30(self, use_ml=False, **kwargs):
        """Strategy 30: Heikin Ashi Rider"""
        ha_close = (self.df['Open'] + self.df['High'] + self.df['Low'] + self.df['Close']) / 4
        ha_open = (self.df['Open'].shift(1) + self.df['Close'].shift(1)) / 2
        entries = (ha_close > ha_open) & (ha_close.shift(1) <= ha_open.shift(1))
        def exit_logic(df, i, ep, ei):
            if ha_close.iloc[i] < ha_open.iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 30", **kwargs)

    def strategy_31(self, use_ml=False, **kwargs):
        """Strategy 31: Volatility Spike Fade"""
        vol_spike = self.df['Hist_Vol'] > self.df['Hist_Vol'].rolling(50).mean() * 1.5
        entries = vol_spike & (self.df['Close'] < self.df['BB_Lower'])
        def exit_logic(df, i, ep, ei):
            if df['Close'].iloc[i] > df['BB_Mid'].iloc[i]: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 31", **kwargs)

    def strategy_32(self, use_ml=False, **kwargs):
        """Strategy 32: Mean Reversion (v2 - Z-Score)"""
        sma_200 = self.df['Close'].rolling(200).mean()
        std_200 = self.df['Close'].rolling(200).std()
        z_score = (self.df['Close'] - sma_200) / std_200.replace(0, 1)
        entries = (z_score < -2.0)
        def exit_logic(df, i, ep, ei):
            if z_score.iloc[i] > -0.5: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 32", **kwargs)

    def strategy_33(self, use_ml=False, **kwargs):
        """Strategy 33: Yield Curve Regime Filter"""
        # Only take long signals if Yield Spread (10Y-2Y) is positive
        is_positive_spread = self.df['T10Y2Y'] > 0 if 'T10Y2Y' in self.df.columns else True
        raw_signals = (self.df['Close'] > self.df['SMA_50']) & (self.df['RSI'] < 40)
        entries = raw_signals & is_positive_spread
        def exit_logic(df, i, ep, ei):
            if df['RSI'].iloc[i] > 60: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 33", **kwargs)

    def strategy_34(self, use_ml=False, **kwargs):
        """Strategy 34: VIX Spike Mean Reversion"""
        # Entry: VIX > 25 and starting to decline + Bullish reversal in SPY
        if 'VIX_Close' not in self.df.columns:
            return pd.DataFrame(), pd.Series([self.initial_capital]*len(self.df), index=self.df.index)
        vix_spike = (self.df['VIX_Close'] > 25) & (self.df['VIX_Close'] < self.df['VIX_Close'].shift(1))
        entries = vix_spike & self.df['Bullish_Reversal']
        def exit_logic(df, i, ep, ei):
            if df['VIX_Close'].iloc[i] < 20: return True, df['Close'].iloc[i]
            if i - ei >= 10: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 34", **kwargs)

    def strategy_35(self, use_ml=False, **kwargs):
        """Strategy 35: Monetary Policy Pivot"""
        # Entry: Fed Funds Rate is not rising sharply (Momentum <= 0) + SPY above 200 SMA
        sma_200 = self.df['Close'].rolling(200).mean()
        policy_ok = self.df['Fed_Policy_Bias'] <= 0.05 if 'Fed_Policy_Bias' in self.df.columns else True
        entries = policy_ok & (self.df['Close'] > sma_200) & (self.df['RSI'] < 45)
        def exit_logic(df, i, ep, ei):
            if i - ei > 20: return True, df['Close'].iloc[i]
            return False, 0
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 35", **kwargs)

    def strategy_36(self, use_ml=False, **kwargs):
        """Strategy 36: AI Meta-Ensemble (Master Brain)"""
        if not self.ml_filter or not self.ml_filter.is_trained:
            # Fallback to simple consensus if not trained
            signal_df = self.get_all_signals([f"Strategy {i}" for i in range(1, 36)])
            consensus = signal_df.mean(axis=1)
            entries = consensus > 0.4 # Need 40% agreement
        else:
            # Full AI Weighting
            signal_names = [f"Strategy {i}" for i in range(1, 36)]
            signal_df = self.get_all_signals(signal_names)
            
            # For each bar, generate probability
            entries = pd.Series(False, index=self.df.index)
            
            # Optimization: We only need to predict for bars where at least 1 signal is active
            active_any = signal_df.any(axis=1)
            
            # Robustly fetch ensemble features list
            e_feats = getattr(self.ml_filter, 'ensemble_features', [])
            
            for i in range(len(self.df)):
                if active_any.iloc[i]:
                    feat_row = self.df.iloc[i].reindex(self.ml_filter.base_features)
                    sig_row = signal_df.iloc[i]
                    # Combine base features + signal features
                    full_feat = pd.concat([feat_row, sig_row]).fillna(0)
                    
                    # Align with trained ensemble features (e.g. 52 inputs)
                    model_input = full_feat.reindex(e_feats).fillna(0)
                    prob = self.ml_filter.predict(model_input.values)
                    
                    if prob > self.ml_filter.confidence_threshold:
                        entries.iloc[i] = True
                            
        def exit_logic(df, i, ep, ei):
            bars_in = i - ei
            if bars_in >= 10: return True, df['Close'].iloc[i]
            if df['Low'].iloc[i] <= ep * 0.97: return True, ep * 0.97
            if df['High'].iloc[i] >= ep * 1.05: return True, ep * 1.05
            return False, 0
            
        return self._simulate_trades(entries, exit_logic, use_ml=use_ml, strat_name="Strategy 36", **kwargs)

    def run_ai_selective_master(self, strategy_options):
        """
        AI Selective Master: Only ONE position open at a time globally.
        Picks the firing strategy with the highest AI trust score.
        """
        # 1. Setup
        strategy_names = [s for s in strategy_options if "Strategy" in s and "AI Meta-Ensemble" not in s]
        signals_df = self.get_all_signals(strategy_names)
        
        # Pre-fetch exit logics
        logics = {}
        for s in strategy_names:
            logics[s] = self.run_strategy(s, return_logic=True)
            
        df = self.df.copy()
        equity = [self.initial_capital] * len(df)
        current_equity = self.initial_capital
        trades = []
        
        in_position = False
        active_logic = None
        active_strat = None
        entry_price = 0
        entry_idx = 0
        allocated_pos_size = 0
        hwm = 0
        
        total_collisions = 0
        
        for i in range(len(df)):
            # Track collisions (bars with >1 signal)
            firing_count = (signals_df.iloc[i] == True).sum()
            if firing_count > 1:
                total_collisions += 1

            if not in_position:
                # Find all firing strategies
                firing_cols = [c for c in signals_df.columns if signals_df[c].iloc[i] == True]
                
                if firing_cols and self.ml_filter and self.ml_filter.is_trained:
                    # Pick the one with highest trust score
                    best_strat = None
                    max_trust = -1
                    
                    for s in firing_cols:
                        try:
                            # Use full name "Strategy X" to match ml_engine mapping
                            trust = self.ml_filter.trust_scores.get(s, 0)
                            if trust > max_trust:
                                max_trust = trust
                                best_strat = s
                        except: continue
                    
                    if best_strat:
                        # Check global AI confidence for this bar
                        # Extract standard features and strategy signals for this bar
                        feat_row = df.iloc[i].reindex(self.ml_filter.base_features)
                        sig_row = signals_df.iloc[i]
                        full_feat = pd.concat([feat_row, sig_row]).fillna(0)
                        
                        # Robustly align with model features using the ensemble feature list
                        e_feats = getattr(self.ml_filter, 'ensemble_features', [])
                        model_input = full_feat.reindex(e_feats).fillna(0)
                        prob = self.ml_filter.predict(model_input.values)
                        
                        # Only trade if model probability exceeds threshold
                        if prob >= self.ml_filter.confidence_threshold:
                                in_position = True
                                active_strat = best_strat
                                active_logic = logics.get(best_strat)
                                if not active_logic: # Fallback if name mapping failed
                                    for k, v in logics.items():
                                        if best_strat in k: 
                                            active_logic = v
                                            break
                                            
                                entry_price = df['Close'].iloc[i]
                                entry_idx = i
                                hwm = entry_price
                                risk_amount = current_equity * self.risk_pc
                                allocated_pos_size = min(risk_amount / 0.03, current_equity) # 3% default stop
                
                if i > 0: equity[i] = equity[i-1]
            else:
                # Update HWM
                hwm = max(hwm, df['High'].iloc[i])
                
                # Check for exit (using the active strategy's logic)
                exit_signal = False
                exit_price = 0
                
                if active_logic:
                    exit_signal, exit_price = active_logic(df, i, entry_price, entry_idx)
                
                # Global Overrides
                bars_in = i - entry_idx
                if not exit_signal:
                    loss_pc = (df['Low'].iloc[i] / entry_price - 1)
                    if self.global_stop_loss > 0 and loss_pc <= -self.global_stop_loss:
                        exit_signal, exit_price = True, entry_price * (1 - self.global_stop_loss)
                    elif self.trailing_stop > 0 and (df['Low'].iloc[i] / hwm - 1) <= -self.trailing_stop:
                        exit_signal, exit_price = True, hwm * (1 - self.trailing_stop)
                    elif self.global_take_profit > 0 and (df['High'].iloc[i] / entry_price - 1) >= self.global_take_profit:
                        exit_signal, exit_price = True, entry_price * (1 + self.global_take_profit)
                    elif self.max_hold_bars > 0 and bars_in >= self.max_hold_bars:
                        exit_signal, exit_price = True, df['Close'].iloc[i]

                if exit_signal:
                    pnl = (exit_price / entry_price - 1) * allocated_pos_size
                    current_equity += pnl
                    trades.append({
                        "Strategy": active_strat,
                        "Date In": df.index[entry_idx],
                        "Date Out": df.index[i],
                        "Type": "Long",
                        "Entry Price": round(entry_price, 2),
                        "Exit Price": round(exit_price, 2),
                        "PnL": round(pnl, 2),
                        "PnL %": round((exit_price / entry_price - 1) * 100, 2),
                        "Duration": bars_in
                    })
                    in_position = False
                    active_logic = None
                    active_strat = None
                
                equity[i] = current_equity
                
        return pd.DataFrame(trades), pd.Series(equity, index=df.index), total_collisions

import pandas as pd
import numpy as np
from core.strategies import BacktestEngine
from core.options_pricer import BlackScholesPricer

class OptionsBacktestEngine(BacktestEngine):
    def __init__(self, data, initial_capital=100000, risk_pc=1.0, ml_filter=None, 
                 global_stop_loss=0.0, global_take_profit=0.0, trailing_stop=0.0, 
                 max_hold_bars=0, target_dte=30, target_delta=0.50):
        super().__init__(data, initial_capital, risk_pc, ml_filter, 
                         global_stop_loss, global_take_profit, trailing_stop, max_hold_bars)
        self.target_dte = target_dte
        self.target_delta = target_delta

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
        
        # Option Position Tracking
        entry_option_price = 0
        entry_strike = 0
        option_type = 'call' if type == 'long' else 'put'
        num_contracts = 0
        entry_idx = 0
        entry_spot = 0
        
        hwm = 0 # High water mark for option premium
        
        for i in range(len(df)):
            # Fallbacks for macro data
            r = df['FEDFUNDS'].iloc[i] / 100.0 if 'FEDFUNDS' in df.columns else 0.04
            iv = df['IV_Decimal'].iloc[i] if 'IV_Decimal' in df.columns else 0.20
            
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
                        S = df['Close'].iloc[i]
                        
                        entry_strike = BlackScholesPricer.find_strike_for_delta(
                            S, self.target_dte/365.0, r, iv, self.target_delta, option_type
                        )
                        
                        entry_option_price = BlackScholesPricer.price(
                            S, entry_strike, self.target_dte/365.0, r, iv, option_type
                        )
                        
                        if entry_option_price <= 0: entry_option_price = 0.01
                        
                        in_position = True
                        entry_idx = i
                        entry_spot = S
                        hwm = entry_option_price
                        
                        # Position Sizing: Risk % of Equity on Option Premium Max Loss (Long Options)
                        max_risk = current_equity * self.risk_pc
                        # Option cost per contract = premium * 100
                        max_contracts = int(max_risk / (entry_option_price * 100))
                        num_contracts = max(1, max_contracts) 
                
                if i > 0: equity[i] = equity[i-1]
                
            else:
                bars_in = i - entry_idx
                dte_remaining = self.target_dte - bars_in
                
                S = df['Close'].iloc[i]
                current_option_price = BlackScholesPricer.price(
                    S, entry_strike, max(dte_remaining, 0)/365.0, r, iv, option_type
                )
                
                hwm = max(hwm, current_option_price)
                
                # Evaluate spot exit logic from original strategy
                spot_exit_signal, spot_exit_price = exits_logic(df, i, entry_spot, entry_idx)
                
                exit_signal = spot_exit_signal
                exit_reason = "Underlying Logic"
                
                # Options-specific overrides
                if not exit_signal:
                    if dte_remaining <= 0:
                        exit_signal = True
                        exit_reason = "Expiration"
                    elif self.global_stop_loss > 0 and current_option_price <= entry_option_price * (1 - self.global_stop_loss):
                        exit_signal = True
                        exit_reason = f"Option SL ({self.global_stop_loss*100}%)"
                    elif self.global_take_profit > 0 and current_option_price >= entry_option_price * (1 + self.global_take_profit):
                        exit_signal = True
                        exit_reason = f"Option TP ({self.global_take_profit*100}%)"
                    elif self.trailing_stop > 0 and current_option_price <= hwm * (1 - self.trailing_stop):
                        exit_signal = True
                        exit_reason = "Trailing Stop"
                    elif self.max_hold_bars > 0 and bars_in >= self.max_hold_bars:
                        exit_signal = True
                        exit_reason = "Max Duration"
                        
                if exit_signal:
                    # Execute option sell at current theoretical price
                    pnl_per_contract = (current_option_price - entry_option_price) * 100
                    trade_pnl = pnl_per_contract * num_contracts
                    current_equity += trade_pnl
                    
                    trades.append({
                        "Strategy": strat_name,
                        "Date In": df.index[entry_idx],
                        "Date Out": df.index[i],
                        "Type": f"Long {option_type.capitalize()}",
                        "Strike": entry_strike,
                        "Entry Price": round(entry_option_price, 2),
                        "Exit Price": round(current_option_price, 2),
                        "PnL": round(trade_pnl, 2),
                        "PnL %": round((current_option_price / entry_option_price - 1) * 100, 2) if entry_option_price > 0 else 0,
                        "Contracts": num_contracts,
                        "DTE Remaining": dte_remaining,
                        "Exit Reason": exit_reason
                    })
                    in_position = False
                    
                if in_position:
                    unrealized_pnl = (current_option_price - entry_option_price) * 100 * num_contracts
                    equity[i] = current_equity + unrealized_pnl
                else: 
                    equity[i] = current_equity
                    
        return pd.DataFrame(trades), pd.Series(equity, index=df.index), 0 # 0 is dummy output for backwards compat if needed (Selective Master collision rate)
